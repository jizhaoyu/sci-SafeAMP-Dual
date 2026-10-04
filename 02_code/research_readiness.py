"""Generate an evidence-bounded project status and a non-submittable protocol draft."""
import argparse
import hashlib
from pathlib import Path
import pandas as pd
from research_utils import ROOT,read_json,write_json,sha256,utc_now
from research_data import validate_records


def generate(source,prepared):
    source,prepared=Path(source),Path(prepared)
    collection=read_json(source/'source_manifest.json');split=read_json(prepared/'manifest.json')
    if split.get('status')!='blocked':
        raise ValueError('This draft renderer is for blocked pilots; use publication_artifacts for completed research runs.')
    digest=sha256(source/'records.csv')
    if digest!=collection['records_sha256'] or digest!=split['records_sha256']:
        raise ValueError('Source collection and preparation hashes do not agree.')
    records=validate_records(pd.read_csv(source/'records.csv'))
    counts={task:{'positive':int(records[task].eq(1).sum()),'negative':int(records[task].eq(0).sum()),
                  'unknown':int(records[task].isna().sum())} for task in ['amp','hemo']}
    state={'generated_at':utc_now(),'publication_ready':False,'formal_results_available':False,
           'source_records':len(records),'label_counts':counts,'preparation':split,
           'source_sha256':digest,'required_next_steps':[
             'Establish a scientifically justified, prespecified feasible isolation protocol; do not silently loosen the current one.',
             'Acquire an independently sourced cohort with compatible measurements and audit cross-cohort homology.',
             'Complete seven-model three-seed grouped experiments only after all data gates pass.',
             'Review source reuse terms, bibliographic claim support, authorship and all declarations.']}
    write_json(ROOT/'04_paper/research_status.json',state)
    evidence=[{'id':'E001','kind':'experimental_source_records','path':str((source/'records.csv').relative_to(ROOT)),
               'sha256':digest,'verification_status':'machine_integrity_checked_human_review_pending'},
              {'id':'E002','kind':'partition_feasibility','path':str((prepared/'manifest.json').relative_to(ROOT)),
               'sha256':sha256(prepared/'manifest.json'),'verification_status':'machine_generated_human_review_pending'}]
    write_json(ROOT/'04_paper/evidence/source_manifest.json',{'sources':evidence,'all_verified':False})
    claims=[('C001','The pilot contains '+str(len(records))+' eligible experimental source records.','E001'),
            ('C002','The current preparation is blocked and no formal predictive results are available.','E002')]
    pd.DataFrame([{'claim_id':k,'claim_sha256':hashlib.sha256(text.encode()).hexdigest(),'evidence_ids':e,
                   'status':'pending_accountable_human_review'} for k,text,e in claims]).to_csv(ROOT/'04_paper/evidence/claims.csv',index=False)
    write_json(ROOT/'04_paper/evidence/consistency_manifest.json',{'sample_count':len(records),'tasks':counts,
        'methods':{'identity':split['identity_definition'],'cutoff':split['cutoff'],'folds':5,'seeds':[11,23,42]},
        'results':[],'status':'protocol_only_no_formal_results'})
    a,h=counts['amp'],counts['hemo']
    table='\n'.join(f"{name} & {v['positive']} & {v['negative']} & {v['unknown']} \\\\" for name,v in [('E. coli MIC',a),('Human erythrocyte HC50',h)])
    manuscript=r'''\documentclass[11pt,a4paper]{article}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,booktabs,hyperref}
\title{SafeAMP-Dual: A Reproducible Protocol for Joint Antimicrobial and Hemolysis Prediction}
\author{Authorship and affiliations not yet verified}
\date{Research protocol draft -- not for submission}
\begin{document}
\maketitle
\begin{abstract}
This document describes an implemented computational evaluation pipeline and the current data-feasibility assessment. It does not report a completed model comparison. The research question is whether joint learning improves the performance trade-off and calibration of antimicrobial and hemolysis prediction under traceable experimental labels and strict sequence separation. The present pilot fails the required partition checks; consequently, training and publication-result generation are blocked. Clinical safety, efficacy and superiority claims are not supported.
\end{abstract}
\section{Research question and scope}
The proposed study concerns unmodified canonical peptides of 10--50 residues. The operational antimicrobial endpoint contrasts Escherichia coli MIC values at most 32 with values at least 128 micrograms per millilitre. The hemolysis endpoint contrasts human-erythrocyte HC50 values at most 100 with values at least 250 micrograms per millilitre. These are exploratory analysis definitions, not clinical decision thresholds. They do not support a species-independent AMP or clinical-safety claim.
\section{Implemented methods and proposed evaluation}
Original source records, accession identifiers, publications, assay fields, retrieval metadata and checksums are retained locally. Unsupported units, ambiguous concentration intervals, intermediate results and conflicting endpoint labels remain missing. Micromolar concentrations are converted using the unmodified sequence molecular weight. Missing outcomes are masked during task-specific loss calculation; they are never converted into negative labels. Database annotations still require review against the cited experimental sources.

All qualifying sequence pairs are compared using global Needleman--Wunsch alignment with match score +2, mismatch score -1 and gap penalty -2. Inputs are oriented lexicographically and traceback prefers diagonal ties. Identity is matches divided by the shorter sequence length. Connected components at identity at least 0.40 cannot cross partitions. This algorithm is explicitly not CD-HIT. Source-separated external assessment, an internal holdout and five grouped development folds are required. Every corresponding training and evaluation subset must contain both observed classes for each endpoint. A failed check prevents formal evaluation.

The implementation reuses frozen ESM-2 8M mean-pooled sequence embeddings and 44 physicochemical descriptors. Seven configurations are implemented: SVM, random forest, gated dual-task network, concatenation dual-task network, physicochemical-only network, ESM-only network and separately trained single-task networks. Seeds are 11, 23 and 42. Hyperparameters are fixed and recorded; there is no claimed search or optimization advantage. Scalers fit training portions only. Networks run for 15 epochs and are refitted on the full development cohort, rather than selecting a single validation-fold checkpoint.

Each task uses logistic calibration of development out-of-fold logit scores with fixed regularization. Thresholds target at least 95 percent specificity on those development scores. Calibration and threshold selection reuse these development predictions, so that subset is labelled selection-only, not unbiased evaluation. Three-seed mean predictions and their own development-selected thresholds are also retained. Neither nominal calibration nor test specificity is guaranteed.

The primary metric is hemolysis average precision (reported as AUPRC), not trapezoidal PR area. Secondary outcomes include task-specific AUROC, MCC, sensitivity, specificity, confusion counts, Brier score and calibration bins. Held-out uncertainty uses 2,000 sequence-component bootstrap resamples. Paired primary comparisons use cluster-level prediction swaps and Holm correction. Intervals are conditional on the fitted models and do not quantify training-set uncertainty; folds and seeds are not independent patient-level replicates.
\section{Current feasibility assessment}
The pilot contains @N@ experimental source records after the declared import filters. These are collection counts, not model-performance evidence. [C001; E001]
\begin{center}
\begin{tabular}{lrrr}\toprule
Endpoint & Positive & Negative & Unobserved/ambiguous \\
\midrule
@TABLE@
\bottomrule\end{tabular}
\end{center}
The current data form @GROUPS@ connected component(s), with @LARGEST@ sequences in the largest component. No independent external source cohort has passed validation. The required five grouped development folds plus holdout are therefore unavailable. No new performance estimate, significance result or superiority conclusion is reported. [C002; E002]
\section{Interpretation boundaries}
Residue displays show fixed physicochemical attributes, not gradients, causal explanations or experimental mechanisms. The product $P(\mathrm{amp})[1-P(\mathrm{hemo})]$ is a computational ranking score, not a therapeutic index or validated joint probability. Mutation proposals are exploratory same-model rankings and are not independent evidence of improved activity or reduced toxicity. The interface explicitly disables model predictions when weights, features or evidence validation are unavailable.
\section{Unresolved work before manuscript preparation}
The isolation protocol requires a scientifically justified prospective decision because the current pilot is infeasible; this implementation does not relax the cutoff. Independent sources, compatible assay coverage, source-use permissions, complete experiments and claim-level literature verification remain necessary. Bibliographic metadata repairs are recorded separately and do not establish that an article supports any particular claim.
\section{Declarations -- unresolved}
Author identities, order, affiliations, contributions, funding, competing interests, ethical applicability, data reuse permissions and author approval remain unverified. A public repository and public deployment have not been verified for this revised version. No statement of compliance, public release or submission approval is made. Computational assistance to code and drafting must be reviewed and disclosed by the accountable authors according to their selected venue's rules.
\end{document}
'''.replace('@N@',str(len(records))).replace('@TABLE@',table).replace('@GROUPS@',str(split.get('groups','unavailable'))).replace('@LARGEST@',str(split.get('largest_cluster','unavailable')))
    (ROOT/'04_paper/manuscript.tex').write_text(manuscript,encoding='utf-8')
    report=f'''# SafeAMP-Dual 整改状态

正式投稿状态：**阻断**。软件实现不等于完成科学验证。

- 公开数据试采样：{len(records)} 条；数据 SHA256：{digest}。
- 抗菌标签：阳性 {a['positive']}、阴性 {a['negative']}、未知 {a['unknown']}。
- 溶血标签：阳性 {h['positive']}、阴性 {h['negative']}、未知 {h['unknown']}。
- 40% 一致性连通簇：{split.get('groups')} 个；最大簇 {split.get('largest_cluster')} 条。
- 缺少通过验证的来源隔离外部队列；五折加内部留出不可行。
- 未产生新的正式模型权重、主结果、消融结果或显著性结论。

代码已实现：逐条来源和原始文件哈希、缺失标签掩码、全成员序列隔离、七模型和三种子固定实验、训练内预处理、全开发集重训、逐样本预测、开发集校准和阈值、簇重采样、产物统一导出、权重和真实 ESM 失效保护。

后续必须解决：预先确定可行且科学合理的隔离设计；取得端点兼容的独立来源；通过数据门禁后完整运行实验；由作者核对原始实验来源、引用用途和全部声明。不能将本次软件测试作为模型性能验证。

数据证据：{(source/'records.csv').relative_to(ROOT).as_posix()}；划分证据：{(prepared/'manifest.json').relative_to(ROOT).as_posix()}。
'''
    (ROOT/'docs/REMEDIATION_STATUS.md').write_text(report,encoding='utf-8')
    print({'publication_ready':False,'records':len(records),'groups':split.get('groups'),'reason':split.get('reason')})


def generate_current_status(prepared_dir, run_dir=None) -> dict:
    """Derive project status from validated prepared dataset and optional completed run artifacts."""
    prepared_path = Path(prepared_dir)
    prep_manifest_file = prepared_path / "manifest.json"
    if not prep_manifest_file.exists():
        raise ValueError(f"Prepared directory does not contain manifest.json: {prepared_path}")
    
    prep_manifest = read_json(prep_manifest_file)
    prep_status = prep_manifest.get("status", "unknown")
    protocol_id = prep_manifest.get('protocol_id')
    protocol_digest = prep_manifest.get('protocol_digest')
    
    blockers = []
    if prep_status != "validated":
        reason = prep_manifest.get("reason") or prep_manifest.get("failure_reasons") or f"Preparation status is {prep_status}"
        blockers.append(f"Dataset preparation not validated: {reason}")
    from research_protocol_config import get_protocol, check_protocol_conflicts, protocol_digest as digest_of
    from dataclasses import asdict
    try:
        spec = get_protocol(protocol_id)
        has_conflict, conflict_reason = check_protocol_conflicts(spec)
        if has_conflict:
            blockers.append(conflict_reason)
        if protocol_id == 'protocol-amd-02' and (
            prep_manifest.get('protocol_spec') != asdict(spec) or protocol_digest != digest_of(spec)
        ):
            blockers.append('Prepared protocol specification or digest does not match the frozen protocol.')
    except KeyError as exc:
        blockers.append(str(exc))
    
    run_status = "none"
    formal_results = False
    pub_ready = False
    run_path = Path(run_dir) if run_dir else None
    
    if run_path is not None:
        run_manifest_file = run_path / "manifest.json"
        if not run_manifest_file.exists():
            blockers.append(f"Run manifest missing: {run_manifest_file}")
            run_status = "missing"
        else:
            run_manifest = read_json(run_manifest_file)
            run_status = run_manifest.get("status", "unknown")
            if run_status == "completed":
                from run_artifacts import validate_run_artifacts
                try:
                    validate_run_artifacts(run_path)
                    formal_results = bool(run_manifest.get("formal_results_available", False))
                    pub_ready = bool(run_manifest.get("publication_ready", False))
                    if not formal_results:
                        blockers.append("Run completed but formal_results_available is false")
                except Exception as exc:
                    formal_results = False
                    blockers.append(f"Run artifact validation failed: {exc}")
            else:
                blockers.append(f"Run status is not completed: {run_status}")
    else:
        blockers.append("No experimental run evaluated (run_dir=None)")

    research_ready = prep_status == 'validated' and run_status == 'completed' and formal_results and not blockers
    if not pub_ready:
        blockers.append("Publication submission requires formal human review and approval receipt")

    next_steps = []
    if protocol_id != 'protocol-amd-02' or any('protocol specification' in item.lower() for item in blockers):
        next_steps.append('Establish a scientifically justified, prespecified feasible isolation protocol.')
    if prep_status != 'validated':
        next_steps.append('Acquire an independently sourced cohort with compatible measurements and audit cross-cohort homology.')
    if run_status != 'completed' or not formal_results:
        next_steps.append('Complete seven-model three-seed grouped experiments only after all data gates pass.')
    if not pub_ready:
        next_steps.append('Review source reuse terms, bibliographic claim support, authorship and all declarations.')

    state = {
        "schema_version": 2,
        "generated_at": utc_now(),
        "status": "ready" if research_ready else "blocked",
        "dataset_preparation_status": prep_status,
        "protocol_id": protocol_id,
        "protocol_digest": protocol_digest,
        "records_input_sha256": prep_manifest.get('records_input_sha256'),
        "prepared_created_at": prep_manifest.get('created_at'),
        "run_status": run_status,
        "formal_results_available": formal_results,
        "publication_ready": pub_ready,
        "prepared_dir": str(prepared_path.resolve()),
        "prepared_sha256": sha256(prep_manifest_file),
        "run_dir": str(run_path.resolve()) if run_path else None,
        "run_sha256": sha256(run_path / "manifest.json") if run_path and (run_path / "manifest.json").exists() else None,
        "blockers": blockers,
        "required_next_steps": next_steps,
    }
    return state


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=None, help='Legacy source directory for historical blocked pilot report')
    p.add_argument('--prepared', type=Path, required=True, help='Path to prepared dataset directory')
    p.add_argument('--run', type=Path, default=None, help='Path to experiment run directory')
    p.add_argument('--output', type=Path, default=None, help='Output path for status JSON')
    a = p.parse_args()
    if a.source is not None:
        generate(a.source, a.prepared)
    else:
        st = generate_current_status(a.prepared, a.run)
        if a.output:
            write_json(a.output, st)
        print({
            "dataset_preparation_status": st["dataset_preparation_status"],
            "run_status": st["run_status"],
            "formal_results_available": st["formal_results_available"],
            "publication_ready": st["publication_ready"],
            "blockers_count": len(st["blockers"])
        })

