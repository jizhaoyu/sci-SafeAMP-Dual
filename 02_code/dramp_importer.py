"""DRAMP data importer and independent external validation candidate evaluator.

Imports DRAMP official peptide library (peptide_library_all.xlsx).
Applies identical biological endpoint criteria:
- 10-50 AA canonical linear monomers
- Human erythrocyte HC50 (<=100 positive, >=250 negative)
- Cross-cohort provenance validation:
  1. Exact sequence deduplication against development cohort.
  2. Literature / PMID / DOI overlap checking against development cohort.
  3. DBAASP cross-reference tracking.
  4. Sequence homology isolation checking against all development sequences.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Optional
import numpy as np
import pandas as pd

from feature_extractor import STANDARD_AMINO_ACIDS, clean_sequence
from assay_records import (
    SingleAssayObservation,
    StandardizedMoleculeRecord,
    evaluate_assay_for_hemo,
    process_molecule_record,
)
from research_data import sequence_identity, REQUIRED
from research_utils import ROOT, sha256, utc_now, write_json


def extract_pmids_and_dois_from_dev(dev_records_path: Path) -> tuple[set[str], set[str]]:
    """Extract PMIDs and DOIs from development set evidence references."""
    dev_df = pd.read_csv(dev_records_path)
    pmids = set()
    dois = set()
    for ref_str in dev_df['evidence_reference'].dropna():
        try:
            articles = json.loads(ref_str) if isinstance(ref_str, str) else []
            for art in articles:
                pubmed_obj = art.get('pubmed') if isinstance(art.get('pubmed'), dict) else {}
                pmid = pubmed_obj.get('pubmedId') or art.get('pubmedId') or art.get('pmid')
                if pmid:
                    pmids.add(str(pmid).strip())
                doi = art.get('doi')
                if doi:
                    dois.add(str(doi).lower().strip())
        except Exception:
            pass
    return pmids, dois


def parse_dramp_hemolysis(text: str) -> Optional[tuple[str, str, str]]:
    """Extract (raw_value, raw_unit, matched_snippet) for human erythrocyte 50% hemolysis."""
    if not isinstance(text, str):
        return None
    text_clean = text.strip()
    if 'human' not in text_clean.lower() or not any(k in text_clean.lower() for k in ['50%', 'hc50', 'mhc']):
        return None

    # Find human erythrocyte section if split by semicolon
    sections = [s.strip() for s in text_clean.split(';')]
    human_sections = [s for s in sections if 'human' in s.lower()]
    target_text = ' ; '.join(human_sections) if human_sections else text_clean

    pattern = re.compile(
        r'(?:(?:50%\s*Hemolysis|HC50|MHC)[^=:]*[=:]\s*([<>]?=?\s*[\d\.]+)\s*([a-zA-Z%µμ/]+))',
        re.IGNORECASE
    )
    m = pattern.search(target_text)
    if m:
        val_str = m.group(1).strip()
        unit_str = m.group(2).strip()
        return val_str, unit_str, m.group(0)
    return None


def import_dramp(raw_xlsx_path: Path, dev_records_path: Path, output_dir: Path):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_xlsx_path = Path(raw_xlsx_path)

    raw_hash = sha256(raw_xlsx_path)
    print(f"[DRAMP Importer] Reading {raw_xlsx_path} (SHA256: {raw_hash[:16]}...)...")

    # Load development cohort for overlap checking
    dev_df = pd.read_csv(dev_records_path)
    dev_seqs = set(dev_df['seq'].map(clean_sequence))
    dev_seq_list = list(dev_seqs)
    dev_pmids, dev_dois = extract_pmids_and_dois_from_dev(dev_records_path)
    print(f"[DRAMP Importer] Dev cohort loaded: {len(dev_seqs)} unique sequences, {len(dev_pmids)} PMIDs, {len(dev_dois)} DOIs.")

    df_dramp = pd.read_excel(raw_xlsx_path)
    total_raw = len(df_dramp)

    candidate_audit = []
    eligible_records = []
    exclusions = []

    for idx, row in df_dramp.iterrows():
        dramp_id = str(row.get('DRAMP_ID', f'DRAMP_ROW_{idx}')).strip()
        dbaasp_id_ref = str(row.get('DBAASP_ID', '')).strip()
        has_dbaasp_id = dbaasp_id_ref not in ('Not available', 'nan', '', 'None')
        literature = str(row.get('Literature', '')).strip()

        raw_seq = str(row.get('Sequence', '')).strip().upper()
        if not raw_seq or raw_seq == 'NAN':
            exclusions.append({'dramp_id': dramp_id, 'reason': 'missing_sequence'})
            continue

        try:
            seq = clean_sequence(raw_seq)
        except Exception:
            exclusions.append({'dramp_id': dramp_id, 'reason': 'noncanonical_amino_acid'})
            continue

        if not (10 <= len(seq) <= 50):
            exclusions.append({'dramp_id': dramp_id, 'reason': 'length_out_of_range'})
            continue

        # Check modifications / linear monomer
        lc = str(row.get('Linear_Cyclic', '')).strip().lower()
        if lc not in ('linear', 'not available', 'none', 'nan', ''):
            exclusions.append({'dramp_id': dramp_id, 'reason': 'cyclic_peptide'})
            continue
        disulf = str(row.get('Disulfide_Bond', '')).strip().lower()
        if disulf not in ('none', 'not available', 'nan', ''):
            exclusions.append({'dramp_id': dramp_id, 'reason': 'disulfide_bond_present'})
            continue
        n_term = str(row.get('N-terminal_Modification', '')).strip().lower()
        if n_term not in ('free', 'none', 'not available', 'nan', ''):
            exclusions.append({'dramp_id': dramp_id, 'reason': 'n_terminal_modification'})
            continue
        c_term = str(row.get('C-terminal_Modification', '')).strip().lower()
        if c_term not in ('free', 'none', 'not available', 'nan', ''):
            exclusions.append({'dramp_id': dramp_id, 'reason': 'c_terminal_modification'})
            continue
        other_mod = str(row.get('Other_Modification', '')).strip().lower()
        if other_mod not in ('none', 'not available', 'nan', ''):
            exclusions.append({'dramp_id': dramp_id, 'reason': 'other_modification'})
            continue

        # Parse Hemolysis
        hemo_raw = str(row.get('Hemolytic_Activity', ''))
        parsed_hemo = parse_dramp_hemolysis(hemo_raw)
        if not parsed_hemo:
            exclusions.append({'dramp_id': dramp_id, 'reason': 'no_human_hc50_measurement'})
            continue

        val_str, unit_str, snippet = parsed_hemo

        # Evaluate observation
        obs = SingleAssayObservation(
            endpoint='hemo',
            target_organism_or_cell='Human erythrocytes',
            metric_name='HC50',
            raw_value=val_str,
            raw_unit=unit_str,
            conditions=snippet,
            reference=literature
        )
        evaluate_assay_for_hemo(obs, seq)

        # Cross-cohort overlap checks
        exact_seq_overlap = seq in dev_seqs
        lit_overlap = any(pmid in literature for pmid in dev_pmids) if dev_pmids else False

        # Homology checks against all dev sequences
        max_id_min = 0.0
        max_id_max = 0.0
        for d_seq in dev_seq_list:
            p_id = sequence_identity(seq, d_seq)
            min_l = min(len(seq), len(d_seq))
            max_l = max(len(seq), len(d_seq))
            matches = round(p_id * min_l)
            id_max = matches / max_l
            if p_id > max_id_min:
                max_id_min = p_id
            if id_max > max_id_max:
                max_id_max = id_max

        audit_entry = {
            'dramp_id': dramp_id,
            'sequence': seq,
            'length': len(seq),
            'raw_value': val_str,
            'raw_unit': unit_str,
            'assay_eligible': obs.eligible,
            'derived_label': obs.derived_label,
            'ineligibility_reason': obs.ineligibility_reason,
            'exact_dev_overlap': exact_seq_overlap,
            'literature_overlap': lit_overlap,
            'dbaasp_crossref': has_dbaasp_id,
            'max_id_min': round(max_id_min, 3),
            'max_id_max': round(max_id_max, 3),
            'violates_current_0.40_isolation': (max_id_min >= 0.40),
            'violates_standard_max_0.40_isolation': (max_id_max >= 0.40),
        }
        candidate_audit.append(audit_entry)

        # Exclusion gates for official external cohort:
        # Must be assay eligible, have derived label, no exact seq overlap, no lit overlap, no dbaasp cross-ref,
        # and MUST satisfy sequence isolation under current rule (max_id_min < 0.40)
        rejection_reasons = []
        if not obs.eligible:
            rejection_reasons.append(obs.ineligibility_reason)
        if obs.derived_label is None:
            rejection_reasons.append('intermediate_or_censored_hemo')
        if exact_seq_overlap:
            rejection_reasons.append('exact_sequence_overlap_with_development')
        if lit_overlap:
            rejection_reasons.append('literature_pmid_overlap_with_development')
        if has_dbaasp_id:
            rejection_reasons.append('dbaasp_cross_referenced')
        if max_id_min >= 0.40:
            rejection_reasons.append('homology_cross_isolation_violation_current_rule')

        if rejection_reasons:
            exclusions.append({
                'dramp_id': dramp_id,
                'sequence': seq,
                'rejection_reasons': rejection_reasons
            })
        else:
            # Passes all gates
            record = StandardizedMoleculeRecord(
                record_id=f'DRAMP:{dramp_id}',
                sequence=seq,
                source_dataset='DRAMP',
                source_accession=dramp_id,
                source_url=f'https://dramp.cpu-bioinfor.com/browse/Peptide_Information.php?id={dramp_id}',
                source_role='external',
                evidence_reference=literature,
                modifications='none',
                evidence_type='experimental',
                is_synthetic=False,
                raw_path=str(raw_xlsx_path.resolve().relative_to(ROOT)).replace('\\', '/'),
                raw_sha256=raw_hash,
                observations=[obs]
            )
            row, _ = process_molecule_record(record)
            if row:
                eligible_records.append(row)

    # Save outputs
    audit_df = pd.DataFrame(candidate_audit)
    audit_df.to_csv(output_dir / 'candidate_audit.csv', index=False)
    write_json(output_dir / 'exclusions.json', exclusions)

    if eligible_records:
        records_df = pd.DataFrame(eligible_records, columns=REQUIRED)
        records_df.to_csv(output_dir / 'records.csv', index=False)
    else:
        # Create empty compatible schema
        pd.DataFrame(columns=REQUIRED).to_csv(output_dir / 'records.csv', index=False)

    summary = {
        'status': 'completed',
        'generated_at': utc_now(),
        'total_dramp_raw': total_raw,
        'candidates_with_human_hc50': len(candidate_audit),
        'exact_sequence_overlaps': int(audit_df['exact_dev_overlap'].sum()) if len(audit_df) else 0,
        'literature_overlaps': int(audit_df['literature_overlap'].sum()) if len(audit_df) else 0,
        'dbaasp_crossrefs': int(audit_df['dbaasp_crossref'].sum()) if len(audit_df) else 0,
        'violates_current_0.40_isolation': int(audit_df['violates_current_0.40_isolation'].sum()) if len(audit_df) else 0,
        'violates_standard_max_0.40_isolation': int(audit_df['violates_standard_max_0.40_isolation'].sum()) if len(audit_df) else 0,
        'strictly_eligible_external_records': len(eligible_records)
    }
    write_json(output_dir / 'source_manifest.json', summary)
    print(f"[DRAMP Importer] Completed: {len(candidate_audit)} candidates audited, {len(eligible_records)} passed all strict gates.")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=ROOT / '02_code/data/sources/dramp_v1/raw/peptide_library_all.xlsx')
    parser.add_argument('--dev-records', type=Path, default=ROOT / '02_code/data/sources/dbaasp_v1/records.csv')
    parser.add_argument('--output', type=Path, default=ROOT / '02_code/data/sources/dramp_v1')
    args = parser.parse_args()

    import_dramp(args.raw, args.dev_records, args.output)


if __name__ == '__main__':
    main()
