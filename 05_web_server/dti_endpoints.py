"""FastAPI router for DTI affinity prediction, kinome profiling, and benchmark exploration."""
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_code"))
from dti_inference_runtime import DTIInferenceRuntime

router = APIRouter(prefix="/api/dti", tags=["DTI Kinase Affinity"])
dti_runtime = DTIInferenceRuntime()
logger = logging.getLogger(__name__)


class DTIPredictionRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048, description="SMILES string of the small molecule")
    target_sequence: str = Field(..., min_length=10, max_length=4096, description="Amino acid sequence of the target kinase")
    model_name: Optional[str] = Field("stacked_ensemble", description="Model name (stacked_ensemble, ridge_alpha10, ridge, hist_gradient_boosting, mlp, dummy_mean)")


class DTIBatchPredictionRequest(BaseModel):
    pairs: List[DTIPredictionRequest] = Field(..., min_length=1, max_length=64)


class DTIProfileRequest(BaseModel):
    drug_smiles: str = Field(..., min_length=2, max_length=2048, description="SMILES string of the small molecule")
    model_name: Optional[str] = Field("stacked_ensemble", description="Profiling model name")


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
            model_name=req.model_name or "stacked_ensemble"
        )
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
                model_name=item.model_name or "stacked_ensemble"
            )
            results.append(res)
        except Exception as exc:
            results.append({"error": str(exc)})
    return results


@router.post("/profile_panel")
def profile_dti_kinase_panel(req: DTIProfileRequest):
    """Screen small molecule against representative 16-kinase diversity panel to assess selectivity."""
    try:
        return dti_runtime.profile_kinase_panel(
            drug_smiles=req.drug_smiles,
            model_name=req.model_name or "stacked_ensemble"
        )
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Kinome profiling failed: {str(exc)}") from exc


@router.get("/models")
def list_dti_models():
    """List all available inference models with descriptive metadata and recommended flags."""
    dti_runtime.load()
    models_meta = [
        {
            "id": "worldmodel_stacked_ensemble",
            "name": "★ 第二代生物世界模型 (WorldModel Stacked Ensemble)",
            "badge": "最新旗舰 · CI 0.8652",
            "badge_color": "emerald",
            "desc": "千万级 Uni-Mol 3D 构象流形 + ESM-2 进化全长保守性表征",
            "is_recommended": True,
            "train_ci": 0.8652,
            "train_mae": 0.3120,
            "cold_target_ci": 0.7447,
            "cold_drug_ci": 0.7619
        },
        {
            "id": "stacked_ensemble",
            "name": "第一代 Stacking 经典集成",
            "badge": "经典基线 · CI 0.7571",
            "badge_color": "blue",
            "desc": "2D Morgan 指纹 + 激酶催化深腔 100 维特征元学习融合",
            "is_recommended": False,
            "train_ci": 0.8494,
            "train_mae": 0.3442,
            "cold_target_ci": 0.7289,
            "cold_drug_ci": 0.7504
        },
        {
            "id": "ridge_alpha10",
            "name": "Ridge α=10 (强正则化)",
            "badge": "双盲泛化最优",
            "badge_color": "indigo",
            "desc": "高维特征强 L2 收缩，抗严重外推分布偏移",
            "is_recommended": False,
            "train_ci": 0.8315,
            "train_mae": 0.3951,
            "cold_target_ci": 0.7281,
            "cold_drug_ci": 0.7504
        },
        {
            "id": "ridge",
            "name": "Ridge 标准岭回归",
            "badge": "经典线性基准",
            "badge_color": "slate",
            "desc": "线性特征映射标准基准标尺",
            "is_recommended": False,
            "train_ci": 0.8241,
            "train_mae": 0.4082,
            "cold_target_ci": 0.7180,
            "cold_drug_ci": 0.7262
        },
        {
            "id": "hist_gradient_boosting",
            "name": "HistGBM 梯度提升树",
            "badge": "非线性树模型",
            "badge_color": "amber",
            "desc": "高效分箱直方图梯度提升决策树",
            "is_recommended": False,
            "train_ci": 0.8450,
            "train_mae": 0.3512,
            "cold_target_ci": 0.7102,
            "cold_drug_ci": 0.7155
        },
        {
            "id": "mlp",
            "name": "MLP 深度多层感知机",
            "badge": "深度神经网络",
            "badge_color": "purple",
            "desc": "非线性特征交叉隐藏层深度表征",
            "is_recommended": False,
            "train_ci": 0.8390,
            "train_mae": 0.3621,
            "cold_target_ci": 0.7051,
            "cold_drug_ci": 0.7090
        },
        {
            "id": "dummy_mean",
            "name": "Dummy 统计基准",
            "badge": "均值绝对下界",
            "badge_color": "rose",
            "desc": "常数预测对比标尺",
            "is_recommended": False,
            "train_ci": 0.5000,
            "train_mae": 0.5512,
            "cold_target_ci": 0.5000,
            "cold_drug_ci": 0.5000
        }
    ]
    # Filter only available models
    avail = set(dti_runtime.models.keys())
    return [m for m in models_meta if m["id"] in avail]


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
            "markdown_summary": report.export_markdown()
        }
    except Exception as exc:
        logger.exception("Active learning evaluation failed")
        raise HTTPException(status_code=422, detail=f"主动学习评估失败: {str(exc)}") from exc


@router.post("/optimize_lead")
def optimize_dti_lead(req: DTIOptimizeLeadRequest):
    """AI-assisted and heuristic lead molecular optimization and quantitative affinity scoring loop."""
    try:
        from dti_lead_optimizer import DTILeadOptimizer
        optimizer = DTILeadOptimizer(dti_runtime)
        return optimizer.optimize(
            drug_smiles=req.drug_smiles,
            target_sequence=req.target_sequence,
            target_name=req.target_name or "Target Kinase",
            optimization_goal=req.optimization_goal or "提升亲和力与结合强度",
            custom_instruction=req.custom_instruction or "",
            model_name=req.model_name or "worldmodel_stacked_ensemble",
            llm_config=req.llm_config
        )
    except Exception as exc:
        logger.exception("Lead optimization failed")
        raise HTTPException(status_code=422, detail="先导化合物优化执行失败，请检查输入分子与靶点序列的合法性。") from exc


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


@router.post("/academic_report")
def generate_dti_report(req: DTIAcademicReportRequest):
    """Generate comprehensive academic research brief and patent disclosure in Markdown and printable HTML."""
    try:
        from dti_report_generator import generate_dti_academic_report
        return generate_dti_academic_report(
            target_name=req.target_name,
            baseline=req.baseline,
            candidates=req.candidates,
            biophysics=req.biophysics,
            admet=req.admet,
            active_learning=req.active_learning,
            author=req.author or "SafeAMP-Dual BioAI Laboratory"
        )
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



