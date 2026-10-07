"""Tests for DTI lead optimizer parameter alignment, fallback mechanisms, and candidate generation."""
import pytest
from dti_inference_runtime import DTIInferenceRuntime
from dti_lead_optimizer import DTILeadOptimizer, generate_heuristic_candidates


@pytest.fixture(scope="module")
def runtime():
    r = DTIInferenceRuntime()
    r.load()
    return r


def test_heuristic_candidates_generation():
    # Imatinib-like SMILES
    smiles = "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc4nccc(n4)c5cccnc5"
    candidates = generate_heuristic_candidates(smiles)
    assert len(candidates) >= 2
    for c in candidates:
        assert "name" in c
        assert "smiles" in c
        assert "modification_type" in c
        assert c["smiles"] != smiles


def test_lead_optimizer_heuristic_execution(runtime):
    optimizer = DTILeadOptimizer(runtime)
    drug_smiles = "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc4nccc(n4)c5cccnc5"
    # ABL1 sequence snippet
    target_seq = "MDPSSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGSGFRSPHLWKKSSTLTSSRLATGEEEGGGSSSKRFLRSCSASCVPHGAKDTEWRSVTLPRDLQSTGRQFDSSTFGGHKSEKPALPRKRAGENRSDQVTRGTVTPPPRLVKKNEEAADEVFKDIMESSPGSSPPNLTPKPLRRQVTVAPASGLPHKEEAWKGSALGTPAAAEPVTPTSKAGSGAPGGTSKGPAEESRVRRHKHSSESPGRDKGKLSRLKPAPPPPPAASAGKAGGKPSQSPSQEAAGEAVLGAKTKATSLVDAVNSDAAKPSQPAEGLKKPVLPATPKPQSAKPSGTPISPAPVPSTLPSASSALAGDQPSSTAFIPLISTRVSLRKTRQPPERIASGAITKGVVLDSTEALCLAISRNSEQMASHSAVLEAGKNLYTFCVSYVDSIQQMRNKFAFREAINKLENNLRELQICPATAGSGPAATQDFSKLLSSVKEISDIVQR"
    
    result = optimizer.optimize(
        drug_smiles=drug_smiles,
        target_sequence=target_seq,
        target_name="ABL1",
        optimization_goal="提升亲和力",
        model_name="stacked_ensemble",
        llm_config=None
    )
    assert result["mode"] == "heuristic_medchem_rules"
    assert result["fallback_reason"] is None
    assert result["summary"]["candidates_evaluated"] >= 2
    assert "baseline" in result
    assert "predicted_pkd" in result["baseline"]


def test_lead_optimizer_fallback_on_invalid_llm(runtime):
    optimizer = DTILeadOptimizer(runtime)
    drug_smiles = "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc4nccc(n4)c5cccnc5"
    target_seq = "MDPSSPNYDKWEMERTDITMKHKLGGGQYGEVYEGVWKKYSLTVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVVLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNKFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGSGFRSPHLWKKSSTLTSSRLATGEEEGGGSSSKRFLRSCSASCVPHGAKDTEWRSVTLPRDLQSTGRQFDSSTFGGHKSEKPALPRKRAGENRSDQVTRGTVTPPPRLVKKNEEAADEVFKDIMESSPGSSPPNLTPKPLRRQVTVAPASGLPHKEEAWKGSALGTPAAAEPVTPTSKAGSGAPGGTSKGPAEESRVRRHKHSSESPGRDKGKLSRLKPAPPPPPAASAGKAGGKPSQSPSQEAAGEAVLGAKTKATSLVDAVNSDAAKPSQPAEGLKKPVLPATPKPQSAKPSGTPISPAPVPSTLPSASSALAGDQPSSTAFIPLISTRVSLRKTRQPPERIASGAITKGVVLDSTEALCLAISRNSEQMASHSAVLEAGKNLYTFCVSYVDSIQQMRNKFAFREAINKLENNLRELQICPATAGSGPAATQDFSKLLSSVKEISDIVQR"

    # Provide custom api_base and model that will fail network connection
    bad_config = {
        "provider": "deepseek",
        "api_key": "sk-invalid-test-key-12345",
        "api_base": "https://127.0.0.1:54321/v1",
        "model": "deepseek-chat"
    }

    result = optimizer.optimize(
        drug_smiles=drug_smiles,
        target_sequence=target_seq,
        target_name="ABL1",
        optimization_goal="提升亲和力",
        model_name="stacked_ensemble",
        llm_config=bad_config
    )
    assert result["mode"] == "heuristic_fallback"
    assert result["fallback_reason"] is not None
    assert "大模型接口调用异常" in result["fallback_reason"]
    assert len(result["candidates"]) >= 2
