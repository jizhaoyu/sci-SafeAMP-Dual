"""Compute a conservative study-count upper bound before MIC-only fivefold training.

Paper-level matches are not training release. The upper bound deliberately
ignores homology, which can only merge study groups and worsen feasibility.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from research_utils import ROOT, sha256, utc_now, write_json


PAPER_AUDITS = {
    "42206144": "03_experiments/audits/mic_primary_review_20261001_v3",
    "33281785": "03_experiments/audits/mic_primary_review_pmid33281785_20261002_v2",
    "36551368": "03_experiments/audits/mic_primary_review_pmid36551368_20261002_v2",
    "29259134": "03_experiments/audits/mic_primary_review_pmid29259134_20261002_v2",
}
CONFLICTING_RECORDS = {"DBAASP:25512"}
FOLDS = 5


def run(output: Path, assays_path: Path, dramp_path: Path) -> dict:
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite evidence feasibility audit: {output}")
    inputs = [Path(assays_path).resolve(), Path(dramp_path).resolve()]
    assays = pd.read_csv(inputs[0])
    rows = []
    for pmid, relative_dir in PAPER_AUDITS.items():
        directory = ROOT / relative_dir
        manifest_path, review_path = directory / "manifest.json", directory / "record_review.csv"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest["paper"]["pmid"] != pmid
                or manifest["status"] != "blocked_primary_review_in_progress"
                or sha256(review_path) != manifest["outputs"]["record_review.csv"]):
            raise ValueError(f"Paper review is missing, modified, or unexpectedly released: {pmid}")
        inputs.extend((manifest_path, review_path))
        record_ids = set(pd.read_csv(review_path).record_id) - CONFLICTING_RECORDS
        selected = assays[
            assays.record_id.isin(record_ids) & assays.eligible.eq(True)
            & assays.derived_label.notna()
            & assays.assay_study_ids.astype(str).str.contains(f"pmid:{pmid}", regex=False)
        ]
        if not record_ids or set(selected.record_id) != record_ids:
            raise ValueError(f"Reviewed records not covered by frozen assay inventory: {pmid}")
        rows.append({
            "primary_study": f"pmid:{pmid}", "review_level": "paper_level_provisional",
            "records": selected.record_id.nunique(), "binary_observations": len(selected),
            "positive_observations": int(selected.derived_label.eq(1).sum()),
            "negative_observations": int(selected.derived_label.eq(0).sum()),
            "training_released": False,
        })
    dramp = pd.read_csv(inputs[1])
    for pmid in ("22467870", "30658410"):
        selected = dramp[dramp.evidence_reference.astype(str).str.contains(pmid, regex=False)]
        if len(selected) != (3 if pmid == "22467870" else 1) or not selected.amp.eq(1).all():
            raise ValueError(f"Verified DRAMP candidate inventory changed: {pmid}")
        rows.append({
            "primary_study": f"pmid:{pmid}", "review_level": "screened_candidate",
            "records": len(selected), "binary_observations": len(selected),
            "positive_observations": len(selected), "negative_observations": 0,
            "training_released": False,
        })
    studies = pd.DataFrame(rows).sort_values("primary_study")
    negative_studies = int(studies.negative_observations.gt(0).sum())
    positive_studies = int(studies.positive_observations.gt(0).sum())
    # Each disjoint validation fold needs its own study group containing a negative.
    # Linking papers or sequences can merge groups, never increase this upper bound.
    blocker = negative_studies < FOLDS or positive_studies < FOLDS
    output.mkdir(parents=True)
    studies.to_csv(output / "study_counts.csv", index=False)
    report = (
        "# MIC-only 已核对证据的五折必要条件\n\n"
        f"当前 4 篇逐原文核对论文与 2 篇已筛查 DRAMP 候选论文构成至多 {len(studies)} 个来源组；"
        f"含阴性测定的论文只有 {negative_studies} 篇，含阳性的有 {positive_studies} 篇。"
        f"严格论文隔离的 {FOLDS} 折验证，每折都要有阴性，故至少还缺 "
        f"{max(0, FOLDS - negative_studies)} 篇可独立分组且有阴性实测的原始研究。"
        "全员同源边、共同作者或重复测定只可能进一步合并组；此处尚未尝试五折，"
        "也没有以调参或放宽阈值解决不足。\n\n"
        "- PMID 42206144 的 `DBAASP:25512` 有原文冲突，整条记录在此上限估计中排除。\n"
        "- PMID 37938588 的两条候选因 C 端酰胺化与来源清单不符而排除。\n"
        "- 局部论文匹配、单人图片转录和 DRAMP 筛查均不是全队列入训释放；训练状态仍为 `blocked`。\n"
        "- 下一步：寻找至少两篇具有可核查阴性 MIC 的独立原始研究，核实化学形式及条件，"
        "再以新数据版本执行全员同源、论文隔离与固定五折审计。\n"
    )
    (output / "report.md").write_text(report, encoding="utf-8")
    manifest = {
        "status": "blocked", "generated_at": utc_now(), "folds_required": FOLDS,
        "reviewed_primary_studies": len(studies),
        "negative_bearing_studies_upper_bound": negative_studies,
        "positive_bearing_studies_upper_bound": positive_studies,
        "additional_independent_negative_studies_required_at_least": max(0, FOLDS - negative_studies),
        "necessary_study_count_gate_passed": not blocker,
        "records_released_for_training": 0,
        "inputs": {str(path.relative_to(ROOT)): sha256(path) for path in inputs},
        "script_sha256": sha256(Path(__file__)),
        "outputs": {name: sha256(output / name) for name in ("study_counts.csv", "report.md")},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assays", type=Path, default=ROOT / "03_experiments/audits/mic_study_disjoint_20261001_v5/assay_observations.csv")
    parser.add_argument("--dramp", type=Path, default=ROOT / "03_experiments/audits/dramp_verified_ecoli_mic_20261001_v8/records.csv")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output, args.assays, args.dramp), ensure_ascii=False, indent=2))
