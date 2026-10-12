"""FastAPI router for DTI affinity prediction, kinome profiling, and benchmark exploration."""
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "02_code"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dti_inference_runtime import DTIInferenceRuntime
from dti_evidence import get_evidence_status, evidence_for_result

router = APIRouter(prefix="/api/dti", tags=["DTI Kinase Affinity"])
dti_runtime = DTIInferenceRuntime()
logger = logging.getLogger(__name__)


class DTIPredictionRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048, description="SMILES string of the small molecule")
    target_sequence: str = Field(..., min_length=10, max_length=4096, description="Amino acid sequence of the target kinase")
    model_name: Optional[str] = Field(None, description="Model name; omit to use the verified F1 Ridge default when deployed")


class DTIBatchPredictionRequest(BaseModel):
    pairs: List[DTIPredictionRequest] = Field(..., min_length=1, max_length=64)


class DTIProfileRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048, description="SMILES string of the small molecule")
    model_name: Optional[str] = Field(None, description="Profiling model name")


class DTIOptimizeLeadRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048, description="SMILES string of the starting molecule")
    target_sequence: str = Field(..., min_length=10, max_length=4096, description="Amino acid sequence of the target kinase")
    target_name: Optional[str] = Field("Target Kinase", description="Target kinase symbol or name")
    optimization_goal: Optional[str] = Field("提升亲和力与结合强度", description="Optimization goal")
    custom_instruction: Optional[str] = Field("", description="Custom medicinal chemistry instruction")
    model_name: Optional[str] = Field("stacked_ensemble", description="Scoring model name")
    llm_config: Optional[dict] = Field(None, description="Optional LLM connection config from frontend settings")


@router.get("/status")
def get_dti_status():
    """Get DTI runtime status, protocol metadata, and baseline metrics."""
    return dti_runtime.get_status()

@router.get('/evidence_status')
def get_dti_evidence_status():
    """Read published review status without loading a model or running prediction."""
    return get_evidence_status()


@router.get("/drugs")
def list_dti_drugs():
    """List 68 clinical kinase inhibitors available in DAVIS benchmark with common names."""
    dti_runtime.load()
    return [
        {
            "id": d["id"],
            "name": d.get("name", f"CID-{d['id']}"),
            "smiles": d["smiles"],
            "fold": d["fold"],
            "is_test": (d["fold"] == 5)
        }
        for d in dti_runtime.drugs.values()
    ]


@router.get("/targets")
def list_dti_targets():
    """List 379 human catalytic protein kinase targets in DAVIS benchmark with full sequences."""
    dti_runtime.load()
    return [
        {
            "id": t["id"],
            "canonical_gene_symbol": t.get("canonical_gene_symbol", t["id"]),
            "standard_display_name": t.get("standard_display_name", f"{t['id']} (Gene-Max)"),
            "is_misleading_mutation_label": t.get("is_misleading_mutation_label", False),
            "misleading_label_type": t.get("misleading_label_type", "none"),
            "target_semantic_type": t.get("target_semantic_type", "Gene-level maximal affinity representative"),
            "curation_note": t.get("curation_note", ""),
            "length": t["length"],
            "sequence": t["sequence"],
            "fold": t["fold"],
            "is_test": (t["fold"] == 5)
        }
        for t in dti_runtime.targets.values()
    ]


@router.post("/predict")
def predict_dti_affinity(req: DTIPredictionRequest):
    """Predict binding affinity (pKd and Kd in nM) between small molecule and target kinase."""
    try:
        result = dti_runtime.predict(
            drug_smiles=req.drug_smiles,
            target_sequence=req.target_sequence,
            model_name=req.model_name
        )
        result['research_evidence'] = evidence_for_result()
        return result
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Prediction failed: {str(exc)}") from exc


@router.post("/predict_batch")
def predict_dti_affinity_batch(req: DTIBatchPredictionRequest):
    """Batch predict binding affinities for multiple drug-target pairs."""
    results = []
    for item in req.pairs:
        try:
            res = dti_runtime.predict(
                drug_smiles=item.drug_smiles,
                target_sequence=item.target_sequence,
                model_name=item.model_name
            )
            res['research_evidence'] = evidence_for_result()
            results.append(res)
        except Exception as exc:
            results.append({"error": f"Prediction failed: {str(exc)}", "status": "failed"})
    return results


@router.post("/profile_panel")
def profile_dti_kinase_panel(req: DTIProfileRequest):
    """Screen small molecule against representative 16-kinase diversity panel to assess selectivity."""
    try:
        results = dti_runtime.profile_kinase_panel(
            drug_smiles=req.drug_smiles,
            model_name=req.model_name
        )
        evidence = evidence_for_result()
        for result in results:
            result['research_evidence'] = evidence
        return results
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Kinome profiling failed: {str(exc)}") from exc


@router.get("/models")
def list_dti_models():
    """List all available inference models with honest, verified metrics from rigorous benchmark."""
    dti_runtime.load()

    if "f1_ridge" in dti_runtime.model_registration_errors:
        raise HTTPException(status_code=503, detail="F1模型校验失败，请检查部署文件；未静默替换默认模型。")
    # Load verified rigorous metrics summary if available
    rigorous_metrics_path = ROOT / "03_experiments/runs/dti_davis_rigorous_20261009_v1/metrics_summary.json"
    metrics_data = {}
    if rigorous_metrics_path.exists():
        try:
            with open(rigorous_metrics_path, "r", encoding="utf-8") as f:
                metrics_data = json.load(f).get("models", {})
        except Exception:
            metrics_data = {}

    def get_dom_metric(m_id: str, dom: str, metric_name: str) -> Optional[float]:
        bare_id = m_id.replace("rigorous_", "")
        sub = metrics_data.get(bare_id) or metrics_data.get(m_id)
        if sub and dom in sub.get("domains", {}):
            val = sub["domains"][dom].get(metric_name)
            return float(val) if val is not None else None
        return None

    benchmark_ver = "dti_davis_rigorous_20261009_v1" if metrics_data else "unverified"

    models_meta = [
        {
            "id": "rigorous_stacked_ensemble",
            "name": "Stacking 堆叠集成 (GroupKFold 实体分组验证)",
            "badge": f"历史基准 · 双冷CI {get_dom_metric('stacked_ensemble', 'strict_dual_cold_test', 'concordance_index') or '未核实'}",
            "badge_color": "emerald",
            "desc": "历史复合特征集成，按20261009版本的评价范围解读。",
            "benchmark_version": benchmark_ver,
            "is_recommended": True,
            "train_ci": get_dom_metric("stacked_ensemble", "train_block", "concordance_index"),
            "dual_cold_ci": get_dom_metric("stacked_ensemble", "strict_dual_cold_test", "concordance_index"),
            "cold_target_ci": get_dom_metric("stacked_ensemble", "cold_target_test", "concordance_index"),
            "cold_drug_ci": get_dom_metric("stacked_ensemble", "cold_drug_test", "concordance_index")
        },
        {
            "id": "rigorous_ridge_alpha50",
            "name": "Ridge α=50 (强正则化线性)",
            "badge": f"历史基准 · 双冷CI {get_dom_metric('ridge_alpha50', 'strict_dual_cold_test', 'concordance_index') or '未核实'}",
            "badge_color": "indigo",
            "desc": "历史复合特征Ridge，保留为显式可选的比较模型。",
            "benchmark_version": benchmark_ver,
            "is_recommended": False,
            "train_ci": get_dom_metric("ridge_alpha50", "train_block", "concordance_index"),
            "dual_cold_ci": get_dom_metric("ridge_alpha50", "strict_dual_cold_test", "concordance_index"),
            "cold_target_ci": get_dom_metric("ridge_alpha50", "cold_target_test", "concordance_index"),
            "cold_drug_ci": get_dom_metric("ridge_alpha50", "cold_drug_test", "concordance_index")
        },
        {
            "id": "rigorous_ridge_alpha10",
            "name": "Ridge α=10 (标准岭回归)",
            "badge": f"历史基准 · 冷药CI {get_dom_metric('ridge_alpha10', 'cold_drug_test', 'concordance_index') or '未核实'}",
            "badge_color": "slate",
            "desc": "历史线性基准，按对应版本和评价域比较。",
            "benchmark_version": benchmark_ver,
            "is_recommended": False,
            "train_ci": get_dom_metric("ridge_alpha10", "train_block", "concordance_index"),
            "dual_cold_ci": get_dom_metric("ridge_alpha10", "strict_dual_cold_test", "concordance_index"),
            "cold_target_ci": get_dom_metric("ridge_alpha10", "cold_target_test", "concordance_index"),
            "cold_drug_ci": get_dom_metric("ridge_alpha10", "cold_drug_test", "concordance_index")
        },
        {
            "id": "rigorous_hist_gradient_boosting",
            "name": "HistGBM 梯度提升决策树",
            "badge": f"历史基准 · 双冷CI {get_dom_metric('hist_gradient_boosting', 'strict_dual_cold_test', 'concordance_index') or '未核实'}",
            "badge_color": "amber",
            "desc": "历史梯度提升模型；各输入域的性能按登记指标解读。",
            "benchmark_version": benchmark_ver,
            "is_recommended": False,
            "train_ci": get_dom_metric("hist_gradient_boosting", "train_block", "concordance_index"),
            "dual_cold_ci": get_dom_metric("hist_gradient_boosting", "strict_dual_cold_test", "concordance_index"),
            "cold_target_ci": get_dom_metric("hist_gradient_boosting", "cold_target_test", "concordance_index"),
            "cold_drug_ci": get_dom_metric("hist_gradient_boosting", "cold_drug_test", "concordance_index")
        },
        {
            "id": "rigorous_random_forest",
            "name": "Random Forest 随机森林",
            "badge": f"历史基准 · 冷靶CI {get_dom_metric('random_forest', 'cold_target_test', 'concordance_index') or '未核实'}",
            "badge_color": "purple",
            "desc": "历史随机森林模型，不将单域排名扩展为所有新输入的优势。",
            "benchmark_version": benchmark_ver,
            "is_recommended": False,
            "train_ci": get_dom_metric("random_forest", "train_block", "concordance_index"),
            "dual_cold_ci": get_dom_metric("random_forest", "strict_dual_cold_test", "concordance_index"),
            "cold_target_ci": get_dom_metric("random_forest", "cold_target_test", "concordance_index"),
            "cold_drug_ci": get_dom_metric("random_forest", "cold_drug_test", "concordance_index")
        }
    ]
    # Filter only verified, available models in runtime
    avail = set(dti_runtime.models.keys())
    matched = [m for m in models_meta if m["id"] in avail]
    for metadata in matched:
        source = metrics_data.get(metadata["id"].replace("rigorous_", ""), {})
        metadata["metrics_by_domain"] = source.get("domains", {})
        metadata["evaluation_scope"] = "历史登记基准；按模型版本解读，非独立盲测。"
    if dti_runtime.f1_predictor is not None and "f1_ridge" in avail:
        for metadata in matched:
            metadata["is_recommended"] = False
        matched.insert(0, dti_runtime.f1_predictor.model_metadata())
    if getattr(dti_runtime, "bilinear_predictor", None) is not None and "bilinear_esm2_interaction" in avail:
        matched.insert(1, dti_runtime.bilinear_predictor.model_metadata())
    return matched


class BiophysicsInsightRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048)
    target_sequence: str = Field(..., min_length=10, max_length=4096)
    gatekeeper_override: Optional[str] = None


@router.post("/biophysics_insights")
def get_biophysics_insights(req: BiophysicsInsightRequest):
    """Compute 3D structural induced-fit and first-principles MM-GBSA thermodynamic decomposition."""
    try:
        from kinase_conformation_adapter import compute_induced_fit_interaction
        from thermodynamic_physics_engine import predict_physical_affinity_dti

        clean_seq = "".join(req.target_sequence.split()).upper()
        clean_smi = req.drug_smiles.strip()

        fit_res = compute_induced_fit_interaction(clean_seq, clean_smi, gatekeeper_override=req.gatekeeper_override)
        phys_res = predict_physical_affinity_dti(clean_seq, clean_smi)

        mode_labels = {
            "type_i": "Type I (经典 ATP 铰链区竞争性结合)",
            "type_ii": "Type II (活化环 DFG-out 变构深腔填充结合)",
            "covalent": "共价结合 (亲核半胱氨酸不可逆加成结合)"
        }

        return {
            "binding_mode": fit_res.binding_mode,
            "binding_mode_label": mode_labels.get(fit_res.binding_mode, fit_res.binding_mode),
            "preferred_conformation": fit_res.preferred_conformation,
            "dfg_flip_penalty_kcal": round(fit_res.dfg_flip_penalty_kcal, 2),
            "induced_fit_score": round(fit_res.induced_fit_score, 2),
            "base_dock_score": round(fit_res.base_dock_score, 2),
            "hinge_score": round(fit_res.details.get("hinge_score", 0.0), 3),
            "gatekeeper_clash": round(fit_res.details.get("gatekeeper_clash", 0.0), 2),
            "mmgbsa": {
                "delta_g_bind": round(phys_res.delta_g_bind, 2),
                "delta_e_vdw": round(phys_res.delta_e_vdw, 2),
                "delta_e_elec": round(phys_res.delta_e_elec, 2),
                "delta_g_gb": round(phys_res.delta_g_gb, 2),
                "delta_g_sa": round(phys_res.delta_g_sa, 2),
                "minus_t_delta_s": round(phys_res.minus_t_delta_s, 2),
                "phys_predicted_pkd": round(phys_res.predicted_pkd, 2),
                "rotatable_bonds": int(phys_res.physics_descriptors[6]),
                "buried_sasa": round(float(phys_res.physics_descriptors[7]), 1)
            }
        }
    except Exception as exc:
        logger.exception("Biophysics insights computation failed")
        raise HTTPException(status_code=422, detail=f"3D 生物物理计算失败: {str(exc)}") from exc


class ActiveLearningPoolRequest(BaseModel):
    target_sequence: str = Field(..., min_length=10, max_length=4096)
    target_name: Optional[str] = "Target Kinase"
    candidates: List[dict] = Field(..., min_length=1, max_length=50) # [{"name": "...", "smiles": "..."}]
    y_best: Optional[float] = 7.50


@router.post("/active_learning")
def evaluate_active_learning(req: ActiveLearningPoolRequest):
    """Evaluate candidate pool with Bayesian Acquisition Functions and 4-quadrant exploration/exploitation."""
    try:
        from active_learning_recommender import evaluate_active_learning_pool

        clean_seq = "".join(req.target_sequence.split()).upper()
        pool = [(c.get("name", f"Molecule-{i}"), c["smiles"]) for i, c in enumerate(req.candidates)]
        report = evaluate_active_learning_pool(
            target_sequence=clean_seq,
            candidate_pool=pool,
            target_name=req.target_name or "Target Kinase",
            y_best=req.y_best or 7.50,
            runtime=dti_runtime
        )
        return {
            "target_name": report.target_name,
            "total_evaluated": report.total_evaluated,
            "y_best_reference": report.y_best_reference,
            "confident_hits": [c.__dict__ for c in report.confident_hits],
            "breakthrough_hypotheses": [c.__dict__ for c in report.breakthrough_hypotheses],
            "high_information_gain_blindspots": [c.__dict__ for c in report.high_information_gain_blindspots],
            "known_inactives": [c.__dict__ for c in report.known_inactives],
            "research_evidence": evidence_for_result(),
            "markdown_summary": report.export_markdown()
        }
    except Exception as exc:
        logger.exception("Active learning evaluation failed")
        raise HTTPException(status_code=422, detail=f"主动学习评估失败: {str(exc)}") from exc


@router.post("/optimize_lead")
@router.post("/optimize-lead")
def optimize_dti_lead(req: DTIOptimizeLeadRequest):
    """AI-assisted and heuristic lead molecular optimization and quantitative affinity scoring loop."""
    try:
        from dti_lead_optimizer import DTILeadOptimizer
        optimizer = DTILeadOptimizer(dti_runtime)
        result = optimizer.optimize(
            drug_smiles=req.drug_smiles,
            target_sequence=req.target_sequence,
            target_name=req.target_name or "Target Kinase",
            optimization_goal=req.optimization_goal or "提升亲和力与结合强度",
            custom_instruction=req.custom_instruction or "",
            model_name=req.model_name,
            llm_config=req.llm_config
        )
        result['research_evidence'] = evidence_for_result()
        return result
    except Exception as exc:
        logger.exception("Lead optimization failed")
        raise HTTPException(status_code=422, detail=f"先导化合物优化执行失败: {str(exc)}") from exc


class DTIPocketRequest(BaseModel):
    target_name: str = Field("ABL1", min_length=1, max_length=100)
    drug_name: Optional[str] = Field("Dasatinib", max_length=200)
    drug_smiles: Optional[str] = Field(None, max_length=2048)


@router.post("/pocket_structure")
def get_kinase_pocket_structure(req: DTIPocketRequest):
    """Retrieve 3D kinase catalytic pocket structure and key residue annotations for 3Dmol.js rendering."""
    try:
        from kinase_pocket_structure_service import get_kinase_pocket_3d
        return get_kinase_pocket_3d(
            target_name=req.target_name,
            drug_name=req.drug_name,
            drug_smiles=req.drug_smiles
        )
    except Exception as exc:
        logger.exception("Failed to retrieve 3D pocket structure")
        raise HTTPException(status_code=422, detail=f"3D 口袋结构解算失败: {str(exc)}") from exc


class ADMETRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048, description="SMILES string of molecule")


@router.post("/predict_admet")
def predict_dti_admet(req: ADMETRequest):
    """Predict ADMET pharmacokinetic, safety, and drug-likeness health profile."""
    try:
        from admet_predictor import predict_admet_properties
        result = predict_admet_properties(req.drug_smiles)
        return result.to_dict()
    except Exception as exc:
        logger.exception("Failed to predict ADMET properties")
        raise HTTPException(status_code=422, detail=f"ADMET成药性解算失败: {str(exc)}") from exc


class DTIWetlabDispatchRequest(BaseModel):
    target_name: str = Field("Target Kinase", max_length=100)
    baseline: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    plate_barcode: Optional[str] = None


@router.post("/wetlab_dispatch")
def generate_wetlab_dispatch_plate(req: DTIWetlabDispatchRequest):
    """Generate 96-well microplate layout, priority tiers, liquid-handling controls, and CSV manifest."""
    try:
        from wetlab_dispatch_generator import generate_96_well_dispatch
        return generate_96_well_dispatch(
            target_name=req.target_name,
            baseline=req.baseline,
            candidates=req.candidates,
            plate_barcode=req.plate_barcode
        )
    except Exception as exc:
        logger.exception("Failed to generate wetlab dispatch plate")
        raise HTTPException(status_code=422, detail=f"96孔板投产清单解算失败: {str(exc)}") from exc


class DTIAcademicReportRequest(BaseModel):
    target_name: str = Field("Target Kinase", max_length=100)
    baseline: Dict[str, Any]
    candidates: List[Dict[str, Any]]
    biophysics: Optional[Dict[str, Any]] = None
    admet: Optional[Dict[str, Any]] = None
    active_learning: Optional[Dict[str, Any]] = None
    author: Optional[str] = "SafeAMP-Dual BioAI Laboratory"
    model_used: Optional[str] = Field(None, max_length=100)


@router.post("/academic_report")
def generate_dti_report(req: DTIAcademicReportRequest):
    """Generate comprehensive academic research brief and patent disclosure in Markdown and printable HTML."""
    try:
        from dti_report_generator import generate_dti_academic_report
        result = generate_dti_academic_report(
            target_name=req.target_name,
            baseline=req.baseline,
            candidates=req.candidates,
            biophysics=req.biophysics,
            admet=req.admet,
            active_learning=req.active_learning,
            author=req.author or "SafeAMP-Dual BioAI Laboratory"
        )
        evidence = evidence_for_result()
        notice = evidence['message']
        review_date = evidence.get('reviewed_at') or '无法确认'
        metric_state = '未评估' if evidence['status'] == 'available' else '无法确认'
        model_used = req.model_used or '未报告'
        template_notice = '本报告为模板草稿；缺失的结构、自由能或ADMET输入可能使用模板默认值，这些字段不是已确认的计算或实验结果。'
        diagnostic = evidence.get('model_diagnostics', {}).get(model_used)
        limitation_notice = ('已有冻结F1版本诊断：' + diagnostic['summary'] + ' 当前报告使用的模型版本尚未核对。') if diagnostic else ''
        result['research_evidence'] = evidence
        result['model_used'] = model_used
        result['markdown_report'] = f'## 报告状态：待人工与实验复核\n\n{template_notice}\n\n调用方记录的亲和力模型：{model_used}。\n\n{limitation_notice}\n\n' + result['markdown_report'] + f'\n\n## 研究证据与适用范围\n\n{notice}\n\n证据复核日期：{review_date}。外部评价指标：{metric_state}。\n'
        from html import escape
        banner = f'<aside style="padding:16px;border:1px solid #d97706;color:#78350f;background:#fffbeb"><strong>研究证据与适用范围 · 待复核草稿</strong><p>{escape(notice)}</p><p>{template_notice}</p><p>{escape(limitation_notice)}</p><p>调用方记录的亲和力模型：{escape(model_used)}。证据复核日期：{escape(review_date)}。外部评价指标：{metric_state}。</p></aside>'
        import re
        result['html_report'], inserted = re.subn(r'(<body\b[^>]*>)', lambda match: match.group(1) + banner, result['html_report'], count=1, flags=re.IGNORECASE)
        if not inserted:
            result['html_report'] = banner + result['html_report']
        return result
    except Exception as exc:
        logger.exception("Failed to generate academic report")
        raise HTTPException(status_code=422, detail=f"学术报告解算生成失败: {str(exc)}") from exc


class DTIWetlabFeedbackRequest(BaseModel):
    target_name: str = Field("Target Kinase", max_length=100)
    candidates: List[Dict[str, Any]]
    measurements: List[Dict[str, Any]]
    y_best_reference: Optional[float] = 7.50


@router.post("/wetlab_feedback")
def calibrate_wetlab_feedback(req: DTIWetlabFeedbackRequest):
    """Recalibrate predictions, shrink uncertainties, and re-rank candidates with wet-lab experimental feedback."""
    try:
        from wetlab_feedback_calibrator import calibrate_with_wetlab_feedback
        return calibrate_with_wetlab_feedback(
            target_name=req.target_name,
            candidates=req.candidates,
            measurements=req.measurements,
            y_best_reference=req.y_best_reference or 7.50
        )
    except Exception as exc:
        logger.exception("Failed to calibrate wetlab feedback")
        raise HTTPException(status_code=422, detail=f"湿实验实测反馈校准失败: {str(exc)}") from exc


@router.get("/clinical_targets")
def get_clinical_targets(
    family: Optional[str] = None,
    include_mutants: bool = True,
    search: Optional[str] = None
):
    """Retrieve catalog of 60+ curated clinical oncology kinases and key resistance mutants."""
    try:
        from target_knowledge_hub import get_all_clinical_targets
        return get_all_clinical_targets(
            family=family,
            include_mutants=include_mutants,
            search_query=search
        )
    except Exception as exc:
        logger.exception("Failed to retrieve clinical targets")
        raise HTTPException(status_code=422, detail=f"临床靶点库获取失败: {str(exc)}") from exc


@router.get("/clinical_target/{symbol}")
def get_clinical_target_profile(symbol: str):
    """Retrieve full clinical profile, resistance mechanism, approved drugs, and UniProt/ChEMBL cross-references."""
    try:
        from target_knowledge_hub import get_clinical_target_by_symbol, fetch_uniprot_chembl_enrichment
        rec = get_clinical_target_by_symbol(symbol)
        if not rec:
            raise HTTPException(status_code=404, detail=f"靶点 {symbol} 未在临床激酶库中收录")
        enrichment = fetch_uniprot_chembl_enrichment(rec["uniprot_id"], rec.get("chembl_id"))
        return {
            **rec,
            "enrichment": enrichment
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve target detail")
        raise HTTPException(status_code=422, detail=f"靶点详情获取失败: {str(exc)}") from exc


class TargetSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100)


@router.post("/search_targets")
def search_clinical_targets_external(req: TargetSearchRequest):
    """Search clinical targets and query UniProt / ChEMBL for bioactivity cross-references."""
    try:
        from target_knowledge_hub import get_all_clinical_targets, fetch_uniprot_chembl_enrichment
        hits = get_all_clinical_targets(search_query=req.query)
        enriched_hits = []
        for h in hits[:10]:
            enrichment = fetch_uniprot_chembl_enrichment(h["uniprot_id"], h.get("chembl_id"))
            enriched_hits.append({
                **h,
                "enrichment": enrichment
            })
        return {
            "query": req.query,
            "total_hits": len(hits),
            "results": enriched_hits
        }
    except Exception as exc:
        logger.exception("Target search failed")
        raise HTTPException(status_code=422, detail=f"靶点检索失败: {str(exc)}") from exc


class DeNovoGenerateRequest(BaseModel):
    target_symbol: str = Field(..., min_length=1, max_length=50, description="Target kinase symbol or mutant e.g. ABL1, ABL1-T315I, EGFR-T790M")
    target_sequence: Optional[str] = Field(None, max_length=4096, description="Optional custom kinase catalytic sequence")
    generation_mode: Optional[str] = Field("scaffold_hopping", description="Generation mode: scaffold_hopping, gatekeeper_bypasser, pocket_growth")
    num_candidates: Optional[int] = Field(6, ge=1, le=12, description="Number of candidates to generate")
    novelty_floor: Optional[float] = Field(0.30, ge=0.0, le=0.9, description="Minimum IP novelty threshold")


class RetrosynthesisRequest(BaseModel):
    smiles: str = Field(..., min_length=2, max_length=2048, description="Target small molecule SMILES")
    molecule_name: Optional[str] = Field("Target Molecule", description="Target molecule display name")


@router.post("/de_novo_generate")
def de_novo_pocket_generation(req: DeNovoGenerateRequest):
    """Generate 3D-pocket conditioned small molecules with high IP novelty and MM-GBSA binding evaluation."""
    try:
        from pocket_de_novo_generator import generate_de_novo_pocket_molecules
        result = generate_de_novo_pocket_molecules(
            target_symbol=req.target_symbol,
            target_sequence=req.target_sequence,
            generation_mode=req.generation_mode or "scaffold_hopping",
            num_candidates=req.num_candidates or 6,
            novelty_floor=req.novelty_floor or 0.30
        )
        return result
    except Exception as exc:
        logger.exception("De novo pocket generation failed")
        raise HTTPException(status_code=422, detail=f"从头分子生成失败: {str(exc)}") from exc


@router.post("/retrosynthesis_plan")
def retrosynthesis_route_planning(req: RetrosynthesisRequest):
    """Plan multi-step retrosynthesis route with commercial CAS precursors and reaction conditions."""
    try:
        from retrosynthesis_planner import plan_retrosynthesis_route
        result = plan_retrosynthesis_route(
            smiles=req.smiles,
            molecule_name=req.molecule_name
        )
        return result
    except Exception as exc:
        logger.exception("Retrosynthesis planning failed")
        raise HTTPException(status_code=422, detail=f"逆合成路线规划失败: {str(exc)}") from exc


class VirtualScreeningRequest(BaseModel):
    target_symbol: str = Field(..., min_length=1, max_length=50, description="Target kinase symbol or mutant e.g. ABL1, EGFR-T790M")
    target_sequence: Optional[str] = Field(None, max_length=4096, description="Optional custom target sequence")
    library_id: Optional[str] = Field("kinase_privileged", description="Screening library ID: kinase_privileged, enamine_diversity, fda_approved_derivatives")
    custom_compounds: Optional[List[Dict[str, Any]]] = Field(None, description="Optional custom compounds list with id, name, smiles")
    max_hits: Optional[int] = Field(15, ge=1, le=100, description="Maximum top hits to report")
    min_pkd_threshold: Optional[float] = Field(5.0, ge=3.0, le=12.0, description="Minimum pKd cutoff threshold")
    diversity_cutoff: Optional[float] = Field(0.40, ge=0.1, le=0.9, description="Butina clustering Tanimoto distance cutoff")


@router.get("/screening_libraries")
def list_screening_libraries():
    """List available pre-indexed commercial virtual screening libraries and their statistics."""
    try:
        from virtual_screening_engine import get_screening_libraries_metadata
        return get_screening_libraries_metadata()
    except Exception as exc:
        logger.exception("Failed to retrieve screening libraries")
        raise HTTPException(status_code=422, detail=f"分子库列表获取失败: {str(exc)}") from exc


@router.post("/virtual_screen")
def execute_virtual_screening(req: VirtualScreeningRequest):
    """Execute high-throughput hierarchical virtual screening on commercial libraries or custom compounds."""
    try:
        from virtual_screening_engine import screen_virtual_library
        result = screen_virtual_library(
            target_symbol=req.target_symbol,
            target_sequence=req.target_sequence,
            library_id=req.library_id or "kinase_privileged",
            custom_compounds=req.custom_compounds,
            max_hits=req.max_hits or 15,
            min_pkd_threshold=req.min_pkd_threshold or 5.0,
            diversity_cutoff=req.diversity_cutoff or 0.40
        )
        return result
    except Exception as exc:
        logger.exception("Virtual screening failed")
        raise HTTPException(status_code=422, detail=f"虚拟筛选执行失败: {str(exc)}") from exc
