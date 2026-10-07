"""FastAPI router for DTI affinity prediction, kinome profiling, and benchmark exploration."""
import logging
import sys
from pathlib import Path
from typing import List, Optional
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
            model_name=req.model_name or "stacked_ensemble",
            llm_config=req.llm_config
        )
    except Exception as exc:
        logger.exception("Lead optimization failed")
        raise HTTPException(status_code=422, detail="先导化合物优化执行失败，请检查输入分子与靶点序列的合法性。") from exc
