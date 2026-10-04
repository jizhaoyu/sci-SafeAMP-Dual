"""Research Feasibility Gate Evaluator.

Audits data quality, evidence coverage, sequence isolation topology,
stratified 5-fold partitioning, and external validation cohort status according
to the frozen research protocol.

Outputs comprehensive diagnostic artifacts.
Returns exit code 0 if ready for formal experiments; returns code 2 and
generates a blocked report if any scientific gating check fails.
"""
import argparse
from dataclasses import asdict
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Optional
import numpy as np
import pandas as pd

from feature_extractor import clean_sequence
from research_data import (
    validate_records,
    consolidate_records,
    prepare_frame,
    analyze_homology,
    assert_study_independence,
    validate_partition,
    sequence_identity,
    sequence_length_ratio,
    ResearchDataError,
    REQUIRED,
    TASKS,
)
from research_protocol_config import get_protocol, check_protocol_conflicts, protocol_digest
from research_utils import ROOT, sha256, utc_now, write_json, read_json


def audit_prepared_feasibility(
    prepared_dir: Path,
    output_dir: Path,
    protocol_id: Optional[str] = None,
) -> tuple[bool, dict]:
    """Audit an existing prepared directory and replay scientific feasibility gates."""
    prepared_dir = Path(prepared_dir)
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError(f"Output directory {output_dir} already exists. Versioned directories are required.")
    output_dir.mkdir(parents=True, exist_ok=True)

    blockers = []
    warnings = []
    checks = []

    report = {
        'status': 'blocked',
        'generated_at': utc_now(),
        'prepared_dir': str(prepared_dir.resolve()),
        'blockers': [],
        'warnings': [],
        'checks': {}
    }

    # 1. Check required prepared files
    required_files = [
        'manifest.json', 'dataset.csv', 'records.csv', 'cluster_membership.csv',
        'partition_audit.json', 'evidence_audit.json', 'exclusions.json'
    ]
    if (prepared_dir / 'manifest.json').is_file():
        candidate_manifest = read_json(prepared_dir / 'manifest.json')
        if candidate_manifest.get('protocol_id') == 'protocol-amd-02':
            required_files.extend(['cross_cohort_similarity.csv', 'homology_audit.json'])
    missing_files = [f for f in required_files if not (prepared_dir / f).is_file()]
    if missing_files:
        if (prepared_dir / 'manifest.json').is_file():
            manifest_reason = read_json(prepared_dir / 'manifest.json').get('reason')
            if manifest_reason:
                blockers.append(f'Prepared dataset blocked: {manifest_reason}')
        blockers.append(f"Missing required prepared files: {missing_files}")
        checks.append(('prepared_files_presence', 'failed', f"Missing: {missing_files}"))
        report['blockers'] = blockers
        write_json(output_dir / 'summary.json', report)
        return False, report
    checks.append(('prepared_files_presence', 'passed', 'All 7 required prepared files exist.'))

    # 2. Check manifest and checksums
    manifest = read_json(prepared_dir / 'manifest.json')
    report['manifest_sha256'] = sha256(prepared_dir / 'manifest.json')
    if manifest.get('status') != 'validated':
        blockers.append(f"Prepared manifest status is '{manifest.get('status')}', expected 'validated'.")
        checks.append(('manifest_status', 'failed', str(manifest.get('status'))))
    else:
        checks.append(('manifest_status', 'passed', 'Status is validated.'))

    for fname, sha_key in [
        ('dataset.csv', 'dataset_sha256'),
        ('records.csv', 'provenance_sha256'),
        ('cluster_membership.csv', 'cluster_membership_sha256'),
        ('partition_audit.json', 'partition_audit_sha256'),
        ('evidence_audit.json', 'evidence_audit_sha256'),
        ('exclusions.json', 'exclusions_sha256'),
        ('cross_cohort_similarity.csv', 'cross_cohort_similarity_sha256'),
        ('homology_audit.json', 'homology_audit_sha256'),
    ]:
        if (prepared_dir / fname).is_file() and sha_key in manifest:
            actual = sha256(prepared_dir / fname)
            expected = manifest[sha_key]
            if actual != expected:
                blockers.append(f"File checksum mismatch for {fname}: expected {expected}, got {actual}")
                checks.append((f'checksum_{fname}', 'failed', 'mismatch'))
            else:
                checks.append((f'checksum_{fname}', 'passed', 'matched'))

    # 3. Protocol consistency and conflict check
    manifest_proto = manifest.get('protocol_id', 'legacy-v1')
    if protocol_id and protocol_id != manifest_proto:
        blockers.append(f"Requested protocol '{protocol_id}' does not match prepared protocol '{manifest_proto}'.")
        checks.append(('protocol_match', 'failed', f"requested {protocol_id} != prepared {manifest_proto}"))
    else:
        checks.append(('protocol_match', 'passed', manifest_proto))

    try:
        spec = get_protocol(manifest_proto)
        if manifest_proto == 'protocol-amd-02' and (
            manifest.get('protocol_spec') != asdict(spec)
            or manifest.get('protocol_digest') != protocol_digest(spec)
        ):
            blockers.append('Frozen protocol specification or digest mismatch.')
            checks.append(('protocol_digest', 'failed', 'manifest differs from registered protocol'))
        has_conflict, conflict_reason = check_protocol_conflicts(spec)
        if has_conflict:
            blockers.append(f"Protocol conflict detected: {conflict_reason}")
            checks.append(('protocol_approval', 'failed', conflict_reason))
        else:
            checks.append(('protocol_approval', 'passed', 'Frozen protocol has no active conflicts.'))
    except Exception as exc:
        blockers.append(f"Invalid protocol specification: {exc}")
        checks.append(('protocol_spec', 'failed', str(exc)))
        spec = None

    # 4. Replay scientific validation on dataset
    try:
        dataset = pd.read_csv(prepared_dir / 'dataset.csv')
        records = pd.read_csv(prepared_dir / 'records.csv')
        validate_records(records, verify_raw=True)
        checks.append(('records_validation', 'passed', f"{len(records)} records validated against raw assays."))
        
        if spec:
            validate_partition(dataset, cutoff=spec.cutoff, protocol=spec)
            checks.append(('partition_validation', 'passed', 'Stratified 5-fold and cross-isolation verified.'))
            if manifest_proto == 'protocol-amd-02':
                assert_study_independence(records)
                expected, _, expected_pairs, expected_audit = analyze_homology(records, spec)
                saved_membership = pd.read_csv(prepared_dir / 'cluster_membership.csv')
                pd.testing.assert_frame_equal(
                    expected[['sample_id', 'cluster_id', 'representative_sample_id']].reset_index(drop=True),
                    saved_membership.reset_index(drop=True),
                )
                saved_pairs = pd.read_csv(prepared_dir / 'cross_cohort_similarity.csv')
                pd.testing.assert_frame_equal(expected_pairs, saved_pairs, check_exact=False, atol=1e-12, rtol=0)
                if read_json(prepared_dir / 'homology_audit.json') != expected_audit:
                    raise ResearchDataError('Homology audit differs from the all-member replay.')
                checks.append(('all_member_homology_replay', 'passed', 'Every pair and cluster membership matched.'))
    except Exception as exc:
        blockers.append(f"Replay partition validation failed: {exc}")
        checks.append(('partition_validation', 'failed', str(exc)))

    # 5. Generate label coverage and summary metrics
    try:
        dataset = pd.read_csv(prepared_dir / 'dataset.csv')
    except Exception:
        dataset = pd.DataFrame()
    total_mols = len(dataset)
    amp_pos = int((dataset['amp'] == 1).sum()) if 'amp' in dataset else 0
    amp_neg = int((dataset['amp'] == 0).sum()) if 'amp' in dataset else 0
    amp_unobs = int(dataset['amp'].isna().sum()) if 'amp' in dataset else 0
    hemo_pos = int((dataset['hemo'] == 1).sum()) if 'hemo' in dataset else 0
    hemo_neg = int((dataset['hemo'] == 0).sum()) if 'hemo' in dataset else 0
    hemo_unobs = int(dataset['hemo'].isna().sum()) if 'hemo' in dataset else 0
    both_observed = int((dataset['amp'].notna() & dataset['hemo'].notna()).sum()) if not dataset.empty else 0

    coverage_rows = [
        {'endpoint': 'AMP (E. coli MIC)', 'positive': amp_pos, 'negative': amp_neg, 'unknown': amp_unobs, 'total_observed': amp_pos + amp_neg, 'obs_pct': round((amp_pos + amp_neg) / max(total_mols, 1) * 100, 2)},
        {'endpoint': 'Hemo (Human HC50)', 'positive': hemo_pos, 'negative': hemo_neg, 'unknown': hemo_unobs, 'total_observed': hemo_pos + hemo_neg, 'obs_pct': round((hemo_pos + hemo_neg) / max(total_mols, 1) * 100, 2)},
        {'endpoint': 'Both Dual-Task', 'positive': both_observed, 'negative': 0, 'unknown': total_mols - both_observed, 'total_observed': both_observed, 'obs_pct': round(both_observed / max(total_mols, 1) * 100, 2)},
    ]
    pd.DataFrame(coverage_rows).to_csv(output_dir / 'label_coverage.csv', index=False)

    is_feasible = (len(blockers) == 0)
    report['status'] = 'ready_for_formal_experiments' if is_feasible else 'blocked'
    report['blockers'] = blockers
    report['warnings'] = warnings
    report['checks'] = {k: {'status': st, 'detail': dt} for k, st, dt in checks}
    write_json(output_dir / 'summary.json', report)

    # Markdown Report
    status_badge = "PASSED: READY FOR FORMAL EXPERIMENTS" if is_feasible else "BLOCKED: GATING CONDITIONS UNMET"
    md_content = f"""# SafeAMP-Dual 可行性复核报告 (Feasibility Audit Report)

**生成时间**：{report['generated_at']}  
**判定状态**：**{status_badge}**  
**检查目录**：`{prepared_dir}`  

---

## 1. 核心判定总结
- **可运行性 (Engineering)**: 准备产物与哈希校验完成。
- **科学门禁 (Scientific Gates)**: {'通过，可开展正式模型实验' if is_feasible else '被科学门禁阻断，禁止启动正式模型实验'}。

### 阻断原因清单 (Blockers):
{chr(10).join(f"- ⛔ **{b}**" for b in blockers) if blockers else "- 无阻断项"}

---

## 2. 标签覆盖统计
- **分子总量**: {total_mols}
- **AMP 抗菌标签**: 阳性 {amp_pos}, 阴性 {amp_neg}, 未测 {amp_unobs}
- **Hemo 溶血标签**: 阳性 {hemo_pos}, 阴性 {hemo_neg}, 未测 {hemo_unobs}
- **双端点测定**: {both_observed}
"""
    (output_dir / 'feasibility_report.md').write_text(md_content, encoding='utf-8')
    return is_feasible, report


def audit_feasibility(
    records_path: Path,
    output_dir: Path,
    cutoff: float = 0.40,
    protocol_id: str = "protocol-amd-02",
    clustering_method: str = "transitive",
    identity_mode: str = "min",
) -> tuple[bool, dict]:
    output_dir = Path(output_dir)
    if output_dir.exists():
        raise ValueError(f"Output directory {output_dir} already exists. Versioned directories are required.")
    output_dir.mkdir(parents=True, exist_ok=True)

    blockers = []
    warnings = []
    checks = []

    report = {
        'status': 'blocked',
        'generated_at': utc_now(),
        'records_path': str(records_path),
        'records_sha256': sha256(records_path) if Path(records_path).exists() else None,
        'cutoff': cutoff,
        'protocol_id': protocol_id,
        'blockers': [],
        'warnings': [],
        'checks': {}
    }

    # 1. Protocol specification & conflict check
    try:
        spec = get_protocol(protocol_id)
        has_conflict, conflict_reason = check_protocol_conflicts(spec)
        if has_conflict:
            blockers.append(conflict_reason)
            checks.append(('protocol_conflicts', 'failed', conflict_reason))
        else:
            checks.append(('protocol_conflicts', 'passed', 'Protocol specification approved without conflicts.'))
    except Exception as exc:
        blockers.append(f"Invalid protocol ID: {exc}")
        checks.append(('protocol_conflicts', 'failed', str(exc)))
        spec = None

    # 2. Load and validate records provenance
    try:
        raw_df = pd.read_csv(records_path)
        records = validate_records(raw_df, verify_raw=True)
        checks.append(('records_provenance_validation', 'passed', f"{len(records)} records validated against raw assays."))
    except Exception as exc:
        blockers.append(f"Records validation failed: {exc}")
        checks.append(('records_provenance_validation', 'failed', str(exc)))
        records = pd.DataFrame()

    if records.empty:
        report['blockers'] = blockers
        report['checks'] = {k: {'status': st, 'detail': dt} for k, st, dt in checks}
        write_json(output_dir / 'summary.json', report)
        return False, report

    # 3. Consolidation & Label Coverage
    consolidated_df, exclusions = consolidate_records(records)
    write_json(output_dir / 'exclusions.json', exclusions)
    checks.append(('consolidation', 'passed', f"{len(consolidated_df)} consolidated unique molecules"))

    total_mols = len(consolidated_df)
    amp_pos = int((consolidated_df['amp'] == 1).sum())
    amp_neg = int((consolidated_df['amp'] == 0).sum())
    amp_unobs = int(consolidated_df['amp'].isna().sum())
    hemo_pos = int((consolidated_df['hemo'] == 1).sum())
    hemo_neg = int((consolidated_df['hemo'] == 0).sum())
    hemo_unobs = int(consolidated_df['hemo'].isna().sum())
    both_observed = int((consolidated_df['amp'].notna() & consolidated_df['hemo'].notna()).sum())

    coverage_rows = [
        {'endpoint': 'AMP (E. coli MIC)', 'positive': amp_pos, 'negative': amp_neg, 'unknown': amp_unobs, 'total_observed': amp_pos + amp_neg, 'obs_pct': round((amp_pos + amp_neg) / total_mols * 100, 2)},
        {'endpoint': 'Hemo (Human HC50)', 'positive': hemo_pos, 'negative': hemo_neg, 'unknown': hemo_unobs, 'total_observed': hemo_pos + hemo_neg, 'obs_pct': round((hemo_pos + hemo_neg) / total_mols * 100, 2)},
        {'endpoint': 'Both Dual-Task', 'positive': both_observed, 'negative': 0, 'unknown': total_mols - both_observed, 'total_observed': both_observed, 'obs_pct': round(both_observed / total_mols * 100, 2)},
    ]
    pd.DataFrame(coverage_rows).to_csv(output_dir / 'label_coverage.csv', index=False)

    # 4. Replay full preparation and partition
    if spec:
        try:
            partitioned_df, audit = prepare_frame(records, spec)
            checks.append(('partition_and_isolation', 'passed', f"{audit['cluster_count']} clusters, 5-fold stratification verified."))
        except Exception as exc:
            blockers.append(f"Preparation pipeline failed: {exc}")
            checks.append(('partition_and_isolation', 'failed', str(exc)))

    is_feasible = (len(blockers) == 0)
    report['status'] = 'ready_for_formal_experiments' if is_feasible else 'blocked'
    report['blockers'] = blockers
    report['warnings'] = warnings
    report['checks'] = {k: {'status': st, 'detail': dt} for k, st, dt in checks}
    write_json(output_dir / 'summary.json', report)

    # Markdown Report
    status_badge = "PASSED: READY FOR FORMAL EXPERIMENTS" if is_feasible else "BLOCKED: GATING CONDITIONS UNMET"
    md_content = f"""# SafeAMP-Dual 可行性与门禁判定报告 (Research Feasibility Report)

**生成时间**：{report['generated_at']}  
**判定状态**：**{status_badge}**  
**评估数据集**：`{records_path}`  
**协议**：`{protocol_id}`  

---

## 1. 核心判定总结
- **科学门禁 (Scientific Gates)**: {'通过，可开展正式模型实验' if is_feasible else '被科学门禁阻断，禁止启动正式模型实验'}。

### 阻断原因清单 (Blockers):
{chr(10).join(f"- ⛔ **{b}**" for b in blockers) if blockers else "- 无阻断项"}

---

## 2. 标签覆盖统计
- **分子总量**: {total_mols} 条未修饰单体肽
- **AMP 抗菌标签**: 阳性 {amp_pos}, 阴性 {amp_neg}, 未测 {amp_unobs}
- **Hemo 溶血标签**: 阳性 {hemo_pos}, 阴性 {hemo_neg}, 未测 {hemo_unobs}
- **双端点测定**: {both_observed}
"""
    (output_dir / 'feasibility_report.md').write_text(md_content, encoding='utf-8')
    return is_feasible, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--records', type=Path, help='Path to records.csv')
    input_group.add_argument('--prepared', type=Path, help='Path to validated prepared directory')

    parser.add_argument('--output', type=Path, required=True, help='Output directory for feasibility report')
    parser.add_argument('--protocol-id', type=str, default=None, choices=['legacy-v1', 'protocol-amd-01', 'protocol-amd-02'])
    parser.add_argument('--cutoff', type=float, default=0.40, help='Homology identity cutoff')
    parser.add_argument('--clustering-method', choices=['cdhit', 'transitive'], default='transitive')
    parser.add_argument('--identity-mode', choices=['min', 'max', 'cdhit_ratio'], default='min')
    args = parser.parse_args()

    if args.prepared:
        feasible, report = audit_prepared_feasibility(
            args.prepared,
            args.output,
            protocol_id=args.protocol_id
        )
    else:
        feasible, report = audit_feasibility(
            args.records,
            args.output,
            cutoff=args.cutoff,
            protocol_id=args.protocol_id or 'protocol-amd-02',
            clustering_method=args.clustering_method,
            identity_mode=args.identity_mode,
        )

    if not feasible:
        print(f"\n[Feasibility Gate] BLOCKERS DETECTED ({len(report['blockers'])}):")
        for b in report['blockers']:
            print(f"  - {b}")
        sys.exit(2)
    else:
        print("\n[Feasibility Gate] ALL SCIENTIFIC GATES PASSED. READY FOR FORMAL EXPERIMENTS.")
        sys.exit(0)


if __name__ == '__main__':
    main()
