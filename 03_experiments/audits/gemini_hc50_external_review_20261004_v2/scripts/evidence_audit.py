"""Local evidence repair. No training, network requests, or formal release."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import platform
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[4]
BUNDLE = Path(__file__).resolve().parents[1]
RAW = BUNDLE / 'raw'
sys.path.insert(0, str(ROOT / '02_code'))
from research_data import sequence_identity
from public_data import measurement_label

EXPECTED_DEV = 'ccec346bf88c6d3b2da57f058019fb10305019de5dca4ef3402949931ac71f37'
PMC_FILES = ('PMC13515218', 'PMC13510277', 'PMC13436381', 'PMC13216044', 'PMC12412326')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_bindings(root, bindings):
    files = bindings.get('files', {})
    required = bindings.get('required_files', [])
    if not required or not files or not set(required).issubset(files):
        raise ValueError('Input coverage incomplete')
    for name, digest in files.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or Path(name).is_absolute():
            raise ValueError('Input path escape')
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f'SHA256 mismatch: {name}')


def load_inputs(manifest, anchor):
    if sha(manifest) != anchor:
        raise ValueError('Input manifest anchor mismatch')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    verify_bindings(ROOT, data)
    roles = data['roles']
    mandatory = set(roles.values()) | {(RAW / f'{p}.xml').relative_to(ROOT).as_posix() for p in PMC_FILES}
    if not mandatory.issubset(data['required_files']):
        raise ValueError('Primary source or table coverage incomplete')
    if sha(ROOT / roles['development_records']) != EXPECTED_DEV:
        raise ValueError('Frozen development input differs')
    verify_bindings(ROOT, {'files': data['protected_v1'], 'required_files': list(data['protected_v1'])})
    return data


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def text(node):
    if node is None:
        raise ValueError('Required primary source location missing')
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()


def table(root, identifier):
    node = root.find(f".//table-wrap[@id='{identifier}']")
    text(node)
    return node


def rows(node):
    return [[text(c) for c in row if c.tag in ('td', 'th')] for row in node.findall('.//tr')]


def unique(items, description):
    if len(items) != 1:
        raise ValueError(f'Ambiguous/missing primary extraction: {description}')
    return items[0]


def named_row(node, name):
    return unique([r for r in rows(node) if r and r[0].casefold() == name.casefold()], name)


def section(root, identifier):
    return text(root.find(f".//sec[@id='{identifier}']"))


def paragraph(root, required):
    return unique([text(p) for p in root.findall('.//p') if all(s in text(p) for s in required)], 'paragraph ' + str(required))


def observation(endpoint, target, raw, unit, location, conditions='not_reported', reviewed=True):
    return dict(endpoint=endpoint, target=target, raw_value=raw, unit=unit,
                source_location=location, conditions=conditions, reviewed=reviewed)


def read_primary(raw_dir):
    result = []
    for pmcid in PMC_FILES:
        path = raw_dir / f'{pmcid}.xml'
        root = ET.parse(path).getroot()
        ids = {n.get('pub-id-type'): text(n) for n in root.findall('.//front/article-meta/article-id')}
        if ids.get('pmcid') != pmcid:
            raise ValueError('Primary article ID mismatch')
        c = dict(candidate_id='PMC_' + ids['pmid'], source_db='PMC', pmcid=pmcid,
                 pmid=ids['pmid'], doi=ids['doi'], source_file=path.relative_to(ROOT).as_posix(),
                 sequence='', sequence_verified=False, molecular_form='unresolved',
                 molecular_mass='', mass_basis='not_verified', source_reviewed=True, assays=[])
        if pmcid == 'PMC13515218':
            c.update(name='Dermatoxin-PD1', sequence=named_row(table(root, 'molecules-31-02748-t001'), 'dermatoxin-PD1')[1].removesuffix('-NH2'),
                     sequence_location='molecules-31-02748-t001/dermatoxin-PD1/Sequence', molecular_form='c_terminal_amide')
            for row in rows(table(root, 'molecules-31-02748-t002')):
                if row and row[0].startswith('E. coli'):
                    c['assays'].append(observation('MIC', row[0].replace('E. coli', 'Escherichia coli '), row[1].split('/')[0], 'µM',
                                                  f'molecules-31-02748-t002/{row[0]}/Dermatoxin-PD1/MIC',
                                                  'See original methods; not inferred from database defaults'))
            method = section(root, 'sec4dot11dot1-molecules-31-02748')
            if 'horse erythrocytes' not in method:
                raise ValueError('Dermatoxin RBC species assertion failed')
            hrow = named_row(table(root, 'molecules-31-02748-t004'), 'Dermatoxin-PD1')
            c['assays'].append(observation('HC50', 'Horse erythrocytes', hrow[1], 'µM',
                                          'molecules-31-02748-t004/Dermatoxin-PD1/HC50; sec4dot11dot1-molecules-31-02748', method))
        elif pmcid == 'PMC13510277':
            row = named_row(table(root, 'antibiotics-15-00813-t001'), 'D-TN6')
            c.update(name='D-TN6', sequence=row[1], sequence_location='antibiotics-15-00813-t001/D-TN6/Sequence', molecular_form='D_residue_peptide')
            c['assays'] = [observation('MIC', 'Escherichia coli ATCC 25922', row[3], 'µg/ml', 'antibiotics-15-00813-t001/D-TN6/E. coli ATCC 25922'),
                           observation('not_reported', 'RBC assay not found in reviewed XML', '', '', 'reviewed XML; IC50 cell assays are not RBC HC50')]
        elif pmcid == 'PMC13436381':
            c.update(name='Arg2MP-C', sequence=named_row(table(root, 'T1'), 'Arg2MP-C')[1].removesuffix('-NH2'),
                     sequence_location='T1/Arg2MP-C/Sequence', molecular_form='c_terminal_amide')
            t2 = rows(table(root, 'T2'))
            headings = unique([r for r in t2 if 'Arg2MP-C' in r], 'Arg2MP-C MIC column')
            erow = unique([r for r in t2 if r and r[0] == 'E. coli'], 'E. coli MIC row')
            method = section(root, 's2-6-2')
            if 'rabbit blood' not in method:
                raise ValueError('Arg2MP-C RBC species assertion failed')
            htext = paragraph(root, ['HC', '372.3', '35.57'])
            hvalue = re.search(r'372\.3\s*[±]\s*35\.57', htext).group()
            c['assays'] = [observation('MIC', 'Escherichia coli; Table 2 does not state strain ID', erow[headings.index('Arg2MP-C') + 1].split('/')[0], 'µM', 'T2/E. coli/Arg2MP-C/MIC', section(root, 's2-3')),
                           observation('HC50', 'Rabbit erythrocytes', hvalue, 'µM', 'Results HC50 paragraph/Arg2MP-C; s2-6-2', method)]
        elif pmcid == 'PMC13216044':
            erow = unique([r for r in rows(table(root, 'tab1')) if r and 'Escherichia coli' in r[0]], 'Han-Def1 E. coli row')
            c.update(name='Han-Def1/rDef1', sequence_location='Figures 1/2; tested recombinant construct sequence not confirmed from archived XML', molecular_form='recombinant_identity_unresolved')
            c['assays'] = [observation('MIC', erow[0], erow[1], '', 'tab1/Escherichia coli/Def1/MIC'),
                           observation('HC50', 'Sheep erythrocytes', '>750', 'µg/ml', 'sec22/HC50 >750 ug/mL', section(root, 'sec12'))]
            if 'No effect' != erow[1] or '750' not in section(root, 'sec22'):
                raise ValueError('Han-Def1 original endpoint assertion failed')
        else:
            t1 = table(root, 'cimb-47-00673-t001')
            seq = unique(re.findall(r'[ACDEFGHIKLMNPQRSTVWY]{10,50}', text(t1)), 'Brevinin sequence')
            mass = float(named_row(t1, 'Molecular weight')[1])
            c.update(name='Brevinin-1 E8.13', sequence=seq, sequence_location='cimb-47-00673-t001/thead',
                     molecular_form='c_terminal_amide; Rana-box motif reported; covalent topology not independently confirmed',
                     molecular_mass=mass, mass_basis='primary Table 1 reported molecular weight; mass convention not specified')
            header = unique([r for r in rows(table(root, 'cimb-47-00673-t003')) if 'E. coli' in r], 'Brevinin MIC header')
            mrow = named_row(table(root, 'cimb-47-00673-t003'), 'Brevinin-1 E8.13')
            hsec = section(root, 'sec3dot6-cimb-47-00673')
            hc50 = unique(re.findall(r'HC\s*50\).*?determined to be ([\d.]+)\s*[μµ]M', hsec), 'Brevinin HC50')
            c['assays'] = [observation('MIC', 'Escherichia coli hospital isolate; individual isolate ID not reported', mrow[header.index('E. coli')], 'µM', 'cimb-47-00673-t003/Brevinin-1 E8.13/E. coli', section(root, 'sec2dot5-cimb-47-00673')),
                           observation('HC50', 'Human erythrocytes', hc50, 'µM', 'sec3dot6-cimb-47-00673/HC50; Figure 7', section(root, 'sec2dot7-cimb-47-00673'))]
        c['sequence_verified'] = bool(c['sequence'])
        result.append(c)
    return result


def is_human_hc50(a):
    return a['endpoint'] == 'HC50' and a['target'].casefold() == 'human erythrocytes' and a.get('reviewed') is True


def label_assay(a, c):
    result = dict(label='unknown', low_ugml='', high_ugml='', reason='unreviewed, disqualified or nonnumeric endpoint')
    if not a.get('reviewed') or (a['endpoint'] != 'MIC' and not is_human_hc50(a)):
        return result
    if a['endpoint'] == 'MIC' and not a['target'].startswith('Escherichia coli'):
        return result
    match = re.fullmatch(r'\s*([<>]=?)?\s*(\d+(?:\.\d+)?)\s*', a['raw_value'])
    if not match:
        return result
    comp, value = match.group(1) or '', float(match.group(2))
    unit = a['unit'].lower().replace('μ', 'µ')
    if unit in ('µg/ml', 'ug/ml', 'mg/l'):
        factor = 1.
    elif unit in ('µm', 'um') and c.get('molecular_mass'):
        factor = float(c['molecular_mass']) / 1000
    else:
        return dict(result, reason='Unit or molecular mass for actual tested form is unverified; no conversion guessed')
    standardized = value * factor
    positive, negative = (32, 128) if a['endpoint'] == 'MIC' else (100, 250)
    label = measurement_label({'concentration': comp + str(standardized), 'unit': {'name': 'µg/ml'}}, '', positive, negative)
    result.update(label='unknown' if label is None else label,
                  low_ugml=0. if comp.startswith('<') else standardized,
                  high_ugml=math.inf if comp.startswith('>') else standardized,
                  reason=f'Frozen {a["endpoint"]} thresholds; conversion basis: {c.get("mass_basis", "reported mass unit")}')
    return result


def resolve_labels(labels):
    known = {v for v in labels if v in (0, 1)}
    if len(known) > 1:
        return 'conflict'
    if not labels or 'unknown' in labels:
        return 'unknown'
    return next(iter(known))


def normalize_alias(value):
    v = str(value).strip().lower()
    v = re.sub(r'^https?://(?:dx\.)?doi\.org/', 'doi:', v)
    return 'doi:' + v if v.startswith('10.') else v


def aliases(article):
    result = set()
    pmid = (article.get('pubmed') or {}).get('pubmedId') or article.get('pmid')
    if pmid:
        result.add(normalize_alias('PMID:' + str(pmid)))
    for key in ('doi', 'pmcid'):
        if article.get(key):
            result.add(normalize_alias(key + ':' + str(article[key])))
    return result


def similarities(candidates, development):
    output, maxima, cache = [], {}, {}
    for c in candidates:
        if not c['sequence']:
            continue
        maximum, nearest = -1., ''
        for d in development:
            key = tuple(sorted((c['sequence'], d['seq'])))
            if key not in cache:
                cache[key] = sequence_identity(*key, identity_mode='alignment')
            identity = cache[key]
            if identity > maximum:
                maximum, nearest = identity, d['record_id']
            output.append(dict(candidate_id=c['candidate_id'], candidate_sequence=c['sequence'], development_record_id=d['record_id'],
                               development_sequence=d['seq'], identity=identity, violates_cutoff=identity >= .4,
                               sequence_basis='primary_sequence_confirmed' if c.get('sequence_verified') else 'unverified_inventory_sequence'))
        maxima[c['candidate_id']] = (maximum, nearest)
    return output, maxima


def homology_status(maximum, sequence_verified):
    if not sequence_verified:
        return 'pending_sequence_review'
    return 'failed' if maximum >= .4 else 'passed'


def candidate_decision(c, mic, hemo, maximum, study_status):
    if not c['source_reviewed'] or not c['sequence_verified']:
        molecule_status = 'pending_primary_identity_review'
    elif (c['molecular_form'] == 'linear_unmodified_free_ends_L' and
          10 <= len(c['sequence']) <= 50 and not set(c['sequence']) - set('ACDEFGHIKLMNPQRSTVWY')):
        molecule_status = 'passed'
    else:
        molecule_status = 'failed'
    homolog = homology_status(maximum, c['sequence_verified'])
    endpoints = mic in (0, 1) and hemo in (0, 1)
    ready = molecule_status == 'passed' and endpoints and homolog == 'passed' and study_status == 'passed'
    decision = ('candidate_ready_for_independent_review' if ready else
                'rejected' if c['source_reviewed'] else 'pending_primary_article_review')
    reasons = []
    if molecule_status != 'passed':
        reasons.append('Molecular identity/form: ' + molecule_status)
    if not endpoints:
        reasons.append(f'Unresolved/conflicting target endpoints: MIC={mic}; HC50={hemo}')
    if homolog != 'passed':
        reasons.append('Homology: ' + homolog)
    if study_status != 'passed':
        reasons.append('Original measurement study independence: ' + study_status)
    return dict(molecule_status=molecule_status, homology_status=homolog, dual_endpoint_passed=endpoints,
                gate_decision=decision, reason=' | '.join(reasons) or 'Candidate only; independent approval still required')


def write_csv(path, values, fields=None):
    fields = fields or list(dict.fromkeys(k for v in values for k in v)) or ['candidate_id']
    with path.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(values)


def write_json(path, data):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)


def run(manifest, anchor, output):
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f'Refusing existing output: {output}')
    if output.is_relative_to(ROOT) and not output.is_relative_to(BUNDLE):
        raise ValueError('Workspace output must stay inside new audit bundle')
    inputs = load_inputs(manifest, anchor)
    roles = inputs['roles']
    legacy = read_csv(ROOT / roles['legacy_molecules'])
    legacy_assays = read_csv(ROOT / roles['legacy_assays'])
    primary = read_primary(RAW)
    primary_by_id = {c['candidate_id']: c for c in primary}
    candidates = []
    for old in legacy:
        if old['candidate_id'] in primary_by_id:
            candidates.append(primary_by_id[old['candidate_id']])
            continue
        c = dict(candidate_id=old['candidate_id'], name=old['name'], source_db=old['source_db'], sequence=old['sequence'],
                 sequence_verified=False, sequence_location='legacy inventory; not reverified', molecular_form='pending_primary_review',
                 source_reviewed=False, source_file=roles['legacy_assays'], pmid=old['pmid'], doi=old['doi'], pmcid='',
                 molecular_mass='', mass_basis='not_verified', assays=[])
        for a in legacy_assays:
            if a['candidate_id'] == c['candidate_id']:
                c['assays'].append(observation(a['reported_assay_type'], a['target_organism_or_cell'], a['raw_value_text'], a['raw_unit'],
                                              f'legacy assay inventory/{a["assay_id"]}; original linked source not re-reviewed', reviewed=False))
        candidates.append(c)
    development = read_csv(ROOT / roles['development_records'])
    pairs, maxima = similarities(candidates, development)
    dev_aliases = set()
    for row in development:
        refs = json.loads(row['evidence_reference'])
        for ref in refs:
            dev_aliases.update(aliases(ref))
    mic_seqs = {r['seq'] for r in read_csv(ROOT / roles['mic_cohort'])}
    molecules, observations, labels, decisions, pool, conflicts, exposure, studies = [], [], [], [], [], [], [], []
    for c in candidates:
        molecules.append({k: v for k, v in c.items() if k != 'assays'})
        mic_labels, hemo_labels = [], []
        for index, a in enumerate(c['assays']):
            aid = f'{c["candidate_id"]}_{index + 1}'
            observations.append(dict(assay_id=aid, candidate_id=c['candidate_id'], source_file=c['source_file'], **a))
            derived = label_assay(a, c)
            labels.append(dict(assay_id=aid, candidate_id=c['candidate_id'], endpoint=a['endpoint'], **derived))
            if a['endpoint'] == 'MIC':
                mic_labels.append(derived['label'])
            if is_human_hc50(a):
                hemo_labels.append(derived['label'])
                pool.append(dict(candidate_id=c['candidate_id'], sequence=c['sequence'], pmcid=c['pmcid'], raw_hc50=a['raw_value'], unit=a['unit'],
                                 standardized_hc50_ugml=derived['low_ugml'], hemo_label=derived['label'], molecular_form=c['molecular_form'],
                                 source_file=c['source_file'], source_location=a['source_location'], mass_basis=c['mass_basis'],
                                 paired_mic_label=resolve_labels([label_assay(v, c)['label'] for v in c['assays'] if v['endpoint'] == 'MIC'])))
        mic, hemo = resolve_labels(mic_labels), resolve_labels(hemo_labels)
        for task, value in (('MIC', mic), ('HC50', hemo)):
            if value == 'conflict':
                conflicts.append(dict(candidate_id=c['candidate_id'], endpoint=task, reason='Opposite derived labels; molecule not released'))
        ca = aliases(c)
        overlap = bool(ca & dev_aliases)
        maximum, nearest = maxima.get(c['candidate_id'], (None, ''))
        study_status = 'overlap_detected' if overlap else 'pending_measurement_study_alias_review'
        # Absence of an alias match is a screen result, not proof of source independence.
        decision = candidate_decision(c, mic, hemo, maximum, study_status)
        decisions.append(dict(candidate_id=c['candidate_id'], mic_label=mic, hemo_label=hemo,
                              reported_sequence_max_identity=maximum if maximum is not None else '', nearest_development_record=nearest,
                              study_status=study_status, **decision))
        exposure.append(dict(candidate_id=c['candidate_id'], measurement_alias_overlap='|'.join(sorted(ca & dev_aliases)),
                             sequence_in_mic_cohort=bool(c['sequence']) and c['sequence'] in mic_seqs,
                             history_scope='Checks development aliases and current MIC sequence membership; full prior paper exposure not established'))
        studies.append(dict(candidate_id=c['candidate_id'], aliases='|'.join(sorted(ca)),
                            measurement_source_verified=c['source_reviewed'], independence_status=study_status))
    internal = []
    known = [c for c in candidates if c['sequence']]
    for i, c in enumerate(known):
        for d in known[:i]:
            identity = sequence_identity(c['sequence'], d['sequence'], identity_mode='alignment')
            internal.append(dict(candidate_1_id=c['candidate_id'], candidate_2_id=d['candidate_id'], identity=identity, violates_cutoff=identity >= .4))
    now = datetime.now(timezone.utc).isoformat()
    summary = dict(status='blocked', generated_at=now, protocol_id='protocol-amd-02',
                   review_method='agent_primary_source_review; not independent human approval', model_fit_calls=0, formal_state_modified=False,
                   counts=dict(candidate_records=len(candidates), distinct_nonempty_sequences=len({c['sequence'] for c in known}),
                               primary_sequence_verified=sum(c['sequence_verified'] for c in candidates), missing_sequence=len(candidates)-len(known),
                               pending_primary_article_review=sum(not c['source_reviewed'] for c in candidates),
                               assay_observations=len(observations), verified_human_hc50=len(pool),
                               eligible_external=sum(d['gate_decision'] == 'candidate_ready_for_independent_review' for d in decisions),
                               candidate_development_comparisons=len(pairs), candidate_internal_comparisons=len(internal),
                               provisional_inventory_homology_failed=sum(v[0] >= .4 for v in maxima.values()),
                               provisional_inventory_homology_passed=sum(v[0] < .4 for v in maxima.values()),
                               alias_overlap_detected=sum(bool(e['measurement_alias_overlap']) for e in exposure)),
                   limitations=['No new web search; repairs five archived XMLs and 78 unverified inventory leads.',
                                'Han-Def1 tested construct sequence not confirmed; omitted from alignment, never imputed.',
                                'No alias match does not prove original measurement-source independence.',
                                'Unverified inventory alignments are provisional; formal eligibility remains zero.'],
                   input_manifest=manifest.relative_to(ROOT).as_posix() if manifest.is_relative_to(ROOT) else str(manifest), input_manifest_sha256=anchor)
    # Recheck inputs at the end of computation, before any output is written.
    load_inputs(manifest, anchor)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'molecule_review.csv': molecules, 'assay_observations.csv': observations, 'derived_labels.csv': labels,
                 'hc50_verified_pool.csv': pool, 'external_candidate_decisions.csv': decisions,
                 'excluded_or_pending.csv': [d for d in decisions if d['gate_decision'] != 'candidate_ready_for_independent_review'],
                 'eligible_external_candidates.csv': [d for d in decisions if d['gate_decision'] == 'candidate_ready_for_independent_review'], 'conflicts.csv': conflicts,
                 'similarity_to_development.csv': pairs, 'candidate_similarity.csv': internal,
                 'historical_exposure.csv': exposure, 'study_aliases.csv': studies}
    for name, values in artifacts.items():
        write_csv(output / name, values)
    sources = []
    for pmcid in PMC_FILES:
        p = RAW / f'{pmcid}.xml'
        root = ET.parse(p).getroot()
        sources.append(dict(source_id=pmcid, source_file=p.relative_to(ROOT).as_posix(), sha256=sha(p),
                            license_as_reported=' | '.join(text(n) for n in root.findall('.//license')),
                            acquisition='Copied unchanged from v1; original acquisition metadata in frozen inputs/source_manifest.csv',
                            primary_xml_reviewed=True))
    write_csv(output / 'source_manifest.csv', sources)
    search = read_csv(ROOT / roles['legacy_search'])
    for row in search:
        row['provenance_status'] = 'Historical Gemini search claim; query response/count not independently reproduced in this repair'
    write_csv(output / 'search_log.csv', search)
    write_json(output / 'audit_summary.json', summary)
    from audit_report import render_report, render_readme
    for name, body in [('report.md', render_report(summary, molecules, observations, pool)), ('README.md', render_readme(summary))]:
        with (output / name).open('x', encoding='utf-8') as handle:
            handle.write(body)
    bound = {p.name: sha(p) for p in output.iterdir() if p.is_file()}
    scripts = {p.relative_to(ROOT).as_posix(): sha(p) for p in Path(__file__).parent.glob('*.py')}
    write_json(output / 'manifest.json', dict(schema_version=1, generated_at=now, inputs=inputs['files'],
                                             input_manifest_sha256=anchor, scripts=scripts, outputs=bound,
                                             environment={'python': platform.python_version(), 'platform': platform.platform()}))
    return summary


def validate_output(output):
    manifest = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    verify_bindings(output, {'files': manifest['outputs'], 'required_files': list(manifest['outputs'])})
    verify_bindings(ROOT, {'files': manifest['inputs'], 'required_files': list(manifest['inputs'])})
    verify_bindings(ROOT, {'files': manifest['scripts'], 'required_files': list(manifest['scripts'])})
    summary = json.loads((output / 'audit_summary.json').read_text(encoding='utf-8'))
    checks = {'candidate_records': 'molecule_review.csv', 'assay_observations': 'assay_observations.csv',
              'verified_human_hc50': 'hc50_verified_pool.csv', 'eligible_external': 'eligible_external_candidates.csv',
              'candidate_development_comparisons': 'similarity_to_development.csv', 'candidate_internal_comparisons': 'candidate_similarity.csv'}
    for count, filename in checks.items():
        if len(read_csv(output / filename)) != summary['counts'][count]:
            raise ValueError(f'Count mismatch: {count}')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-manifest', type=Path, required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input_manifest.resolve(), args.input_sha256, args.output)
    print(json.dumps(result, ensure_ascii=True))
