"""Test integration of Tobit-Ranking DTI model into inference runtime and endpoints."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure 02_code is on path
CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from dti_inference_runtime import DTIInferenceRuntime


def test_tobit_ranking_model_registered():
    rt = DTIInferenceRuntime()
    rt.load()

    assert "tobit_ranking_model" in rt.models, "tobit_ranking_model must be registered in runtime"
    assert "tobit_ranking_model" not in rt.model_registration_errors, (
        f"Registration error for tobit_ranking_model: {rt.model_registration_errors.get('tobit_ranking_model')}"
    )


def test_tobit_ranking_inference_dasatinib_abl1():
    rt = DTIInferenceRuntime()
    rt.load()

    # Dasatinib SMILES & ABL1 kinase sequence snippet
    dasatinib_smiles = "CC1=C(C(=O)NC2=CC(=C(C=C2)S(=O)(=O)N)Cl)C=C(C=C1)NC3=NC=NC(=C3)N4CCN(CC4)CCO"
    # Canonical human ABL1 catalytic kinase sequence
    abl1_seq = (
        "MLEICLKLVGCKSKKGLSSSSSCYLEEALQRPVASDFEPQGLSEAARWNSKENLLAGPSENDPNLFVALYDFVASGDNTLSITKGEKLR"
        "VLGYNHNGEWCEAQTKNGQGWVPSNYITPVNSLEKHSWYHGPVSRNAAEYLLSSGINGSFLVRESESSPGQRSISLRYEGRVYHYRINTAS"
        "DGKLYVSSESRFNTLAELVHHHSTVADGLITTLHYPAPKRNKPTVYGVSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVK"
        "TLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHR"
        "DLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLE"
        "KDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRD"
        "TTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAG"
    )

    res = rt.predict(dasatinib_smiles, abl1_seq, model_name="tobit_ranking_model")

    assert res["model_used"] == "tobit_ranking_model"
    assert "predicted_pkd" in res
    assert "predicted_kd_nM" in res
    assert "affinity_tier" in res
    assert "domain" in res

    # Ensure unconstrained physically plausible output
    assert 4.0 <= res["predicted_pkd"] <= 12.0
    print(f"\n[Dasatinib + ABL1 under Tobit-Ranking]: pKd = {res['predicted_pkd']:.3f}, Kd = {res['predicted_kd_nM']:.2f} nM ({res['affinity_tier']})")


def test_tobit_ranking_kinome_panel():
    rt = DTIInferenceRuntime()
    rt.load()

    dasatinib_smiles = "CC1=C(C(=O)NC2=CC(=C(C=C2)S(=O)(=O)N)Cl)C=C(C=C1)NC3=NC=NC(=C3)N4CCN(CC4)CCO"
    panel_res = rt.profile_kinase_panel(dasatinib_smiles, model_name="tobit_ranking_model")

    assert len(panel_res) == 14, f"Expected 14 matched panel kinases, got {len(panel_res)}"
    for item in panel_res:
        assert item["predicted_pkd"] > 0
        assert item["predicted_kd_nM"] > 0
    # Verify sorted descending by pKd
    for i in range(len(panel_res) - 1):
        assert panel_res[i]["predicted_pkd"] >= panel_res[i + 1]["predicted_pkd"]
