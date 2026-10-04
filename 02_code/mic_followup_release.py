"""Release original-figure observations, then audit the unchanged fixed split.

Evidence decisions precede partitioning. No model output is read by this module.
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold

from mic_reviewed_release import _check_inputs
from public_data import measurement_label
from research_data import sequence_identity
from research_evidence_gate import verify_manifest
from research_utils import ROOT, read_json, sha256, utc_now, write_json
from validate_mic_acid_progress import independent_identity

RETRIEVAL = ROOT / '03_experiments/audits/mic_followup_source_retrieval_20261004_v1'
BASELINE = ROOT / '03_experiments/audits/mic_three_fold_20261002_v1'
PRIOR_STATE = ROOT / '03_experiments/audits/mic_training_readiness_20261003_v20.json'
XML = ROOT / '03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/bmap2025.xml'
FIGURE = RETRIEVAL / 'bmap_figure_1.jpeg'
BMAP_ID = '5445b7b645f69b6d7f8abdf3'
PISCIDIN_ID = '4e1914c54d14afece198fd5d'
FIGURE_SHA = 'c4f0f07f3c4df75955ffbb034f165da2ea4eaef8cbb54e42d10adf636810c815'
FORM = 'linear canonical sequence with free amino and carboxyl termini'


def label_of(row: dict, sequence: str) -> int:
    label = measurement_label({'concentration': row['raw_mic'], 'unit': {'name': row['raw_unit']}},
                              sequence, 32, 128)
    if label is None:
        raise ValueError('Raw measurement does not produce a frozen binary label')
    return label


def ensure_consistent(assays: pd.DataFrame, sequences: dict) -> dict:
    labels = {}
    for sample, records in assays.groupby('sample_id', sort=False):
        derived = {label_of(row, sequences[sample]) for row in records.to_dict('records')}
        if len(derived) != 1:
            raise ValueError(f'Opposite measured labels block molecule release: {sample}')
        labels[sample] = derived.pop()
    return labels


def aliases_for(molecules: pd.DataFrame, assays: pd.DataFrame, sources: pd.DataFrame) -> dict:
    urls = sources.set_index('source_id').source_url.to_dict()
    aliases = {str(r.sample_id): set(filter(None, str(r.study_ids).split('|')))
               for r in molecules.itertuples(index=False)}
    for r in assays.itertuples(index=False):
        values = aliases[str(r.sample_id)]
        values.add('primary_source:' + r.source_id)
        values.update(filter(None, str(r.assay_study_ids).split('|')))
        url = urls[r.source_id]
        if 'doi.org/' in url:
            values.add('doi:' + url.split('doi.org/', 1)[1].lower())
    return {sample: {v.strip().lower() for v in values} for sample, values in aliases.items()}


def graph_components(ids: list, pairs: list, aliases: dict) -> dict:
    parent = {sample: sample for sample in ids}
    def find(sample):
        while parent[sample] != sample:
            parent[sample] = parent[parent[sample]]
            sample = parent[sample]
        return sample
    def union(a, b):
        aa, bb = find(a), find(b)
        parent[max(aa, bb)] = min(aa, bb)
    for row in pairs:
        a, b = row['sample_id_a'], row['sample_id_b']
        if row['identity'] >= .40 or aliases[a] & aliases[b]:
            union(a, b)
    roots = sorted({find(sample) for sample in ids})
    return {sample: roots.index(find(sample)) for sample in ids}


def audit_partition(molecules: pd.DataFrame, assays: pd.DataFrame, sources: pd.DataFrame,
                    roles: pd.DataFrame, stored_pairs: pd.DataFrame) -> dict:
    ids = molecules.sample_id.tolist()
    seq = molecules.set_index('sample_id').seq.to_dict()
    labels = ensure_consistent(assays, seq)
    if labels != molecules.set_index('sample_id').amp.astype(int).to_dict():
        raise ValueError('Independent measurement-derived molecule labels differ')
    aliases = aliases_for(molecules, assays, sources)
    pairs = [{'sample_id_a': a, 'sample_id_b': b, 'identity': independent_identity(seq[a], seq[b])}
             for a,b in itertools.combinations(ids, 2)]
    expected = {(r['sample_id_a'], r['sample_id_b']): r['identity'] for r in pairs}
    actual = {(r.sample_id_a, r.sample_id_b): float(r.identity) for r in stored_pairs.itertuples(index=False)}
    if len(stored_pairs) != len(expected) or set(actual) != set(expected) or any(abs(actual[k]-v)>1e-12 for k,v in expected.items()):
        raise ValueError('Full-member independent pair audit differs')
    components = graph_components(ids, pairs, aliases)
    if components != molecules.set_index('sample_id').component.astype(int).to_dict():
        raise ValueError('Independent homology/study connected components differ')
    fold_for = roles[roles.role.eq('validation')].set_index('sample_id').fold.to_dict()
    blockers=[]
    if set(fold_for)!=set(ids) or len(roles[roles.role.eq('validation')])!=len(ids):
        blockers.append('Every molecule must have exactly one validation fold')
    cross_hom = sum(r['identity']>=.40 and fold_for.get(r['sample_id_a'])!=fold_for.get(r['sample_id_b']) for r in pairs)
    cross_study = sum(bool(aliases[a]&aliases[b]) and fold_for.get(a)!=fold_for.get(b) for a,b in itertools.combinations(ids,2))
    if cross_hom or cross_study:
        blockers.append('Cross-fold homology or primary measurement study overlap')
    for fold in range(3):
        train=roles[(roles.fold==fold)&roles.role.eq('train')]
        valid=roles[(roles.fold==fold)&roles.role.eq('validation')]
        if set(train.sample_id)&set(valid.sample_id) or set(train.sample_id)|set(valid.sample_id)!=set(ids):
            blockers.append(f'Fold {fold} role coverage differs')
        if len(train)!=len(set(train.sample_id)) or len(valid)!=len(set(valid.sample_id)):
            blockers.append(f'Fold {fold} duplicates roles')
        if set(train.amp.astype(int))!={0,1} or set(valid.amp.astype(int))!={0,1}:
            blockers.append(f'Fixed fold {fold} lacks a class')
    return {'status':'blocked' if blockers else 'passed', 'generated_at':utc_now(),
            'molecules':len(ids),'observations':len(assays),'pairs_recomputed':len(pairs),
            'cross_fold_homology_edges':int(cross_hom),'cross_fold_primary_studies':int(cross_study),
            'blockers':blockers,'model_fitting_performed':False}


def prepare(output: Path) -> dict:
    output=output.resolve()
    if output.exists(): raise FileExistsError(output)
    if not output.is_relative_to(ROOT/'03_experiments/audits'): raise ValueError('Audit output must remain in workspace')
    ctx=_check_inputs()
    prior=read_json(PRIOR_STATE)
    for path, expected in prior['inputs'].items():
        if sha256(ROOT/path)!=expected: raise ValueError('Previous state binding changed: '+path)
    acquisition=read_json(RETRIEVAL/'acquisition.json')
    if sha256(FIGURE)!=FIGURE_SHA or sha256(XML)!=acquisition['source_xml_sha256']:
        raise ValueError('Visually reviewed original figure/XML differs')
    acquired=next(r for r in acquisition['attempts'] if r['id']=='bmap_figure_1')
    if not acquired['verified_original_document'] or acquired['sha256']!=FIGURE_SHA:
        raise ValueError('Original figure retrieval is not certified')
    old=ctx['old_release_dir']
    verify_manifest(old)
    sources=pd.read_csv(old/'source_review.csv',keep_default_na=False)
    reviewed=pd.read_csv(old/'molecule_evidence_review.csv',keep_default_na=False)
    assays=pd.read_csv(old/'assay_evidence_review.csv',keep_default_na=False)
    molecules=pd.read_csv(BASELINE/'candidate_molecules.csv',keep_default_na=False)
    bmap=ctx['molecules17'][ctx['molecules17'].sample_id.eq(BMAP_ID)].iloc[0]
    xml_rel=XML.relative_to(ROOT).as_posix(); fig_rel=FIGURE.relative_to(ROOT).as_posix()
    molecular_basis='Section mlf270020-sec-0170 explicitly gives the sequence, Wang resin and final Fmoc removal. Free N terminus follows that final deprotection; C-terminal acid follows Wang resin cleavage. No subsequent covalent capping is reported.'
    limitations='Raw mass spectrum and supplementary document were not obtained; no contents of those missing files are assumed. MIC unit is stated in results section mlf270020-sec-0030 and tied to Figure 1. Review is by agent, not independent human signoff.'
    source={c:'' for c in sources.columns}
    source.update(source_id='bmap2025',primary_file=xml_rel,sha256=sha256(XML),source_url='https://doi.org/10.1002/mlf2.70020',primary_locations='XML sections mlf270020-sec-0030, -0170, -0180; Figure 1 CREC6 row and BMAP-27B column',molecular_evidence=molecular_basis,method_evidence='Primary MIC assay described in same article; conditions separately recorded',limitations_and_scope=limitations)
    sources=pd.concat([sources,pd.DataFrame([source])],ignore_index=True)
    assay={c:'' for c in assays.columns}
    assay.update(sample_id=BMAP_ID,record_id='bmap2025:Figure1:CREC6',source_dataset='original_primary_article',assay_index=0,target='Escherichia coli CREC6',medium='Mueller-Hinton Broth (MHB)',method='CLSI broth microdilution',raw_mic='3.125',raw_unit='µg/ml',normalized_low_ug_ml=3.125,normalized_high_ug_ml=3.125,eligible=True,reference_resolution='original_figure_numeric_cell',assay_study_ids='doi:10.1002/mlf2.70020|pmid:40600060|pmcid:PMC12207908',source_id='bmap2025',primary_peptide_name='BMAP-27B',sequence=bmap.seq,primary_file=fig_rel,primary_file_sha256=FIGURE_SHA,primary_locations='Figure 1, CREC6 row (purple outline), BMAP-27B column: explicit number 3.125; units from XML section mlf270020-sec-0030',primary_method_conditions='MHB; broth microdilution; article sections -0180 and -0030',condition_limitations=limitations,raw_value_unit_target_rechecked=True,decision='passed_primary_evidence')
    assay['derived_label']=label_of(assay,bmap.seq)
    assays=pd.concat([assays,pd.DataFrame([assay])],ignore_index=True)
    molecule={c:'' for c in reviewed.columns}
    molecule.update(sample_id=BMAP_ID,sequence=bmap.seq,source_id='bmap2025',primary_peptide_name='BMAP-27B',primary_file=xml_rel,primary_file_sha256=sha256(XML),primary_locations='XML mlf270020-sec-0170 sequence and terminal deprotection; Figure 1 CREC6 row',molecular_form=FORM,molecular_evidence=molecular_basis,condition_limitations=limitations,derived_label=assay['derived_label'],observations_rechecked=1,decision='passed_primary_evidence',human_reviewer_signoff='not_claimed')
    reviewed=pd.concat([reviewed,pd.DataFrame([molecule])],ignore_index=True)
    new_m={c:'' for c in molecules.columns}
    new_m.update(sample_id=BMAP_ID,seq=bmap.seq,amp=assay['derived_label'],record_ids=json.dumps([assay['record_id']]),source_datasets='original_primary_article',study_ids=assay['assay_study_ids'])
    molecules=pd.concat([molecules,pd.DataFrame([new_m])],ignore_index=True)
    if not molecules.sample_id.is_unique or not molecules.seq.is_unique: raise ValueError('Duplicate molecule requires explicit aggregation')
    labels=ensure_consistent(assays,molecules.set_index('sample_id').seq.to_dict())
    molecules.amp=molecules.sample_id.map(labels).astype(int)
    aliases=aliases_for(molecules,assays,sources)
    pairs=[{'sample_id_a':a.sample_id,'sample_id_b':b.sample_id,'identity':sequence_identity(a.seq,b.seq,identity_mode='alignment')}
           for a,b in itertools.combinations(molecules.itertuples(index=False),2)]
    components=graph_components(molecules.sample_id.tolist(),pairs,aliases)
    molecules['component']=molecules.sample_id.map(components)
    positive=set(molecules.loc[molecules.amp.eq(1),'component']);negative=set(molecules.loc[molecules.amp.eq(0),'component'])
    counts={'total':len(set(components.values())),'positive':len(positive),'negative':len(negative)}
    if min(counts.values())<3: raise ValueError('Independent components insufficient for fixed three folds')
    roles=[]
    splitter=StratifiedGroupKFold(n_splits=3,shuffle=True,random_state=42)
    for fold,(train,valid) in enumerate(splitter.split(np.zeros((len(molecules),1)),molecules.amp.to_numpy(),molecules.component.to_numpy())):
        for role,positions in [('train',train),('validation',valid)]:
            roles.extend({'sample_id':molecules.iloc[i].sample_id,'fold':fold,'role':role,'amp':int(molecules.iloc[i].amp),'component':int(molecules.iloc[i].component)} for i in positions)
    role_table=pd.DataFrame(roles);pair_table=pd.DataFrame(pairs)
    independent=audit_partition(molecules,assays,sources,role_table,pair_table)
    output.mkdir(parents=True)
    cohort_dir=output/'cohort';evidence_dir=output/'evidence';cohort_dir.mkdir();evidence_dir.mkdir()
    for name,table in [('candidate_molecules.csv',molecules),('candidate_observations.csv',assays),('fold_roles.csv',role_table),('all_member_similarity.csv',pair_table)]:
        table.to_csv(cohort_dir/name,index=False,encoding='utf-8-sig')
    for name,table in [('source_review.csv',sources),('molecule_evidence_review.csv',reviewed),('assay_evidence_review.csv',assays)]:
        table.to_csv(evidence_dir/name,index=False,encoding='utf-8-sig')
    decisions=pd.DataFrame([{'sample_id':BMAP_ID,'decision':'passed_primary_evidence','new_record_id':assay['record_id'],'reason':'Original numeric CREC6 cell and terminal identity supported; no aggregate range used'}, {'sample_id':PISCIDIN_ID,'decision':'withheld_actual_assay_n_terminus_unverified','new_record_id':'','reason':'Actual UTSW antimicrobial sample N terminus remains unverified; materials section is physical PDF page 3 (journal p.1361); Table 1 is physical page 5 (p.1363)'}])
    decisions.to_csv(output/'candidate_decisions.csv',index=False,encoding='utf-8-sig')
    bound=[PRIOR_STATE,Path(__file__),XML,FIGURE,RETRIEVAL/'acquisition.json',old/'manifest.json']
    inputs={p.relative_to(ROOT).as_posix():sha256(p) for p in bound}
    cohort={'status':'passed' if independent['status']=='passed' else 'blocked','generated_at':utc_now(),'molecules':len(molecules),'observations':len(assays),'component_counts':counts,'fold_structure_gate_passed':independent['status']=='passed','cross_fold_homology_edges':independent['cross_fold_homology_edges'],'cross_fold_primary_studies':independent['cross_fold_primary_studies'],'validation':{'folds':3,'shuffle':True,'seed':42},'candidate_selection_after_split':False,'inputs':inputs,'outputs':{p.name:sha256(p) for p in cohort_dir.iterdir()}}
    write_json(cohort_dir/'manifest.json',cohort)
    release={'status':'passed_for_local_exploratory_training_protocol_review','generated_at':utc_now(),'full_release_review_complete':True,'molecules_evidence_approved':len(molecules),'observations_evidence_approved':len(assays),'cohort_manifest_sha256':sha256(cohort_dir/'manifest.json'),'primary_review_mode':'agent_original_figure_review_with_independent_label_arithmetic','independent_human_review_claimed':False,'new_candidates_released':1,'records_released_for_training':0,'training_started':False,'inputs':{**inputs,(cohort_dir/'manifest.json').relative_to(ROOT).as_posix():sha256(cohort_dir/'manifest.json')},'outputs':{p.name:sha256(p) for p in evidence_dir.iterdir()}}
    write_json(evidence_dir/'manifest.json',release)
    independent['inputs']={(cohort_dir/'manifest.json').relative_to(ROOT).as_posix():sha256(cohort_dir/'manifest.json'),(evidence_dir/'manifest.json').relative_to(ROOT).as_posix():sha256(evidence_dir/'manifest.json')}
    write_json(output/'partition_audit.json',independent)
    manifest={'status':'ready_for_protocol_freeze' if independent['status']=='passed' else 'fixed_split_blocked','generated_at':utc_now(),'candidate_molecules_reviewed':17,'molecules_evidence_approved':len(molecules),'observations_evidence_approved':len(assays),'new_candidates_reviewed':2,'new_candidates_released':1,'primary_evidence_gate':'passed','fixed_partition_gate':independent['status'],'blockers':independent['blockers'],'training_started':False,'inputs':inputs,'outputs':{p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()}}
    write_json(output/'manifest.json',manifest)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    result=prepare(args.output)
    print(json.dumps({k:v for k,v in result.items() if k not in {'inputs','outputs'}},ensure_ascii=False,indent=2))
