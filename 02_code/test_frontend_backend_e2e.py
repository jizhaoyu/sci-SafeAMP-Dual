"""End-to-End Frontend-Backend Integration & Interoperability Test Suite.
Verifies all API endpoints consumed by React frontend:
- DTI status, drugs, targets, and models
- Single-point affinity prediction (classical & world models)
- Kinome panel selectivity profiling (16 representative kinases)
- 3D induced-fit geometry & MM-GBSA physical free energy breakdown
- Lead optimization molecular evolution & scoring
- Bayesian Active Learning 4-quadrant exploration/exploitation matrix
- Static frontend index.html delivery
"""
import sys
import time
from pathlib import Path

# Add project root and 05_web_server to sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "02_code"))
sys.path.insert(0, str(ROOT_DIR / "05_web_server"))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

DASATINIB_SMILES = "CC1=C(C(=CC=C1)Cl)NC(=O)C2=CN=C(S2)NC3=CC(=NC(=N3)C)N4CCN(CC4)CCO"
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


def test_01_static_index_page():
    print("[1/9] Testing Static Frontend Delivery (GET /)...", end=" ")
    t0 = time.time()
    res = client.get("/")
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "text/html" in res.headers.get("content-type", "")
    assert "<div id=\"root\"></div>" in res.text or "<script type=\"module\"" in res.text
    print(f"PASS ({elapsed:.1f}ms) - HTML shell returned")


def test_02_dti_status():
    print("[2/9] Testing DTI Runtime Status (GET /api/dti/status)...", end=" ")
    t0 = time.time()
    res = client.get("/api/dti/status")
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert data["status"] in ["ready", "operational"]
    assert data["num_drugs"] >= 68
    assert data["num_targets"] >= 379
    assert data["total_benchmark_pairs"] == 25772
    print(f"PASS ({elapsed:.1f}ms) - 68 drugs, 379 targets, 25,772 pairs verified")


def test_03_dti_drugs_and_targets():
    print("[3/9] Testing Drug & Target Metadata Catalog...", end=" ")
    t0 = time.time()
    res_drugs = client.get("/api/dti/drugs")
    res_targets = client.get("/api/dti/targets")
    elapsed = (time.time() - t0) * 1000
    assert res_drugs.status_code == 200
    assert res_targets.status_code == 200
    drugs = res_drugs.json()
    targets = res_targets.json()
    assert len(drugs) == 68, f"Expected 68 drugs, got {len(drugs)}"
    assert len(targets) == 379, f"Expected 379 targets, got {len(targets)}"
    assert "smiles" in drugs[0] and "name" in drugs[0]
    assert "sequence" in targets[0] and "length" in targets[0]
    print(f"PASS ({elapsed:.1f}ms) - Catalog structure fully compliant")


def test_04_dti_models():
    print("[4/9] Testing Registered DTI Models (GET /api/dti/models)...", end=" ")
    t0 = time.time()
    res = client.get("/api/dti/models")
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 5, f"Expected at least 5 models, got {len(models)}"
    model_ids = [m["id"] for m in models]
    assert "worldmodel_stacked_ensemble" in model_ids, "Missing flagship worldmodel_stacked_ensemble"
    assert "stacked_ensemble" in model_ids
    assert "ridge" in model_ids
    rec = next(m for m in models if m["id"] == "worldmodel_stacked_ensemble")
    assert rec["is_recommended"] is True
    assert rec["train_ci"] > 0.85
    assert rec["cold_target_ci"] > 0.70
    print(f"PASS ({elapsed:.1f}ms) - Flagship World Model validated (Train CI={rec['train_ci']}, ColdTarget CI={rec['cold_target_ci']})")


def test_05_dti_predict_affinity():
    print("[5/9] Testing Single-Point Affinity Prediction (POST /api/dti/predict)...", end=" ")
    t0 = time.time()
    payload = {
        "drug_smiles": DASATINIB_SMILES,
        "target_sequence": ABL1_SEQUENCE,
        "model_name": "worldmodel_stacked_ensemble"
    }
    res = client.post("/api/dti/predict", json=payload)
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "predicted_pkd" in data
    assert "predicted_kd_nM" in data
    assert "affinity_tier" in data
    assert data["predicted_pkd"] >= 6.0, f"Dasatinib to ABL1 predicted pKd: {data['predicted_pkd']}"
    assert data["predicted_kd_nM"] < 1000
    assert data["affinity_tier_code"] in ["high_affinity", "moderate_affinity"]
    assert "domain_benchmark_metrics" in data
    print(f"PASS ({elapsed:.1f}ms) - pKd={data['predicted_pkd']:.3f}, Kd={data['predicted_kd_nM']:.1f}nM")


def test_06_kinome_profiling():
    print("[6/9] Testing Kinome Selectivity Profiling (POST /api/dti/profile_panel)...", end=" ")
    t0 = time.time()
    payload = {
        "drug_smiles": DASATINIB_SMILES,
        "model_name": "worldmodel_stacked_ensemble"
    }
    res = client.post("/api/dti/profile_panel", json=payload)
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    panel = res.json()
    assert len(panel) >= 12, f"Expected representative kinases >= 12, got {len(panel)}"
    kinase_names = [p["kinase_name"] for p in panel]
    print(f"PASS ({elapsed:.1f}ms) - {len(panel)} kinases evaluated across diversity panel")


def test_07_biophysics_insights():
    print("[7/9] Testing 3D Induced-Fit & MM-GBSA Insights (POST /api/dti/biophysics_insights)...", end=" ")
    t0 = time.time()
    payload = {
        "drug_smiles": DASATINIB_SMILES,
        "target_sequence": ABL1_SEQUENCE
    }
    res = client.post("/api/dti/biophysics_insights", json=payload)
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "binding_mode" in data
    assert "preferred_conformation" in data
    assert "mmgbsa" in data
    mmgbsa = data["mmgbsa"]
    assert isinstance(mmgbsa["delta_g_bind"], (int, float)), f"Expected float delta_g_bind, got {mmgbsa['delta_g_bind']}"
    assert -500.0 < mmgbsa["delta_g_bind"] < 500.0, f"Unreasonable delta_g_bind: {mmgbsa['delta_g_bind']}"
    assert "delta_e_vdw" in mmgbsa
    assert "delta_e_elec" in mmgbsa
    assert "minus_t_delta_s" in mmgbsa
    print(f"PASS ({elapsed:.1f}ms) - Mode={data['binding_mode']}, ΔG_bind={mmgbsa['delta_g_bind']:.2f} kcal/mol")


def test_08_lead_optimizer():
    print("[8/9] Testing AI Lead Optimization (POST /api/dti/optimize_lead)...", end=" ")
    t0 = time.time()
    payload = {
        "drug_smiles": DASATINIB_SMILES,
        "target_sequence": ABL1_SEQUENCE,
        "target_name": "ABL1",
        "optimization_goal": "提升亲和力与结合强度",
        "custom_instruction": "在苯环无阻碍位点探查卤素结合",
        "model_name": "worldmodel_stacked_ensemble"
    }
    res = client.post("/api/dti/optimize_lead", json=payload)
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "baseline" in data
    assert "candidates" in data
    assert len(data["candidates"]) >= 3
    cand0 = data["candidates"][0]
    assert "name" in cand0 and "smiles" in cand0
    assert "predicted_pkd" in cand0
    assert "delta_pkd" in cand0
    print(f"PASS ({elapsed:.1f}ms) - Generated {len(data['candidates'])} candidates, Best={data['summary']['best_candidate']}")


def test_09_active_learning():
    print("[9/9] Testing Bayesian Active Learning Matrix (POST /api/dti/active_learning)...", end=" ")
    t0 = time.time()
    payload = {
        "target_sequence": ABL1_SEQUENCE,
        "target_name": "ABL1",
        "candidates": [
            {"name": "Candidate-F-01", "smiles": DASATINIB_SMILES},
            {"name": "Candidate-CF3-02", "smiles": "CNC(=O)C1=NC=CC(=C1)OC2=CC=C(C=C2)NC(=O)NC3=CC(=C(C=C3)Cl)C(F)(F)F"},
            {"name": "Candidate-Sol-03", "smiles": "COC1=C(C=C2C(=C1)N=CN=C2NC3=CC(=C(C=C3)F)Cl)OCCCN4CCOCC4"}
        ],
        "y_best": 7.85
    }
    res = client.post("/api/dti/active_learning", json=payload)
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    report = res.json()
    assert "total_evaluated" in report
    assert report["total_evaluated"] == 3
    assert "confident_hits" in report
    assert "breakthrough_hypotheses" in report
    assert "high_information_gain_blindspots" in report
    assert "known_inactives" in report
    assert "markdown_summary" in report and len(report["markdown_summary"]) > 50
    print(f"PASS ({elapsed:.1f}ms) - 4-Quadrant acquisition report generated")


def test_10_spa_and_health_probes():
    print("[10/11] Testing System Health & SPA Deep-Link Routing...", end=" ")
    t0 = time.time()
    # 1. Health probe
    res_health = client.get("/api/health")
    assert res_health.status_code == 200, f"Expected 200 from /api/health, got {res_health.status_code}"
    health_data = res_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["checks"]["dti_runtime"] == "ready"

    # 2. SPA Deep-link /dti and /evolution
    res_dti_page = client.get("/dti")
    res_evo_page = client.get("/evolution")
    elapsed = (time.time() - t0) * 1000
    assert res_dti_page.status_code == 200
    assert res_evo_page.status_code == 200
    assert "<div id=\"root\"></div>" in res_dti_page.text or "<script type=\"module\"" in res_dti_page.text
    print(f"PASS ({elapsed:.1f}ms) - Health probe healthy & SPA deep-links fallthrough verified")


def test_11_helical_wheel_endpoint():
    print("[11/11] Testing Helical Wheel Endpoint (/api/helical_wheel)...", end=" ")
    t0 = time.time()
    res = client.post("/api/helical_wheel", json={"sequence": "KWKLFKKIEKVGQNIRDGIIKAGPAVAVVGQATQIAK"})
    elapsed = (time.time() - t0) * 1000
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    assert "residues" in data
    assert "mean_hydrophobicity" in data
    assert "hydrophobic_moment" in data
    print(f"PASS ({elapsed:.1f}ms) - Peptide wheel calculation verified (μH={data['hydrophobic_moment']:.3f})")


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Running Full Frontend-Backend Interoperability Test Suite (11 Tests)")
    print("=" * 70)
    t_start = time.time()
    test_01_static_index_page()
    test_02_dti_status()
    test_03_dti_drugs_and_targets()
    test_04_dti_models()
    test_05_dti_predict_affinity()
    test_06_kinome_profiling()
    test_07_biophysics_insights()
    test_08_lead_optimizer()
    test_09_active_learning()
    test_10_spa_and_health_probes()
    test_11_helical_wheel_endpoint()
    total_elapsed = time.time() - t_start
    print("=" * 70)
    print(f"✅ ALL 11 FRONTEND-BACKEND INTEROPERABILITY TESTS PASSED in {total_elapsed:.2f}s!")
    print("=" * 70)
