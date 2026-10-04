"""Provenance validation and all-member homology-separated research partitions.

The alignment is an explicitly defined Needleman-Wunsch implementation, not CD-HIT.
Connected components keep every above-cutoff pair in the same partition. A giant
component or insufficient class coverage is a failed feasibility check, not license
to relax the cutoff or silently discard observations.
"""
import argparse
from collections import Counter
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from feature_extractor import clean_sequence
from research_utils import ROOT, sha256, write_json, utc_now

TASKS = ('amp', 'hemo')
REQUIRED = ('record_id', 'seq', 'amp', 'hemo', 'source_dataset', 'source_accession',
            'source_url', 'evidence_reference', 'label_basis', 'assay_conditions',
            'modifications', 'evidence_type', 'is_synthetic', 'source_role', 'raw_path', 'raw_sha256')

class ResearchDataError(ValueError):
    def __init__(self, message, evidence_audit=None):
        super().__init__(message)
        self.evidence_audit = evidence_audit

def validate_records(frame, verify_raw=True):
    missing = set(REQUIRED) - set(frame.columns)
    if missing:
        raise ResearchDataError('Missing provenance columns: ' + ', '.join(sorted(missing)))
    df = frame.copy()
    if df.empty or df.record_id.isna().any() or df.record_id.duplicated().any():
        raise ResearchDataError('Record identifiers must be present, unique and nonempty.')
    for col in set(REQUIRED) - set(TASKS):
        if df[col].isna().any() or df[col].astype(str).str.strip().eq('').any():
            raise ResearchDataError(f'Missing evidence in {col}.')
    if not df.is_synthetic.astype(str).str.lower().isin(['false', '0']).all():
        raise ResearchDataError('Synthetic records cannot enter research evaluation.')
    if not df.evidence_type.eq('experimental').all():
        raise ResearchDataError('Only experimental evidence is accepted; unannotated is not negative.')
    if not df.modifications.eq('none').all():
        raise ResearchDataError('Modified peptides need a separately specified representation.')
    if not df.source_role.isin(['development', 'external']).all():
        raise ResearchDataError('Unknown source role.')
    for task in TASKS:
        df[task] = pd.to_numeric(df[task], errors='raise')
        if not df[task].dropna().isin([0, 1]).all():
            raise ResearchDataError('Observed labels must be binary; unknown labels must be blank.')
        observed=df[task].notna()
        if task+'_observed' in df and not df[task+'_observed'].astype(str).str.lower().eq('true').equals(observed):
            raise ResearchDataError('Observed-label flag disagrees with missing label state.')
        df[task+'_observed']=observed
    if df[list(TASKS)].isna().all(axis=1).any():
        raise ResearchDataError('Every included record needs at least one measured endpoint.')
    df['seq'] = df.seq.map(clean_sequence)
    if not df.seq.str.len().between(10, 50).all():
        raise ResearchDataError('Prespecified research domain is 10–50 canonical residues.')
    if verify_raw:
        from evidence_validation import validate_source_evidence
        validate_source_evidence(df)
    return df

def consolidate_records(df):
    """Merge identical molecules; conflicting measured labels become unknown."""
    rows, excluded = [], []
    for seq, group in df.groupby('seq', sort=True):
        labels = {}
        conflicts = []
        for task in TASKS:
            observed = group[task].dropna().unique()
            labels[task] = float(observed[0]) if len(observed) == 1 else np.nan
            if len(observed) > 1:
                conflicts.append(task)
        if len(set(group.source_role)) > 1:
            excluded.append({'record_ids': group.record_id.tolist(), 'reason': 'exact development/external overlap'})
            continue
        if all(pd.isna(v) for v in labels.values()):
            excluded.append({'record_ids': group.record_id.tolist(), 'reason': 'no unambiguous label'})
            continue
        rows.append({'sample_id': hashlib.sha256(seq.encode()).hexdigest()[:24], 'seq': seq, **labels,
                     **{task+'_observed':not pd.isna(labels[task]) for task in TASKS},
                     'source_role': group.source_role.iloc[0],
                     'source_datasets': '|'.join(sorted(set(group.source_dataset))),
                     'record_ids': json.dumps(group.record_id.tolist()), 'conflicts': '|'.join(conflicts)})
    return pd.DataFrame(rows), excluded

def sequence_length_ratio(a: str, b: str) -> float:
    if not a or not b:
        raise ResearchDataError('Empty sequence cannot have length ratio.')
    return min(len(a), len(b)) / max(len(a), len(b))

def sequence_identity(a, b, *, identity_mode='min'):
    """Global NW identity with a frozen traceback and explicit denominator."""
    if not a or not b:
        raise ResearchDataError('Empty sequence cannot be aligned.')
    if identity_mode not in ('min', 'max', 'alignment'):
        raise ResearchDataError(f"Unknown identity_mode: '{identity_mode}', expected 'min', 'max' or 'alignment'.")
    # Canonical orientation makes traceback tie handling symmetric.
    if a > b:
        a, b = b, a
    n, m = len(a), len(b)
    # Track the traceback-equivalent number of matches, preferring diagonal ties.
    prev = [-2*j for j in range(m+1)]
    pm = [0]*(m+1)
    pl = list(range(m+1))
    for i, aa in enumerate(a, 1):
        cur, cm = [-2*i] + [0]*m, [0]*(m+1)
        cl = [i] + [0]*m
        for j, bb in enumerate(b, 1):
            diag = prev[j-1] + (2 if aa == bb else -1)
            up, left = prev[j]-2, cur[j-1]-2
            if diag >= up and diag >= left:
                cur[j], cm[j] = diag, pm[j-1] + (aa == bb)
                cl[j] = pl[j-1] + 1
            elif up >= left:
                cur[j], cm[j] = up, pm[j]
                cl[j] = pl[j] + 1
            else:
                cur[j], cm[j] = left, cm[j-1]
                cl[j] = cl[j-1] + 1
        prev, pm, pl = cur, cm, cl
    matches = pm[-1]
    denom = {'min': min(n, m), 'max': max(n, m), 'alignment': pl[-1]}[identity_mode]
    return matches / denom

def homology_components(sequences, cutoff=0.40, *, identity_mode='min'):
    if not 0 < cutoff <= 1:
        raise ResearchDataError('Identity cutoff must be in (0, 1].')
    parent = list(range(len(sequences)))
    counts = [Counter(s) for s in sequences]
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    if identity_mode not in ('min', 'max', 'alignment'):
        raise ResearchDataError(f'Unknown identity mode: {identity_mode}')
    checked, edges = 0, 0
    for i, a in enumerate(sequences):
        for j in range(i):
            denom = min(len(a), len(sequences[j])) if identity_mode == 'min' else max(len(a), len(sequences[j]))
            if sum((counts[i] & counts[j]).values()) / denom < cutoff:
                continue
            checked += 1
            if sequence_identity(a, sequences[j], identity_mode=identity_mode) >= cutoff:
                parent[find(i)] = find(j)
                edges += 1
    roots = [find(i) for i in range(len(parent))]
    ids = {v: k for k, v in enumerate(sorted(set(roots)))}
    return np.array([ids[r] for r in roots]), {
        'possible_pairs': len(sequences) * (len(sequences) - 1) // 2,
        'aligned_pairs': checked, 'above_cutoff_pairs': edges, 'groups': len(ids),
        'identity_mode': identity_mode,
    }

def source_study_ids(row):
    """Extract DOI/PMID identifiers from a record's declared primary references."""
    refs = str(row.evidence_reference)
    identifiers = {f'doi:{doi.lower().rstrip(".,;)}")}' for doi in re.findall(r'10\.\d{4,9}/[^\s"<>]+', refs, re.I)}
    identifiers.update(f'pmid:{pmid}' for pmid in re.findall(r'PMID\s*[:=]\s*(\d+)', refs, re.I))
    try:
        payload = json.loads(refs)
    except (TypeError, ValueError):
        payload = None

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() == 'doi' and item:
                    identifiers.add(f'doi:{str(item).lower().strip()}')
                elif key.lower() in ('pubmedid', 'pmid') and item:
                    identifiers.add(f'pmid:{str(item).strip()}')
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(payload)
    return identifiers

def assert_study_independence(records):
    """External records must not reuse a development cohort's primary study."""
    dev_studies = set().union(*(source_study_ids(row) for row in records[records.source_role.eq('development')].itertuples()))
    for row in records[records.source_role.eq('external')].itertuples():
        overlap = source_study_ids(row) & dev_studies
        if overlap:
            raise ResearchDataError(f'External record {row.record_id} shares a development study: {sorted(overlap)}')

def analyze_homology(records, spec):
    """Build all-member components and retain every development/external pair score."""
    df, exclusions = consolidate_records(records)
    if df.empty:
        raise ResearchDataError('No eligible molecules after consolidation.')
    if spec.clustering_method == 'transitive':
        cluster_ids, summary = homology_components(
            df.seq.tolist(), spec.cutoff, identity_mode=spec.membership_identity
        )
        df['cluster_id'] = cluster_ids
        df['representative_sample_id'] = df['sample_id']
    elif spec.clustering_method == 'greedy_nw':
        from cdhit_cluster import cdhit_cluster_sequences
        cluster_ids, reps, summary = cdhit_cluster_sequences(
            df.seq.tolist(), cutoff=spec.cutoff, min_length_ratio=spec.min_length_ratio
        )
        df['cluster_id'] = cluster_ids
        rep_map = {c_idx: df.loc[df.seq.eq(rep_seq), 'sample_id'].iloc[0] for c_idx, rep_seq in enumerate(reps)}
        df['representative_sample_id'] = df['cluster_id'].map(rep_map)
    else:
        raise ResearchDataError(f'Unknown clustering method: {spec.clustering_method}')

    pairs = []
    dev = df[df.source_role.eq('development')]
    ext = df[df.source_role.eq('external')]
    for a in ext.itertuples():
        for b in dev.itertuples():
            identity = sequence_identity(a.seq, b.seq, identity_mode=spec.cross_identity)
            pairs.append({
                'external_sample_id': a.sample_id,
                'development_sample_id': b.sample_id,
                'identity': identity,
                'violates_cutoff': identity >= spec.cutoff,
            })
    cross_pairs = pd.DataFrame(pairs, columns=[
        'external_sample_id', 'development_sample_id', 'identity', 'violates_cutoff'
    ])
    audit = {
        'protocol_id': spec.protocol_id,
        'identity_mode': spec.cross_identity,
        'cutoff': spec.cutoff,
        'development_samples': len(dev),
        'external_samples': len(ext),
        'cross_pairs_evaluated': len(cross_pairs),
        'cross_pair_violations': int(cross_pairs.violates_cutoff.sum()),
        'clustering_summary': summary,
        'largest_cluster': int(df.groupby('cluster_id').size().max()),
    }
    return df, exclusions, cross_pairs, audit

def assert_cross_isolation(left, right, cutoff=0.40, *, protocol=None):
    if protocol is None:
        mode = 'min'
        scope = 'all_members'
        min_len_ratio = 0.0
    else:
        if isinstance(protocol, str):
            from research_protocol_config import get_protocol
            spec = get_protocol(protocol)
        else:
            spec = protocol
        mode = spec.cross_identity
        scope = spec.cross_scope
        cutoff = spec.cutoff
        min_len_ratio = spec.min_length_ratio

    if scope == 'all_members':
        for a in left.itertuples():
            ca = Counter(a.seq)
            for b in right.itertuples():
                if min_len_ratio > 0 and sequence_length_ratio(a.seq, b.seq) < min_len_ratio:
                    continue
                denom = min(len(a.seq), len(b.seq)) if mode == 'min' else max(len(a.seq), len(b.seq))
                if sum((ca & Counter(b.seq)).values()) / denom < cutoff:
                    continue
                sim = sequence_identity(a.seq, b.seq, identity_mode=mode)
                if sim >= cutoff:
                    raise ResearchDataError(f'Cross-partition sequence similarity violates {cutoff}: {a.sample_id} / {b.sample_id}')
    elif scope == 'members_to_representatives':
        left_reps = left[left.sample_id == left.representative_sample_id] if 'representative_sample_id' in left else left
        right_reps = right[right.sample_id == right.representative_sample_id] if 'representative_sample_id' in right else right
        for a in left.itertuples():
            ca = Counter(a.seq)
            for r in right_reps.itertuples():
                if min_len_ratio > 0 and sequence_length_ratio(a.seq, r.seq) < min_len_ratio:
                    continue
                denom = min(len(a.seq), len(r.seq)) if mode == 'min' else max(len(a.seq), len(r.seq))
                if sum((ca & Counter(r.seq)).values()) / denom < cutoff:
                    continue
                sim = sequence_identity(a.seq, r.seq, identity_mode=mode)
                if sim >= cutoff:
                    raise ResearchDataError(f'Cross-partition sequence similarity violates {cutoff}: {a.sample_id} / rep {r.sample_id}')

def require_classes(df, context):
    for task in TASKS:
        if set(df[task].dropna().unique()) != {0, 1}:
            raise ResearchDataError(f'{context}: both measured classes required for {task}.')

def partition(df, folds=5, seed=42):
    if df.empty:
        raise ResearchDataError('No eligible experimental records.')
    out = df.copy()
    dev = out[out.source_role.eq('development')]
    ext = out[out.source_role.eq('external')]
    if ext.empty:
        raise ResearchDataError('A separately sourced external cohort is required.')
    col = 'source_datasets' if 'source_datasets' in dev else ('source_dataset' if 'source_dataset' in dev else None)
    if col:
        dev_sources = set('|'.join(dev[col].astype(str)).split('|'))
        ext_sources = set('|'.join(ext[col].astype(str)).split('|'))
        if dev_sources & ext_sources:
            raise ResearchDataError('External source cannot also supply development records.')
    if set(dev.cluster_id) & set(ext.cluster_id):
        raise ResearchDataError('Development/external cohorts contain homologous sequences.')
    if len(set(dev.cluster_id)) < folds+1:
        raise ResearchDataError('Insufficient independent homology groups for five-fold development plus holdout.')
    strata = dev.amp.fillna(-1).astype(int).astype(str) + '_' + dev.hemo.fillna(-1).astype(int).astype(str)
    outer = StratifiedGroupKFold(n_splits=folds+1, shuffle=True, random_state=seed)
    development_idx, test_idx = next(outer.split(dev, strata, dev.cluster_id))
    development, test = dev.iloc[development_idx], dev.iloc[test_idx]
    require_classes(development, 'Development'); require_classes(test, 'Independent test'); require_classes(ext, 'External test')
    out['split'], out['fold'] = 'external', -1
    out.loc[test.index, 'split'] = 'test'
    out.loc[development.index, 'split'] = 'development'
    labels = development.amp.fillna(-1).astype(int).astype(str) + '_' + development.hemo.fillna(-1).astype(int).astype(str)
    cv = StratifiedGroupKFold(n_splits=folds, shuffle=True, random_state=seed)
    for fold, (a, b) in enumerate(cv.split(development, labels, development.cluster_id)):
        require_classes(development.iloc[a], f'Fold {fold} training'); require_classes(development.iloc[b], f'Fold {fold} validation')
        out.loc[development.iloc[b].index, 'fold'] = fold
    return out

def validate_partition(df, cutoff=.40, *, protocol=None):
    if df.loc[df.split.eq('external'),'source_role'].ne('external').any() or df.loc[df.split.ne('external'),'source_role'].ne('development').any():
        raise ResearchDataError('Prepared split changed the declared source role.')
    if set(df.split) != {'development', 'test', 'external'}:
        raise ResearchDataError('Development, test and external partitions are required.')
    if set(df.loc[df.split.eq('development'), 'fold']) != set(range(5)):
        raise ResearchDataError('Exactly five development folds are required.')
    if df.sample_id.duplicated().any() or df.seq.duplicated().any():
        raise ResearchDataError('Duplicate molecule in prepared partitions.')
    groups = [df[df.split.eq(s)] for s in ['development','test','external']]
    for i, a in enumerate(groups):
        require_classes(a, ['development','test','external'][i])
        for b in groups[:i]:
            if set(a.cluster_id) & set(b.cluster_id):
                raise ResearchDataError('Cluster crosses dataset partition.')
            assert_cross_isolation(a, b, cutoff, protocol=protocol)
    dev=groups[0]
    for fold in range(5):
        a,b=dev[dev.fold.ne(fold)],dev[dev.fold.eq(fold)]
        require_classes(a, f'Fold {fold} training'); require_classes(b, f'Fold {fold} validation')
        if set(a.cluster_id) & set(b.cluster_id):
            raise ResearchDataError('Cluster crosses validation fold.')
        assert_cross_isolation(a, b, cutoff, protocol=protocol)

def build_partition_audit(df, spec, exclusions=None, summary=None):
    audit = {
        'protocol_id': spec.protocol_id,
        'cutoff': spec.cutoff,
        'cross_scope': spec.cross_scope,
        'cross_identity': spec.cross_identity,
        'min_length_ratio': spec.min_length_ratio,
        'sample_count': len(df),
        'cluster_count': int(df.cluster_id.nunique()),
        'splits': {},
        'folds': {},
        'clustering_summary': summary or {},
        'exclusions_count': len(exclusions or [])
    }
    for split_name in ['development', 'test', 'external']:
        sub = df[df.split == split_name]
        audit['splits'][split_name] = {
            'sample_count': len(sub),
            'cluster_count': int(sub.cluster_id.nunique()) if not sub.empty else 0,
            'amp': {
                'positive': int((sub.amp == 1).sum()),
                'negative': int((sub.amp == 0).sum()),
                'missing': int(sub.amp.isna().sum())
            },
            'hemo': {
                'positive': int((sub.hemo == 1).sum()),
                'negative': int((sub.hemo == 0).sum()),
                'missing': int(sub.hemo.isna().sum())
            }
        }
    dev = df[df.split == 'development']
    for fold in range(spec.folds):
        train = dev[dev.fold != fold]
        val = dev[dev.fold == fold]
        audit['folds'][f'fold_{fold}'] = {
            'train': {
                'sample_count': len(train),
                'cluster_count': int(train.cluster_id.nunique()),
                'amp': {'positive': int((train.amp == 1).sum()), 'negative': int((train.amp == 0).sum()), 'missing': int(train.amp.isna().sum())},
                'hemo': {'positive': int((train.hemo == 1).sum()), 'negative': int((train.hemo == 0).sum()), 'missing': int(train.hemo.isna().sum())},
            },
            'val': {
                'sample_count': len(val),
                'cluster_count': int(val.cluster_id.nunique()),
                'amp': {'positive': int((val.amp == 1).sum()), 'negative': int((val.amp == 0).sum()), 'missing': int(val.amp.isna().sum())},
                'hemo': {'positive': int((val.hemo == 1).sum()), 'negative': int((val.hemo == 0).sum()), 'missing': int(val.hemo.isna().sum())},
            }
        }
    return audit

def prepare_frame(records, protocol='protocol-amd-02'):
    if isinstance(protocol, str):
        from research_protocol_config import get_protocol, check_protocol_conflicts
        spec = get_protocol(protocol)
    else:
        from research_protocol_config import check_protocol_conflicts
        spec = protocol

    has_conflict, conflict_reason = check_protocol_conflicts(spec)
    if has_conflict:
        raise ResearchDataError(conflict_reason)

    if spec.protocol_id == 'protocol-amd-02':
        assert_study_independence(records)
    df, exclusions, cross_pairs, homology_audit = analyze_homology(records, spec)

    dev = df[df.source_role.eq('development')]
    ext = df[df.source_role.eq('external')]
    if ext.empty:
        raise ResearchDataError('A separately sourced external cohort is required.')
    if dev.empty:
        raise ResearchDataError('Development cohort is empty.')
    if homology_audit['cross_pair_violations']:
        raise ResearchDataError(f"Development/external all-member isolation failed for {homology_audit['cross_pair_violations']} pairs.")
    if dev.cluster_id.nunique() < spec.folds + 1:
        raise ResearchDataError(f'Insufficient independent homology groups for five-fold development plus holdout: found {dev.cluster_id.nunique()}, need {spec.folds+1}.')

    df = partition(df, folds=spec.folds, seed=spec.partition_seed)
    validate_partition(df, cutoff=spec.cutoff, protocol=spec)

    audit = build_partition_audit(df, spec, exclusions=exclusions, summary=homology_audit['clustering_summary'])
    audit['cross_pairs_evaluated'] = len(cross_pairs)
    return df, audit

def prepare(records_path, output_dir, cutoff=.40, *, protocol_id='protocol-amd-02'):
    output = Path(output_dir)
    if output.exists():
        raise ResearchDataError('Output exists; use a new versioned preparation directory.')
    from research_protocol_config import get_protocol, protocol_digest, check_protocol_conflicts
    from dataclasses import asdict
    spec = get_protocol(protocol_id)
    if cutoff != spec.cutoff:
        raise ResearchDataError(f'Requested cutoff {cutoff} contradicts protocol cutoff {spec.cutoff}.')

    output.mkdir(parents=True)
    report = {
        'schema_version': 2,
        'status': 'blocked',
        'created_at': utc_now(),
        'protocol_id': spec.protocol_id,
        'protocol_spec': asdict(spec),
        'protocol_digest': protocol_digest(spec),
        'records_input_sha256': sha256(records_path),
        'cutoff': spec.cutoff,
        'identity_definition': (
            f'{spec.alignment}; matches/aligned_columns; gap_columns_are_mismatches'
            if spec.protocol_id == 'protocol-amd-02' else spec.alignment
        ),
        'folds': spec.folds,
        'seed': spec.partition_seed,
        'feasibility_blockers': [],
    }

    try:
        raw_df = pd.read_csv(records_path)
        records = validate_records(raw_df, verify_raw=False)
        from evidence_validation import validate_source_evidence
        evidence_audit = validate_source_evidence(records)
        write_json(output / 'evidence_audit.json', evidence_audit)
        report['evidence_audit_sha256'] = sha256(output / 'evidence_audit.json')

        has_conflict, conflict_reason = check_protocol_conflicts(spec)
        if has_conflict:
            report['feasibility_blockers'].append(conflict_reason)
            raise ResearchDataError(conflict_reason)

        if spec.protocol_id == 'protocol-amd-02':
            assert_study_independence(records)
        df, exclusions, cross_pairs, homology_audit = analyze_homology(records, spec)
        report['sample_count'] = len(df)
        report['development_samples'] = homology_audit['development_samples']
        report['external_samples'] = homology_audit['external_samples']
        report['cluster_count'] = homology_audit['clustering_summary']['groups']
        report['largest_cluster'] = homology_audit['largest_cluster']
        cluster_cols = ['sample_id', 'cluster_id', 'representative_sample_id']
        df[cluster_cols].to_csv(output / 'cluster_membership.csv', index=False)
        write_json(output / 'exclusions.json', exclusions)
        records.to_csv(output / 'records.csv', index=False)
        report['cluster_membership_sha256'] = sha256(output / 'cluster_membership.csv')
        report['exclusions_sha256'] = sha256(output / 'exclusions.json')
        report['provenance_sha256'] = sha256(output / 'records.csv')
        if spec.protocol_id == 'protocol-amd-02':
            cross_pairs.to_csv(output / 'cross_cohort_similarity.csv', index=False)
            write_json(output / 'homology_audit.json', homology_audit)
            report['cross_cohort_similarity_sha256'] = sha256(output / 'cross_cohort_similarity.csv')
            report['homology_audit_sha256'] = sha256(output / 'homology_audit.json')

        dev = df[df.source_role.eq('development')]
        ext = df[df.source_role.eq('external')]
        if ext.empty:
            raise ResearchDataError('A separately sourced external cohort is required.')
        if dev.empty:
            raise ResearchDataError('Development cohort is empty.')
        if homology_audit['cross_pair_violations']:
            raise ResearchDataError(f"Development/external all-member isolation failed for {homology_audit['cross_pair_violations']} pairs.")
        if dev.cluster_id.nunique() < spec.folds + 1:
            raise ResearchDataError(f'Insufficient independent homology groups for five-fold development plus holdout: found {dev.cluster_id.nunique()}, need {spec.folds+1}.')

        df = partition(df, folds=spec.folds, seed=spec.partition_seed)
        validate_partition(df, cutoff=spec.cutoff, protocol=spec)
        audit = build_partition_audit(df, spec, exclusions=exclusions, summary=homology_audit['clustering_summary'])
        audit['cross_pairs_evaluated'] = len(cross_pairs)
        write_json(output / 'partition_audit.json', audit)
        df.to_csv(output / 'dataset.csv', index=False)

        report.update({
            'status': 'validated',
            'sample_count': len(df),
            'dataset_sha256': sha256(output / 'dataset.csv'),
            'partition_audit_sha256': sha256(output / 'partition_audit.json'),
        })
    except (ValueError, KeyError, ResearchDataError) as exc:
        report['reason'] = str(exc)
        if hasattr(exc, 'evidence_audit') and exc.evidence_audit:
            write_json(output / 'evidence_audit.json', exc.evidence_audit)
        if str(exc) not in report['feasibility_blockers']:
            report['feasibility_blockers'].append(str(exc))
        write_json(output / 'manifest.json', report)
        raise ResearchDataError(str(exc)) from exc

    write_json(output / 'manifest.json', report)
    return report

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--protocol-id', type=str, default='protocol-amd-02', choices=['legacy-v1', 'protocol-amd-01', 'protocol-amd-02'])
    p.add_argument('--cutoff', type=float, default=0.40)
    args = p.parse_args()
    try:
        print(json.dumps(prepare(args.records, args.output, cutoff=args.cutoff, protocol_id=args.protocol_id), ensure_ascii=False))
    except ResearchDataError as exc:
        p.exit(2, str(exc) + '\n')

if __name__ == '__main__':
    main()
