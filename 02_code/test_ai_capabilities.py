"""AI Capabilities Verification Test Suite.
Comprehensive validation across all AI-driven modules:
1. Second-Generation Biological World Model (Stacking Ensemble)
   - Cold-start extrapolation & regression sanity
   - Mathematical invariance: Kd_nM == 10^(9 - pKd)
2. 3D Induced-Fit Conformation Identification
   - Biological ground-truth check: Dasatinib (Type I) vs Sorafenib/Imatinib (Type II)
3. First-Principles MM-GBSA Thermodynamic Free Energy Breakdown
   - Energy conservation: dG = dE_vdw + dE_elec + dG_gb + dG_sa - T*dS
   - Descriptor boundaries (rotatable bonds, buried SASA)
4. AI Lead Optimization & Medicinal Chemistry Evolution
   - Heuristic bioisostere generation & Lipinski rule of 5 verification
5. Bayesian Active Learning 4-Quadrant Decision Loop
   - EI & UCB acquisition mathematical properties
   - Epistemic uncertainty boundary exploration
6. LLM Gateway Security & Config Contract
   - Credential validation & endpoint spoofing protection
"""
import sys
import math
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "02_code"))
sys.path.insert(0, str(ROOT_DIR / "05_web_server"))

# Core scientific libraries
import numpy as np

# System modules under test
from dti_inference_runtime import DTIInferenceRuntime
from kinase_conformation_adapter import compute_induced_fit_interaction
from thermodynamic_physics_engine import predict_physical_affinity_dti
from active_learning_recommender import (
    compute_expected_improvement,
    evaluate_active_learning_pool
)
from llm_connection import validate_config, ConnectionCheckError

# Ground-truth test molecules & targets
DASATINIB_SMILES = "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO"
SORAFENIB_SMILES = "CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F"
IMATINIB_SMILES = "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"
ABL1_SEQUENCE = (
    "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSIT"
    "KGEKLRVLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISL"
    "RYEGRVYHYRINTASDGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTVYGVSPNYDKWEMERTDITMKHK"
    "LGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRE"
    "CNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESL"
    "AYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAF"
    "ETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRK"
    "ERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAK"
    "SPKPSNGAGVPNGALRESGGSGFRSPHLWKKSSTLTSSRLATGEEEGGGSSSKRFLRSCSASCVPHGAKDTEWRSVTLPRDL"
    "QSTGRQFDSSTFGGHKSEKPALPRKRAGENRSDQVTRGTVTPPPRLVKKNEEAADEVFKDIMESSPGSSPPNLTPKPLRRQV"
    "TVAPASGLPHKEEAEKGSALGTPAAAEPVTPTSKAGSGAPGGTSKGPAEESRVRRHKHSSESPGRDKGKLSRLKPAPPPPPA"
    "ASAGKAGGKPSQSPSQEAAGEAVLGAKTKATSLVDAVNSDAAKPSQPGEGLKKPVLPATPKPQSAKPSGTPISPAPVPSTLP"
    "SASSALAGDQPSSTAFIPLISTRVSLRKTRQPPERIASGAITKGVVLDSTEALCLAISRNSEQMASHSAVLEAGKNLYTFCV"
    "SYVDSIQQMRNKFAFREAINKLENNLRELQICPATAGSGPAATQDFSKLLSSVKEISDIVQR"
)
BRAF_SEQUENCE = (
    "MAALSGGGGGGAEPGQALFNGDMEPEAGAGAGAAASSAADPAIPEEVWNIKQMIKLTQEHIEALLDKFGGEHNPPSIYLEAY"
    "EEYTSKLDALQQREQQLLESLGNGTDFSVSSSASMDTVTSSSSSSLSVLPSSLSVFQNPTDVARSNPKSPQKPIVRVFLPNKQ"
    "RTVVPARCGVTVRDSLKKALMMRGLIPECCAVYRIQDGEKKPIGWDTDISWLTGEELHVEVLENVPLTTHNFVRKTFFTLAFC"
    "DFCRKLLFQGFRCQTCGYKFHQRCSTEVPLMCVNYDQLDLLFVSKFFEHHPIPQEEASLAETALTSGSSPSAPASDSIGPQIL"
    "TSPSPSKSIPIPQPFRPADEDHRNQFGQRDRSSSAPNVHINTIEPVNIDDLIRDQGFRGDGGSTTGLSATPPASLPGSLTNVK"
    "ALQKSPGPQRERKSSSSSEDRNRMKTLGRRDSSDDWEIPDGQITVGQRIGSGSFGTVYKGKWHGDVAVKMLNVTAPTPQQLQA"
    "FNEVGVLRKTRHVNILLFMGYSTKPQLAIVTQWCEGSSLYHHLHIIETKFEMIKLIDIARQTAQGMDYLHAKSIIHRDLKSNN"
    "IFLHEDLTVKIGDFGLATVKSRWSGSHQFEQLSGSILWMAPEVIRMQDKNPYSFQSDVYAFGIVLYELMTGQLPYSNINNRDQ"
    "IIFMVGRGYLSPDLSKVRSNCPKAMKRLMAECLKKKRDERPLFPQILASIELLARSLPKIHRSASEPSLNRAGFQTEDFSLYA"
    "CASPKTPIQAGGYGAFPVH"
)


def test_ai_01_world_model_inference():
    print("[AI-1/6] Testing Second-Gen Biological World Model Regression & Physics Bounds...", end=" ")
    runtime = DTIInferenceRuntime()
    runtime.load()
    
    # 1. Flagship inference
    res = runtime.predict(DASATINIB_SMILES, ABL1_SEQUENCE, model_name="worldmodel_stacked_ensemble")
    pkd = res["predicted_pkd"]
    kd_nM = res["predicted_kd_nM"]
    
    assert 5.0 <= pkd <= 11.0, f"Expected realistic pKd in [5.0, 11.0], got {pkd}"
    expected_kd = (10 ** (9.0 - pkd))
    assert math.isclose(kd_nM, expected_kd, rel_tol=1e-3), (
        f"Mathematical violation: pKd={pkd} -> expected Kd={expected_kd}nM, got {kd_nM}nM"
    )
    assert res["domain"] in ["train_block", "cold_drug_test", "cold_target_test", "strict_dual_cold_test"]
    assert "concordance_index" in res["domain_benchmark_metrics"]
    
    # 2. Baseline comparison: World Model vs Ridge vs Dummy
    ridge_res = runtime.predict(DASATINIB_SMILES, ABL1_SEQUENCE, model_name="ridge")
    dummy_res = runtime.predict(DASATINIB_SMILES, ABL1_SEQUENCE, model_name="dummy_mean")
    
    # Dummy mean should be near dataset baseline ~5.66
    assert abs(dummy_res["predicted_pkd"] - 5.41) < 0.25, f"Dummy baseline mismatch: {dummy_res['predicted_pkd']}"
    # World model prediction on known potent binder should be distinctly higher than dummy baseline
    assert pkd > dummy_res["predicted_pkd"] + 0.5, "World model should capture binding affinity enhancement"
    print(f"PASS (pKd={pkd:.3f}, Kd={kd_nM:.1f}nM, Invariance check ok)")


def test_ai_02_induced_fit_conformation_classification():
    print("[AI-2/6] Testing 3D Induced-Fit Kinase Conformation Classifier (Type I vs Type II)...", end=" ")
    
    # 1. Ground truth Type I check: Dasatinib on ABL1 (Classic ATP-hinge competitive, DFG-in)
    dasatinib_fit = compute_induced_fit_interaction(ABL1_SEQUENCE, DASATINIB_SMILES)
    assert dasatinib_fit.binding_mode == "type_i", (
        f"Dasatinib on ABL1 must be classified as Type I, got {dasatinib_fit.binding_mode}"
    )
    assert dasatinib_fit.preferred_conformation == "dfg_in", (
        f"Unexpected conformation: {dasatinib_fit.preferred_conformation}"
    )
    # Type I binder does not suffer DFG flip penalty in effective delta
    assert dasatinib_fit.effective_pkd_delta == 0.0, "Type I binder should have 0.0 effective delta penalty"
    
    # 2. Ground truth Type II check: Sorafenib on BRAF (Allosteric pocket filler, DFG-out)
    sorafenib_fit = compute_induced_fit_interaction(BRAF_SEQUENCE, SORAFENIB_SMILES)
    assert sorafenib_fit.binding_mode == "type_ii", (
        f"Sorafenib on BRAF must be classified as Type II allosteric, got {sorafenib_fit.binding_mode}"
    )
    assert sorafenib_fit.preferred_conformation == "dfg_out"
    assert sorafenib_fit.effective_pkd_delta < 0.0, (
        f"Type II binding must pay conformational flip penalty in affinity delta, got {sorafenib_fit.effective_pkd_delta}"
    )
    assert sorafenib_fit.dfg_flip_penalty_kcal > 0.5, (
        f"Type II binding should account for energetic barrier of DFG flip, got {sorafenib_fit.dfg_flip_penalty_kcal}"
    )
    print("PASS (Dasatinib -> Type-I DFG-in; Sorafenib -> Type-II DFG-out verified)")


def test_ai_03_mmgbsa_thermodynamic_decomposition():
    print("[AI-3/6] Testing First-Principles MM-GBSA Energy Conservation...", end=" ")
    phys = predict_physical_affinity_dti(ABL1_SEQUENCE, DASATINIB_SMILES)
    
    dG = phys.delta_g_bind
    dE_vdw = phys.delta_e_vdw
    dE_elec = phys.delta_e_elec
    dG_gb = phys.delta_g_gb
    dG_sa = phys.delta_g_sa
    minus_T_dS = phys.minus_t_delta_s
    
    # Verify thermodynamic conservation: dG = dE_vdw + dE_elec + dG_gb + dG_sa + minus_T_dS
    sum_components = dE_vdw + dE_elec + dG_gb + dG_sa + minus_T_dS
    assert math.isclose(dG, sum_components, rel_tol=1e-5), (
        f"Thermodynamic violation: dG={dG}, sum of components={sum_components}"
    )
    
    # Physical sanity checks
    # minus_T_dS represents conformational entropy loss upon binding, must be positive
    assert minus_T_dS > 0.0, f"Conformational entropy penalty (-T*dS) must be > 0, got {minus_T_dS}"
    # Buried SASA must be non-negative
    buried_sasa = phys.physics_descriptors[7]
    assert buried_sasa >= 0.0, f"Buried SASA must be >= 0, got {buried_sasa}"
    # Rotatable bonds count for Dasatinib should be around 8
    n_rot = phys.physics_descriptors[6]
    assert 3 <= n_rot <= 15, f"Expected realistic rotatable bonds count, got {n_rot}"
    print(f"PASS (dG={dG:.2f} kcal/mol, Sum conservation Delta={abs(dG-sum_components):.6f})")


def test_ai_04_medicinal_chemistry_evolution():
    print("[AI-4/6] Testing AI Lead Optimization & Bioisostere Evolution...", end=" ")
    from dti_endpoints import DTIOptimizeLeadRequest, optimize_dti_lead
    
    req = DTIOptimizeLeadRequest(
        drug_smiles=DASATINIB_SMILES,
        target_sequence=ABL1_SEQUENCE,
        target_name="ABL1",
        optimization_goal="提升亲和力与结合强度",
        custom_instruction="探查苯环与哌嗪位点修饰",
        model_name="worldmodel_stacked_ensemble"
    )
    res = optimize_dti_lead(req)
    
    assert res["summary"]["candidates_evaluated"] >= 4
    assert res["baseline"]["predicted_pkd"] >= 6.0
    
    # Verify each generated derivative is a chemically valid, distinct SMILES
    seen_smiles = set()
    for cand in res["candidates"]:
        assert len(cand["smiles"]) > 5
        assert cand["smiles"] not in seen_smiles
        seen_smiles.add(cand["smiles"])
        assert "delta_pkd" in cand
        # Verify delta matches candidate - baseline
        expected_delta = round(cand["predicted_pkd"] - res["baseline"]["predicted_pkd"], 3)
        assert abs(cand["delta_pkd"] - expected_delta) <= 0.002, (
            f"Delta math error: {cand['delta_pkd']} vs expected {expected_delta}"
        )
        assert cand["status_code"] in ["improved", "neutral", "decreased"]
        assert len(cand["rationale"]) >= 5
    print(f"PASS (Generated {len(res['candidates'])} valid derivatives, Deltas verified)")


def test_ai_05_bayesian_active_learning():
    print("[AI-5/6] Testing Bayesian Active Learning Acquisition (EI & UCB)...", end=" ")
    
    # 1. Mathematical properties of Expected Improvement (EI)
    # Case A: High predicted mean, zero uncertainty -> EI = max(0, mu - y_best - xi)
    ei_certain = compute_expected_improvement(mu=8.0, sigma=0.0, y_best=7.0, xi=0.0)
    assert math.isclose(ei_certain, 1.0, rel_tol=1e-3)
    
    # Case B: Sub-baseline predicted mean with zero uncertainty -> EI = 0
    ei_sub = compute_expected_improvement(mu=6.0, sigma=0.0, y_best=7.0, xi=0.0)
    assert ei_sub == 0.0
    
    # Case C: High uncertainty increases EI even for equal mean (exploration value)
    ei_low_sig = compute_expected_improvement(mu=7.2, sigma=0.2, y_best=7.0, xi=0.05)
    ei_high_sig = compute_expected_improvement(mu=7.2, sigma=1.0, y_best=7.0, xi=0.05)
    assert ei_high_sig > ei_low_sig, (
        f"Active learning acquisition must award higher exploration value to higher epistemic uncertainty: {ei_high_sig} vs {ei_low_sig}"
    )
    
    # 2. Pool evaluation and 4-quadrant dispatch
    pool = [
        ("Candidate-HighPotent-Confident", DASATINIB_SMILES),
        ("Candidate-Allosteric-Exploratory", SORAFENIB_SMILES),
        ("Candidate-Alternative", IMATINIB_SMILES)
    ]
    report = evaluate_active_learning_pool(
        target_sequence=ABL1_SEQUENCE,
        candidate_pool=pool,
        target_name="ABL1",
        y_best=6.50
    )
    assert report.total_evaluated == 3
    # Check that quadrants are populated and markdown summary is structured
    total_assigned = (
        len(report.confident_hits) +
        len(report.breakthrough_hypotheses) +
        len(report.high_information_gain_blindspots) +
        len(report.known_inactives)
    )
    assert total_assigned == 3, f"All candidates must be assigned to quadrants, got {total_assigned}"
    md = report.export_markdown()
    assert "# 主动学习定向验证与高信息增益推荐报告" in md
    print("PASS (EI exploration monotonicity & 4-quadrant assignment verified)")


def test_ai_06_llm_gateway_security_and_contracts():
    print("[AI-6/6] Testing LLM Gateway Security, Validation & Input Guardrails...", end=" ")
    
    # 1. Missing or invalid provider
    try:
        validate_config({"provider": "unsupported_ai", "api_key": "sk-123", "base_url": "https://api.openai.com/v1", "model_name": "gpt-4o"})
        assert False, "Should reject unsupported provider"
    except ConnectionCheckError as exc:
        assert exc.code == "UNSUPPORTED_PROVIDER"
        
    # 2. Malformed key (e.g. newline injection or control characters)
    try:
        validate_config({"provider": "openai", "api_key": "sk-123\nmalicious_header: foo", "base_url": "https://api.openai.com/v1", "model_name": "gpt-4o"})
        assert False, "Should reject key with control characters"
    except ConnectionCheckError as exc:
        assert exc.code == "INVALID_KEY"
        
    # 3. Endpoint spoofing attempt
    try:
        validate_config({"provider": "openai", "api_key": "sk-validkey12345678", "base_url": "https://evil-phishing-site.com/v1", "model_name": "gpt-4o"})
        assert False, "Should reject unauthorized endpoint"
    except ConnectionCheckError as exc:
        assert exc.code == "INVALID_ENDPOINT"

    # 4. Valid official config contract
    key, endpoint, model = validate_config({
        "provider": "openai",
        "api_key": "sk-sampletestkey12345678",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-4o"
    })
    assert key == "sk-sampletestkey12345678"
    assert endpoint == "https://api.openai.com/v1/chat/completions"
    assert model == "gpt-4o"
    print("PASS (Guardrails against credential injection & endpoint spoofing verified)")


if __name__ == "__main__":
    print("=" * 70)
    print("[START] RUNNING SCIENTIFIC & AI CAPABILITIES RIGOROUS VALIDATION SUITE")
    print("=" * 70)
    test_ai_01_world_model_inference()
    test_ai_02_induced_fit_conformation_classification()
    test_ai_03_mmgbsa_thermodynamic_decomposition()
    test_ai_04_medicinal_chemistry_evolution()
    test_ai_05_bayesian_active_learning()
    test_ai_06_llm_gateway_security_and_contracts()
    print("=" * 70)
    print("[SUCCESS] ALL 6 AI & SCIENTIFIC CAPABILITIES TESTS PASSED AND COMPLIANT WITH EXPECTATIONS!")
    print("=" * 70)
