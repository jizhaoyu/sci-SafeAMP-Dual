"""Source evidence validation and experimental measurement re-derivation.

Validates that every experimental record traceably derives its binary endpoints
(E. coli MIC <=32 / >=128 ug/mL, human erythrocyte HC50 <=100 / >=250 ug/mL)
from verified raw assay measurements.

Handwritten binary labels, unsupported endpoints, missing raw assays,
default fallback DOIs, and unannotated negative assumptions are rejected
and structured into an evidence_audit dictionary.
"""
import json
import math
from pathlib import Path
from typing import Any, Optional
import numpy as np
import pandas as pd

from feature_extractor import clean_sequence, STANDARD_AMINO_ACIDS
from research_utils import ROOT, sha256
from assay_records import (
    SingleAssayObservation,
    evaluate_assay_for_amp,
    evaluate_assay_for_hemo,
)


DEFAULT_DISALLOWED_DOIS = {
    '10.1093/nar/gkw1008',  # APD3 database summary paper, not an assay paper
}


def compare_declared_assay_conditions(declared_text: str, raw_assays: list[dict]) -> list[str]:
    """Reject structured assay metadata that disagrees with the underlying record."""
    try:
        declared = json.loads(declared_text)
    except (TypeError, ValueError):
        return []  # Older sources may carry unstructured conditions text.
    if not isinstance(declared, dict):
        return []
    issues = []
    for endpoint in ('amp', 'hemo'):
        entries = declared.get(endpoint, [])
        if not isinstance(entries, list):
            continue
        candidates = [obs for obs in raw_assays if isinstance(obs, dict) and obs.get('endpoint') == endpoint]
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict) or not {'target', 'raw_value', 'raw_unit'} <= set(entry):
                continue
            def same(a, b):
                return str(a).strip().casefold() == str(b).strip().casefold()
            matching = [obs for obs in candidates if
                        same(entry['target'], obs.get('target_organism_or_cell', '')) and
                        same(entry['raw_value'], obs.get('raw_value', '')) and
                        same(entry['raw_unit'], obs.get('raw_unit', ''))]
            if not matching:
                issues.append(f'Declared {endpoint} assay conditions entry {index} differs from raw target, value, or unit.')
                continue
            for declared_key, raw_key in (('method', 'assay_method'), ('medium', 'medium')):
                if entry.get(declared_key) and any(obs.get(raw_key) for obs in matching) and not any(
                    same(entry[declared_key], obs.get(raw_key, '')) for obs in matching
                ):
                    issues.append(f'Declared {endpoint} assay {declared_key} entry {index} differs from raw evidence.')
    return issues


def derive_external_labels(entry: dict, sequence: str) -> tuple[float, float, list[str]]:
    """Derive task labels solely from eligible experimental observations."""
    observations = entry.get('observations') or entry.get('assays') or entry.get('measurements')
    if not isinstance(observations, list) or not observations:
        return np.nan, np.nan, ['No raw assay observations found in source entry.']
    labels = {'amp': set(), 'hemo': set()}
    for obs_dict in observations:
        if not isinstance(obs_dict, dict):
            continue
        obs = SingleAssayObservation(
            endpoint=obs_dict.get('endpoint', ''),
            target_organism_or_cell=obs_dict.get('target_organism_or_cell', ''),
            metric_name=obs_dict.get('metric_name', ''),
            raw_value=str(obs_dict.get('raw_value', '')),
            raw_unit=str(obs_dict.get('raw_unit', '')),
            conditions=str(obs_dict.get('conditions', '')),
            reference=str(obs_dict.get('reference', '')),
        )
        if obs.endpoint == 'amp':
            evaluate_assay_for_amp(obs, sequence)
        elif obs.endpoint == 'hemo':
            evaluate_assay_for_hemo(obs, sequence)
        else:
            continue
        if obs.derived_label is not None:
            labels[obs.endpoint].add(obs.derived_label)
    issues = [f'Conflicting {task.upper()} measurements in raw assays.' for task in labels if len(labels[task]) > 1]
    result = tuple(float(next(iter(labels[task]))) if len(labels[task]) == 1 else np.nan for task in ('amp', 'hemo'))
    if all(np.isnan(value) for value in result):
        issues.append('No eligible experimental assay yields a study endpoint label.')
    return result[0], result[1], issues


def validate_source_evidence(records: pd.DataFrame) -> dict:
    """Validate raw evidence files and rederive labels from experimental measurements.
    
    Returns structured audit dictionary on success.
    Raises ResearchDataError(message, evidence_audit=audit) if any record
    cannot be substantiated by real experimental assays.
    """
    from research_data import ResearchDataError

    failures = []
    source_hashes = {}
    verified_records = 0

    # 1. Verify existence and sha256 of all declared raw files
    unique_raw = records[['raw_path', 'raw_sha256']].drop_duplicates()
    for _, raw_row in unique_raw.iterrows():
        raw_rel = str(raw_row['raw_path'])
        expected_sha = raw_row['raw_sha256']
        p = Path(raw_rel)
        if not p.is_absolute():
            p = (ROOT / raw_rel).resolve()
            if not p.is_relative_to(ROOT) or not p.is_file():
                failures.append({
                    'record_id': f'RAW_FILE:{raw_rel}',
                    'raw_path': raw_rel,
                    'issues': ['Raw source file is missing or not located within repository root.']
                })
                continue
        else:
            p = p.resolve()
            if not p.is_file():
                failures.append({
                    'record_id': f'RAW_FILE:{raw_rel}',
                    'raw_path': raw_rel,
                    'issues': ['Raw source file does not exist.']
                })
                continue
        actual_sha = sha256(p)
        source_hashes[raw_rel] = actual_sha
        if actual_sha != expected_sha:
            failures.append({
                'record_id': f'RAW_FILE:{raw_rel}',
                'raw_path': raw_rel,
                'issues': [f'Raw source checksum mismatch: expected {expected_sha}, got {actual_sha}']
            })

    # Cache parsed raw files
    raw_cache = {}

    # 2. Iterate through records and verify underlying assay measurements
    for row in records.itertuples():
        record_id = getattr(row, 'record_id')
        raw_rel = str(getattr(row, 'raw_path'))
        p = Path(raw_rel)
        raw_path = p.resolve() if p.is_absolute() else (ROOT / raw_rel).resolve()
        if not raw_path.is_file():
            continue  # Already captured above

        if raw_rel not in raw_cache:
            try:
                raw_cache[raw_rel] = json.loads(raw_path.read_text(encoding='utf-8'))
            except Exception as exc:
                raw_cache[raw_rel] = exc

        raw_content = raw_cache[raw_rel]
        if isinstance(raw_content, Exception):
            failures.append({
                'record_id': str(record_id),
                'raw_path': raw_rel,
                'issues': [f'Cannot parse raw JSON: {raw_content}']
            })
            continue

        issues = []
        source_dataset = getattr(row, 'source_dataset', '')

        # Case A: DBAASP official raw records
        if source_dataset == 'DBAASP' or (isinstance(raw_content, dict) and 'dbaaspId' in raw_content):
            from public_data import extract_record
            derived, reason = extract_record(raw_content, raw_path)
            if derived is None:
                issues.append(f'Raw DBAASP record does not meet operational criteria: {reason}')
            else:
                for field_name in ['record_id', 'seq', 'source_accession', 'source_url', 'amp', 'hemo']:
                    exp = derived[field_name]
                    act = getattr(row, field_name)
                    if pd.isna(exp) and pd.isna(act):
                        continue
                    if exp != act:
                        issues.append(f'DBAASP field mismatch in {field_name}: expected {exp}, got {act}')

        # Case B: Other databases / benchmark / external records
        else:
            entry = None
            candidates = []
            if isinstance(raw_content, list):
                candidates = [item for item in raw_content if isinstance(item, dict)]
            elif isinstance(raw_content, dict):
                candidates = [item for item in raw_content.get('records', []) if isinstance(item, dict)] if isinstance(raw_content.get('records'), list) else [raw_content]

            exact = [item for item in candidates if (
                item.get('id') in (record_id, row.source_accession)
                or item.get('record_id') == record_id
                or item.get('acc') == row.source_accession
            )]
            if len(exact) == 1:
                entry = exact[0]
            elif not exact:
                sequence_matches = [item for item in candidates if item.get('seq') == row.seq]
                if len(sequence_matches) == 1:
                    entry = sequence_matches[0]

            if entry is None:
                issues.append(f'Record identifier {record_id} not found in raw source file.')
            else:
                # Check for fake/handwritten records where binary labels were typed directly
                raw_assays = entry.get('observations') or entry.get('assays') or entry.get('measurements')
                
                # Check default catch-all DOI
                url = str(getattr(row, 'source_url', ''))
                doi = str(entry.get('doi', '') or url).lower()
                for dis_doi in DEFAULT_DISALLOWED_DOIS:
                    if dis_doi in doi:
                        issues.append(f'Default fallback DOI ({dis_doi}) cannot serve as primary assay reference for {entry.get("db")}.')

                if not raw_assays:
                    # Check if entry is only hardcoded binary labels
                    if 'amp' in entry or 'hemo' in entry:
                        issues.append('Record contains handwritten binary labels without underlying experimental assay observations.')
                    else:
                        issues.append('No raw assay observations found in source entry.')
                else:
                    if entry.get('seq'):
                        try:
                            if clean_sequence(entry['seq']) != clean_sequence(row.seq):
                                issues.append('Raw assay sequence does not match declared record sequence.')
                        except ValueError:
                            issues.append('Raw assay sequence is invalid.')
                    issues.extend(compare_declared_assay_conditions(str(row.assay_conditions), raw_assays))
                    if getattr(row, 'source_role', '') == 'external' and not (
                        entry.get('doi') or entry.get('pmid') or any(
                            isinstance(obs, dict) and obs.get('reference') for obs in raw_assays
                        )
                    ):
                        issues.append('External assay lacks a primary study reference.')
                    derived_amp, derived_hemo, derivation_issues = derive_external_labels(entry, clean_sequence(row.seq))
                    issues.extend(derivation_issues)
                    for task, derived in (('amp', derived_amp), ('hemo', derived_hemo)):
                        declared = getattr(row, task)
                        if not pd.isna(declared):
                            if pd.isna(derived):
                                issues.append(f'Declared {task.upper()} label {declared} lacks eligible experimental assay derivation.')
                            elif derived != declared:
                                issues.append(f'Declared {task.upper()} {declared} differs from re-derived assay label {derived}.')

        if issues:
            failures.append({
                'record_id': str(record_id),
                'seq': str(row.seq),
                'source_dataset': str(source_dataset),
                'source_role': str(getattr(row, 'source_role', '')),
                'declared_amp': None if pd.isna(row.amp) else float(row.amp),
                'declared_hemo': None if pd.isna(row.hemo) else float(row.hemo),
                'raw_path': str(raw_rel),
                'issues': issues
            })
        else:
            verified_records += 1

    audit = {
        'status': 'validated' if not failures else 'blocked',
        'total_records': len(records),
        'verified_records': verified_records,
        'failed_records': len(failures),
        'source_hashes': source_hashes,
        'failures': failures
    }

    if failures:
        raise ResearchDataError(
            f'Source evidence validation failed for {len(failures)} records; missing or conflicted experimental assays.',
            evidence_audit=audit
        )

    return audit
