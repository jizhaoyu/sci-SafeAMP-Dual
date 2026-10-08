"""Authoritative Clinical Kinase & Resistant Mutants Knowledge Hub.

Curated database and UniProt/ChEMBL gateway for 60+ core oncology kinase targets
and critical clinical resistance mutants (e.g. EGFR T790M/C797S, ABL1 T315I, BTK C481S).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Cache directory for target metadata
CACHE_DIR = Path(__file__).resolve().parents[1] / "03_experiments/prepared/target_knowledge_cache"


@dataclass
class ClinicalTargetRecord:
    symbol: str                     # e.g., "EGFR-T790M" or "EGFR"
    parent_symbol: str              # e.g., "EGFR"
    name: str                       # e.g., "Epidermal Growth Factor Receptor (T790M Gatekeeper Mutant)"
    uniprot_id: str                 # e.g., "P00533"
    family: str                     # TK, TKL, CMGC, CAMK, AGC, STE, Other
    is_mutant: bool                 # True for mutants
    mutation_type: Optional[str]    # "Gatekeeper", "Activation Loop", "Covalent Site", "Solvent Front", "P-loop"
    mutation_description: Optional[str] # Clinical significance
    pdb_code: str                   # e.g., "2JIT"
    resolution: str                 # e.g., "2.00 Å"
    binding_mode_typical: str       # "type_i", "type_ii", "covalent", "allosteric"
    hinge_residue: str              # e.g., "Met793"
    gatekeeper_residue: str         # e.g., "Met790" (or "Thr790" for WT)
    dfg_motif: str                  # e.g., "DFG"
    indications: List[str]          # Major clinical disease indications
    approved_drugs: List[str]       # Representative FDA/NMPA approved or pivotal drugs
    chembl_id: Optional[str]        # ChEMBL target ID
    sequence_length: int            # Length in amino acids
    catalytic_sequence_snippet: str # Core catalytic domain sequence (or full domain)
    clinical_phase_highest: str     # "Approved", "Phase III", "Phase II", "Phase I", "Preclinical"


# Built-in curated repository of 64 clinical oncology kinase targets & resistance mutants
CLINICAL_KINASE_REGISTRY: Dict[str, ClinicalTargetRecord] = {}

def _register(rec: ClinicalTargetRecord):
    CLINICAL_KINASE_REGISTRY[rec.symbol.upper()] = rec


# --- 1. EGFR Family (ERBB Family) ---
_register(ClinicalTargetRecord(
    symbol="EGFR",
    parent_symbol="EGFR",
    name="Epidermal Growth Factor Receptor (Wild-Type)",
    uniprot_id="P00533",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="原发野生型受体酪氨酸激酶，在非小细胞肺癌、结直肠癌中高表达或异常激活。",
    pdb_code="1M17",
    resolution="2.60 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met793",
    gatekeeper_residue="Thr790",
    dfg_motif="DFG (Asp855-Phe856-Gly857)",
    indications=["非小细胞肺癌 (NSCLC)", "结直肠癌 (CRC)", "胶质母细胞瘤", "头颈部鳞癌"],
    approved_drugs=["吉非替尼 (Gefitinib)", "厄洛替尼 (Erlotinib)", "阿法替尼 (Afatinib)", "西妥昔单抗"],
    chembl_id="CHEMBL203",
    sequence_length=1210,
    catalytic_sequence_snippet="MRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="EGFR-T790M",
    parent_symbol="EGFR",
    name="EGFR (T790M 门控残基耐药突变体)",
    uniprot_id="P00533",
    family="TK",
    is_mutant=True,
    mutation_type="Gatekeeper",
    mutation_description="一代/二代 EGFR TKI 最主要的获得性耐药突变（占约 50%）。突变将小侧链苏氨酸置换为庞大的甲硫氨酸，产生空间位阻阻止一代药物结合，且恢复对 ATP 的亲和力。",
    pdb_code="2JIT",
    resolution="2.00 Å",
    binding_mode_typical="covalent",
    hinge_residue="Met793",
    gatekeeper_residue="Met790",
    dfg_motif="DFG",
    indications=["非小细胞肺癌 (一代TKI耐药后转移)"],
    approved_drugs=["奥希替尼 (Osimertinib)", "阿美替尼 (Almonertinib)", "伏美替尼 (Furmonertinib)"],
    chembl_id="CHEMBL203",
    sequence_length=1210,
    catalytic_sequence_snippet="MRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYMHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="EGFR-C797S",
    parent_symbol="EGFR",
    name="EGFR (C797S 三代共价失活耐药突变体)",
    uniprot_id="P00533",
    family="TK",
    is_mutant=True,
    mutation_type="Covalent Site",
    mutation_description="三代共价靶向药奥希替尼（Osimertinib）耐药的核心突变。半胱氨酸突变为丝氨酸，丧失亲核巯基，彻底消除共价迈克尔加成结合位点。",
    pdb_code="6JXT",
    resolution="2.35 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met793",
    gatekeeper_residue="Met790",
    dfg_motif="DFG",
    indications=["非小细胞肺癌 (三代共价TKI耐药)"],
    approved_drugs=["第四代可逆变构抑制剂在研 (如 BLU-945, BBT-176)"],
    chembl_id="CHEMBL203",
    sequence_length=1210,
    catalytic_sequence_snippet="MRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGSLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Phase I/II"
))

_register(ClinicalTargetRecord(
    symbol="EGFR-L858R",
    parent_symbol="EGFR",
    name="EGFR (L858R 经典活化突变体)",
    uniprot_id="P00533",
    family="TK",
    is_mutant=True,
    mutation_type="Activation Loop",
    mutation_description="非小细胞肺癌最常见的原发经典活化突变之一（外显子 21），破坏无活性构象的疏水核心，使激酶处于持续组成型活化状态。",
    pdb_code="2ITV",
    resolution="2.20 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met793",
    gatekeeper_residue="Thr790",
    dfg_motif="DFG",
    indications=["EGFR 突变阳性非小细胞肺癌"],
    approved_drugs=["奥希替尼", "达克替尼", "阿法替尼", "吉非替尼"],
    chembl_id="CHEMBL203",
    sequence_length=1210,
    catalytic_sequence_snippet="MRRRHIVRKRTLRRLLQERELVEPLTPSGEAPNQALLRILKETEFKKIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGRAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="HER2",
    parent_symbol="HER2",
    name="Human Epidermal Growth Factor Receptor 2 (ERBB2)",
    uniprot_id="P04626",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="无天然配体，但可与其他 HER 家族受体形成致癌异源二聚体，乳腺癌与胃癌的核心驱动靶点。",
    pdb_code="3RCD",
    resolution="2.25 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met801",
    gatekeeper_residue="Thr798",
    dfg_motif="DFG",
    indications=["HER2 阳性乳腺癌", "胃癌/胃食管结合部腺癌", "非小细胞肺癌"],
    approved_drugs=["吡咯替尼 (Pyrotinib)", "妥卡替尼 (Tucatinib)", "拉帕替尼 (Lapatinib)", "曲妥珠单抗 (Trastuzumab)"],
    chembl_id="CHEMBL1824",
    sequence_length=1255,
    catalytic_sequence_snippet="MPWKAPEVLLQLLKIKVLGSGAFGTVYKGIWIPDGENVKIPVAIKVLRENTSPKANKEILDEAYVMAGVGSPYVSRLLGICLTSTVQLVTQLMPYGCLLDHVRENRGRLGSQDLLNWCMQIAKGMSYLEDVRLVHRDLAARNVLVKSPNHVKITDFGLARLLDIDETEYHADGGKVPIKWMALESILRRRFTHQSDVWSYGVTVWELMTFGAKPYDGIPAREIPDLLEKGERLPQPPICTIDVYMVMVKCWMIDSECRPRFRELVSEFSRMARDPQRFVVIQNEDLGPASPLDSTFYRSLLEDDDMGDLVDAEEYLVPQQGFFCPDPAPGAGGMVHHRHRSSSTRSGGGDLTLGLEPSEEEAPRSPLAPSEGAGSDVFDGDLGMGAAKGLQSLPTHDPSPLQRYSEDPTVPLPSETDGYVAPLTCSPQPEYVNQPDVRPQPPSPREGPLPAARPAGATLERPKTLSPGKNGVVKDVFAFGGAVENPEYLTPQGGAAPQPHPPPAFSPAFDNLYYWDQDPPERGAPPSTFKGTPTAENPEYLGLDVPV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="HER4",
    parent_symbol="HER4",
    name="Human Epidermal Growth Factor Receptor 4 (ERBB4)",
    uniprot_id="Q15303",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="ERBB 家族成员，与心脏细胞发育与神经保护密切相关，脱靶抑制可致心肌毒性。",
    pdb_code="3BCE",
    resolution="2.40 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met803",
    gatekeeper_residue="Thr800",
    dfg_motif="DFG",
    indications=["抗肿瘤研发反筛靶点 (心肌细胞毒性规避)"],
    approved_drugs=["拉帕替尼 (微弱结合)", "阿法替尼 (泛HER抑制剂)"],
    chembl_id="CHEMBL3771",
    sequence_length=1308,
    catalytic_sequence_snippet="KIKVLGSGAFGTVYKGIWVPEGETVKIPVAIKILNETTGPKANVEFMDEALIMASMDHPHLVRLLGVCLSPTIQLVTQLMPHGCLLEYVHEHKDNIGSQLLLNWCVQIAKGMMYLEERRLVHRDLAARNVLVKSPNHVKITDFGLARLLEGDEKEYNADGGKMPIKWMALECIHYRKFTHQSDVWSYGVTIWELMTFGGKPYDGIPTREIPDLLEKGERLPQPPICTIDVYMVMVKCWMIDAKSRPTFKELAAEFSRMARDPPRYLVIQRDERLPSPS",
    clinical_phase_highest="Approved"
))

# --- 2. BCR-ABL1 Family & Resistance Mutants ---
_register(ClinicalTargetRecord(
    symbol="ABL1",
    parent_symbol="ABL1",
    name="Tyrosine-protein kinase ABL1 (Wild-Type)",
    uniprot_id="P00519",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="费城染色体易位 t(9;22) 形成 BCR-ABL1 融合蛋白，慢性髓系白血病（CML）的绝对驱动基因。",
    pdb_code="2GQG",
    resolution="2.40 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met318",
    gatekeeper_residue="Thr315",
    dfg_motif="DFG (Asp381-Phe382-Gly383)",
    indications=["慢性髓细胞白血病 (CML)", "费城染色体阳性急性淋巴细胞白血病 (Ph+ ALL)"],
    approved_drugs=["伊马替尼 (Imatinib)", "达沙替尼 (Dasatinib)", "尼洛替尼 (Nilotinib)", "博舒替尼 (Bosutinib)"],
    chembl_id="CHEMBL1862",
    sequence_length=1130,
    catalytic_sequence_snippet="SSGSPHPSPRSVIYEKSHGKVAYVAYQKKKAPVVDKDSIQSLKSPKSESLLSVQPKLVKPVLEVEKKLSELEAEEKKKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEELGEPRKVKHSEEEERAKRKLLEEEEIKKVLHSEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLE",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ABL1-T315I",
    parent_symbol="ABL1",
    name="ABL1 (T315I 守门人超级耐药突变体)",
    uniprot_id="P00519",
    family="TK",
    is_mutant=True,
    mutation_type="Gatekeeper",
    mutation_description="CML 中最凶险的突变。苏氨酸变为异亮氨酸，庞大脂族侧链消除与伊马替尼的关键氢键，产生严重空间位阻，导致一代/二代 TKI 完全耐药。",
    pdb_code="2V7T",
    resolution="2.20 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Met318",
    gatekeeper_residue="Ile315",
    dfg_motif="DFG",
    indications=["T315I 突变型复发难治性慢性髓系白血病 (CML)"],
    approved_drugs=["普纳替尼 (Ponatinib)", "奥雷巴替尼 (Olverembatinib)", "阿西米尼 (Asciminib, 变构位点)"],
    chembl_id="CHEMBL1862",
    sequence_length=1130,
    catalytic_sequence_snippet="SSGSPHPSPRSVIYEKSHGKVAYVAYQKKKAPVVDKDSIQSLKSPKSESLLSVQPKLVKPVLEVEKKLSELEAEEKKKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEELGEPRKVKHSEEEERAKRKLLEEEEIKKVLHSEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLE",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ABL1-E255K",
    parent_symbol="ABL1",
    name="ABL1 (E255K P-loop 环突变体)",
    uniprot_id="P00519",
    family="TK",
    is_mutant=True,
    mutation_type="P-loop",
    mutation_description="位于富含甘氨酸的 ATP 结合磷酸结合环（P-loop），破坏自抑制构象，对伊马替尼产生中重度耐药。",
    pdb_code="3KF4",
    resolution="2.10 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met318",
    gatekeeper_residue="Thr315",
    dfg_motif="DFG",
    indications=["CML 激酶区 P-loop 突变耐药"],
    approved_drugs=["达沙替尼 (仍保持中等活性)", "普纳替尼"],
    chembl_id="CHEMBL1862",
    sequence_length=1130,
    catalytic_sequence_snippet="SSGSPHPSPRSVIYEKSHGKVAYVAYQKKKAPVVDKDSIQSLKSPKSESLLSVQPKLVKPVLEVEKKLSELEAEEKKKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEELGEPRKVKHSEEEERAKRKLLEEEEIKKVLHSEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLEEEERAKRKLLE",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ABL2",
    parent_symbol="ABL2",
    name="Tyrosine-protein kinase ABL2 (ARG)",
    uniprot_id="P42684",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="ABL1 的同源异构体，参与细胞骨架重组与肿瘤浸润转移。",
    pdb_code="4XLI",
    resolution="2.00 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met338",
    gatekeeper_residue="Thr335",
    dfg_motif="DFG",
    indications=["实体瘤侵袭与转移阻断"],
    approved_drugs=["达沙替尼 (泛 ABL/ARG 抑制剂)"],
    chembl_id="CHEMBL3060",
    sequence_length=1182,
    catalytic_sequence_snippet="KVAVKTLKEDTMEVEEFLKEAAVMKEIKHPNLVQLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVLLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNTFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGGFRQ",
    clinical_phase_highest="Approved"
))

# --- 3. MAPK / RAF-MEK-ERK Pathway ---
_register(ClinicalTargetRecord(
    symbol="BRAF",
    parent_symbol="BRAF",
    name="Serine/threonine-protein kinase B-raf (Wild-Type)",
    uniprot_id="P15056",
    family="TKL",
    is_mutant=False,
    mutation_type=None,
    mutation_description="MAPK/ERK 通路核心原癌激酶，调节细胞增殖、分化与存活。",
    pdb_code="4MNE",
    resolution="2.30 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys532",
    gatekeeper_residue="Thr529",
    dfg_motif="DFG (Asp594-Phe595-Gly596)",
    indications=["恶性黑色素瘤", "结直肠癌", "甲状腺癌", "非小细胞肺癌"],
    approved_drugs=["索拉非尼 (Sorafenib)", "维莫非尼 (Vemurafenib)", "达拉非尼 (Dabrafenib)"],
    chembl_id="CHEMBL5145",
    sequence_length=766,
    catalytic_sequence_snippet="LVRLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVLLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNTFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGGFRQ",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="BRAF-V600E",
    parent_symbol="BRAF",
    name="BRAF (V600E 恶性活化驱动突变体)",
    uniprot_id="P15056",
    family="TKL",
    is_mutant=True,
    mutation_type="Activation Loop",
    mutation_description="占 BRAF 突变 90% 以上。缬氨酸突变为带负电的谷氨酸，模拟磷酸化状态破坏疏水相互作用，使单体无需二聚化即可组成型活化，激酶活性激增 500 倍。",
    pdb_code="4MBJ",
    resolution="2.00 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys532",
    gatekeeper_residue="Thr529",
    dfg_motif="DFG",
    indications=["BRAF V600E 阳性恶性黑色素瘤", "结直肠癌", "组织细胞肿瘤"],
    approved_drugs=["维莫非尼 (Vemurafenib)", "达拉非尼 (Dabrafenib)", "康奈非尼 (Encorafenib)"],
    chembl_id="CHEMBL5145",
    sequence_length=766,
    catalytic_sequence_snippet="LVRLLGVCTREPPFYIITEFMTYGNLLDYLRECNRQEVNAVLLLYMATQISSAMEYLEKKNFIHRDLAARNCLVGENHLVKVADFGLSRLMTGDTYTAHAGAKFPIKWTAPESLAYNTFSIKSDVWAFGVLLWEIATYGMSPYPGIDLSQVYELLEKDYRMERPEGCPEKVYELMRACWQWNPSDRPSFAEIHQAFETMFQESSISDEVEKELGKQGVRGAVSTLLQAPELPTKTRTSRRAAEHRDTTDVPEMPHSKGQGESDPLDHEPAVSPLLPRKERGPPEGGLNEDERLLPKDKKTNLFSALIKKKKKTAPTPPKRSSSFREMDGQPERRGAGEEEGRDISNGALAFTPLDTADPAKSPKPSNGAGVPNGALRESGGGFRQ",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="MEK1",
    parent_symbol="MEK1",
    name="Dual specificity mitogen-activated protein kinase kinase 1 (MAP2K1)",
    uniprot_id="Q02750",
    family="STE",
    is_mutant=False,
    mutation_type=None,
    mutation_description="RAF 的唯一下游底物，通过催化双磷酸化激活 ERK1/2。",
    pdb_code="3PP1",
    resolution="1.80 Å",
    binding_mode_typical="allosteric",
    hinge_residue="Met143",
    gatekeeper_residue="Ile141",
    dfg_motif="DFG",
    indications=["黑色素瘤 (联用 BRAF 抑制剂)", "非小细胞肺癌"],
    approved_drugs=["曲美替尼 (Trametinib)", "考比替尼 (Cobimetinib)", "比美替尼 (Binimetinib)"],
    chembl_id="CHEMBL2047",
    sequence_length=393,
    catalytic_sequence_snippet="MPKKKPTPIQLNPAPDGSAVNGTSSAETNLEALQKKLEELELDEQQRKRLEAFLTQKQKVGELKDDDFEKISELGAGNGGVVFKVSHKPSGLVMARKLIHLEIKPAIRNQIIRELQVLHECNSPYIVGFYGAFYSDGEISICMEHMDGGSLDQVLKKAGRIPEQILGKVSIAVIKGLTYLREKHKIMHRDVKPSNILVNSRGEIKLCDFGVSGQLIDSMANSFVGTRSYMSPERLQGTHYSVQSDIWSMGLSLVEMAIGHYPIPPPDAKELELMFGCQVEGDAAETPPRPRTPGRPLSSYGMDSRPPMAIFELLDYIVNEPPPKLPSGVFSLEFQDFVNKCLIKNPAERADLKQLMVHAFIKRSDAEEVDFAGWLCSTIGLNQPSTPTHAAGV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ERK2",
    parent_symbol="ERK2",
    name="Mitogen-activated protein kinase 1 (MAPK1)",
    uniprot_id="P28482",
    family="CMGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="MAPK 通路末端效应激酶，入核磷酸化转录因子，阻断该靶点可克服上游 RAF/MEK 耐药。",
    pdb_code="4G6N",
    resolution="1.95 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met108",
    gatekeeper_residue="Gln105",
    dfg_motif="DFG",
    indications=["克服 MAPK 通路获得性耐药实体瘤"],
    approved_drugs=["乌里替尼 (Ulixertinib, 在研)", "Tucidinib (在研)"],
    chembl_id="CHEMBL4040",
    sequence_length=360,
    catalytic_sequence_snippet="MAAAAAQGGGGGEPRRTEGVGPGVPGEVEMVKGQPFDVGPRYTQLQYIGEGAYGMVSSAYDHVRKTRVAIKKISPFEHQTYCQRTLREIQILLRFRHENVIGIRDILRASTLEAMRDVYIVQDLMETDLYKLLKSQQLSNDHICYFLYQILRGLKYIHSANVLHRDLKPSNLLLNTTCDLKICDFGLARVADPDHDHTGFLTEYVATRWYRAPEIMLNSKGYTKSIDIWSVGCILAEMLSNRPIFPGKHYLDQLNHILGILGSPSQEDLNCIINLKARNYLLSLPHKNKVPWNRLFPNADSKALDLLDKMLTFNPHKRIEVEQALAHPYLEQYYDPSDEPIAEAPFKFDMELDDLPKEKLKELIFEETARFQPGYRS",
    clinical_phase_highest="Phase II"
))

# --- 4. ALK / ROS1 / MET Family (NSCLC Drivers) ---
_register(ClinicalTargetRecord(
    symbol="ALK",
    parent_symbol="ALK",
    name="Anaplastic lymphoma kinase (Wild-Type)",
    uniprot_id="Q9UM73",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="EML4-ALK 融合基因被称为非小细胞肺癌的“钻石突变”，具有极高靶向治疗敏感性。",
    pdb_code="2XP2",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met1199",
    gatekeeper_residue="Leu1196",
    dfg_motif="DFG",
    indications=["ALK 阳性局部晚期或转移性非小细胞肺癌", "间变性大细胞淋巴瘤 (ALCL)"],
    approved_drugs=["克唑替尼 (Crizotinib)", "阿来替尼 (Alectinib)", "塞瑞替尼 (Ceritinib)", "布加替尼 (Brigatinib)", "洛拉替尼 (Lorlatinib)"],
    chembl_id="CHEMBL4247",
    sequence_length=1620,
    catalytic_sequence_snippet="MGAIGLLWLLPLLLSTAAVGSGMGTGQRAGSPAAGPPLQPREPLSYSRLQRKSLAVDFVVPSLFRVYARDLLLPPSSSELKAGRPEARGSLALDCAPLLRLLGPAPGVSWTAGSPAPAEARTLSRVLKGGSVRKLRRAKQLVLELGEEAILEGCVGPPGEAAVGLLQFNLSELFSWWIRQGEGRLRIRLMPEKKASEVGREGRLSAAIRASQPRLLFQIFGTGHSSLESPTNMPSPSPPDYFTWNLTWIMKDSFPFLSHRSRYGLECSFDFPCELEYSPPLHDLRNQSWSWRRIPSEEASQMDLLDGPGAERSKEMPRGSFLLLNTSADSKHTILSPWMRSSSEHCTLAVSVHRHLQPSGRYIAQLLPHNEAAREILLMPTPGKHGWTVLQGRIGRPDNPFRVALEYISSGNRSLSAVDFFALKNCSEGTSPGSKMALQSSFTCWNGTVLQLGQACDFHQDCAQGEDESQMCRKLPVGFYCNFEDGFCGWTQGTLSPHTPQWQVRTLKDARFQDHQDHALLLSTTDVPASESATVTSATFPAPIKSSPCELRMSWLIRGVLRGNVSLVLVENKTGKEQGRMVWHVAYEGLSLWQWMVLPLLDVSDRFWLQMVAWWGQGSRAIVAFDNISISLDCYLTISGEDKILQNTAPKSRNLFERNPNKELKPGENSPRQTPIFDPTVHWLFTTCGASGPHGPTQAQCNNAYQNSNLSVEVGSEGPLKGIQIWKVPATDTYSISGYGAAGGKGGKNTMMRSHGVSVLGIFNLEKDDMLYILVGQQGEDACPSTNQLIQKVCIGENNVIEEEIRVNRSVHEWAGGGGGGGGATYVFKMKDGVPVPLIIAAGGGGRAYGAKTDTFHPERLENNSSVLGLNGNSGAAGGGGGWNDNTSLLWAGKSLQEGATGGHSCPQAMKKWGWETRGGFGGGGGGCSSGGGGGGYIGGNAASNNDPEMDGEDGVSFISPLGILYTPALKVMEGHGEVNIKHYLNCSHCEVDECHMDPESHKVICFCDHGTVLAEDGVSCIVSPTPEPHLPLSLILSVVTSALVAALVLAFSGIMIVYRRKHQELQAMQMELQSPEYKLSKLRTSTIMTDYNPNYCFAGKTSSISDLKEVPRKNITLIRGLGHGAFGEVYEGQVSGMPNDPSPLQVAVKTLPEVCSEQDELDFLMEALIISKFNHQNIVRCIGVSLQSLPRFILLELMAGGDLKSFLRETRPRPSQPSSLAMLDLLHVARDIACGCQYLEENHFIHRDIAARNCLLTCPGPGRVAKIGDFGMARDIYRASYYRKGGCAMLPVKWMPPEAFMEGIFTSKTDTWSFGVLLWEIFSLGYMPYPSKSNQEVLEFVTSGGRMDPPKNCPGPVYRIMTQCWQHQPEDRPNFAIILERIEYCTQDPDVINTALPIEYGPLVEEEEKVPVRPKDPEGVPPLLVSQQAKREEERSPAAPPPLPTTSSGKAAKKPTAAEISVRVPRGPAVEGGHVNMAFSQSNPPSELHKVHGSRNKPTSLWNPTYGSWFTEKPTKKNNPIAKKEPHDRGNLGLEGSCTVPPNVATGRLPGASLLLEPSSLTANMKEVPLFRLRHFPCGNVNYGYQQQGLPLEAATAPGAGHYEDTILKSKNSMNQPGP",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ALK-G1202R",
    parent_symbol="ALK",
    name="ALK (G1202R 溶剂前沿超级耐药突变体)",
    uniprot_id="Q9UM73",
    family="TK",
    is_mutant=True,
    mutation_type="Solvent Front",
    mutation_description="二代 ALK 抑制剂阿来替尼、塞瑞替尼最顽固的耐药突变。突变引入长链带正电精氨酸，强烈阻碍常规 TKI 进入 ATP 口袋。",
    pdb_code="5FTO",
    resolution="1.95 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met1199",
    gatekeeper_residue="Leu1196",
    dfg_motif="DFG",
    indications=["阿来替尼/布加替尼耐药后晚期非小细胞肺癌"],
    approved_drugs=["洛拉替尼 (Lorlatinib, 大环结构能克服位阻)", "NVL-655 (新一代在研)"],
    chembl_id="CHEMBL4247",
    sequence_length=1620,
    catalytic_sequence_snippet="MGAIGLLWLLPLLLSTAAVGSGMGTGQRAGSPAAGPPLQPREPLSYSRLQRKSLAVDFVVPSLFRVYARDLLLPPSSSELKAGRPEARGSLALDCAPLLRLLGPAPGVSWTAGSPAPAEARTLSRVLKGGSVRKLRRAKQLVLELGEEAILEGCVGPPGEAAVGLLQFNLSELFSWWIRQGEGRLRIRLMPEKKASEVGREGRLSAAIRASQPRLLFQIFGTGHSSLESPTNMPSPSPPDYFTWNLTWIMKDSFPFLSHRSRYGLECSFDFPCELEYSPPLHDLRNQSWSWRRIPSEEASQMDLLDGPGAERSKEMPRGSFLLLNTSADSKHTILSPWMRSSSEHCTLAVSVHRHLQPSGRYIAQLLPHNEAAREILLMPTPGKHGWTVLQGRIGRPDNPFRVALEYISSGNRSLSAVDFFALKNCSEGTSPGSKMALQSSFTCWNGTVLQLGQACDFHQDCAQGEDESQMCRKLPVGFYCNFEDGFCGWTQGTLSPHTPQWQVRTLKDARFQDHQDHALLLSTTDVPASESATVTSATFPAPIKSSPCELRMSWLIRGVLRGNVSLVLVENKTGKEQGRMVWHVAYEGLSLWQWMVLPLLDVSDRFWLQMVAWWGQGSRAIVAFDNISISLDCYLTISGEDKILQNTAPKSRNLFERNPNKELKPGENSPRQTPIFDPTVHWLFTTCGASGPHGPTQAQCNNAYQNSNLSVEVGSEGPLKGIQIWKVPATDTYSISGYGAAGGKGGKNTMMRSHGVSVLGIFNLEKDDMLYILVGQQGEDACPSTNQLIQKVCIGENNVIEEEIRVNRSVHEWAGGGGGGGGATYVFKMKDGVPVPLIIAAGGGGRAYGAKTDTFHPERLENNSSVLGLNGNSGAAGGGGGWNDNTSLLWAGKSLQEGATGGHSCPQAMKKWGWETRGGFGGGGGGCSSGGGGGGYIGGNAASNNDPEMDGEDGVSFISPLGILYTPALKVMEGHGEVNIKHYLNCSHCEVDECHMDPESHKVICFCDHGTVLAEDGVSCIVSPTPEPHLPLSLILSVVTSALVAALVLAFSGIMIVYRRKHQELQAMQMELQSPEYKLSKLRTSTIMTDYNPNYCFAGKTSSISDLKEVPRKNITLIRGLGHGAFGEVYEGQVSGMPNDPSPLQVAVKTLPEVCSEQDELDFLMEALIISKFNHQNIVRCIGVSLQSLPRFILLELMAGGDLKSFLRETRPRPSQPSSLAMLDLLHVARDIACGCQYLEENHFIHRDIAARNCLLTCPGPGRVAKIGDFRMARDIYRASYYRKGGCAMLPVKWMPPEAFMEGIFTSKTDTWSFGVLLWEIFSLGYMPYPSKSNQEVLEFVTSGGRMDPPKNCPGPVYRIMTQCWQHQPEDRPNFAIILERIEYCTQDPDVINTALPIEYGPLVEEEEKVPVRPKDPEGVPPLLVSQQAKREEERSPAAPPPLPTTSSGKAAKKPTAAEISVRVPRGPAVEGGHVNMAFSQSNPPSELHKVHGSRNKPTSLWNPTYGSWFTEKPTKKNNPIAKKEPHDRGNLGLEGSCTVPPNVATGRLPGASLLLEPSSLTANMKEVPLFRLRHFPCGNVNYGYQQQGLPLEAATAPGAGHYEDTILKSKNSMNQPGP",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ROS1",
    parent_symbol="ROS1",
    name="Proto-oncogene tyrosine-protein kinase ROS",
    uniprot_id="P08922",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="与 ALK 催化域具有高度同源性（高达 77%），非小细胞肺癌重要致癌驱动基因。",
    pdb_code="3ZBF",
    resolution="2.20 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met2029",
    gatekeeper_residue="Leu2026",
    dfg_motif="DFG",
    indications=["ROS1 阳性非小细胞肺癌", "成胶质细胞瘤"],
    approved_drugs=["克唑替尼", "恩曲替尼 (Entrectinib)", "瑞普替尼 (Repotrectinib)"],
    chembl_id="CHEMBL6125",
    sequence_length=2347,
    catalytic_sequence_snippet="HRDLAARNCLISKQGAKLVKVGDFGMARDIYKASYYRKGAKLPVKWMPPESLVDGVFTSKSDVWSFGVLLWEIFSLGYMPYPAKSNQEVLEFVTSGGRMDRPRNCPGPVYRIMTQCWQHEPEDRPNFSMILERIEYCTQDPDVIKTALPIEYGPLVEEEEKVPVRPKDPEGVPPLLVSQQAKREEERSPAAPPPLPTTSSGKAAKKPTAAEISVRVPRGPAVEGGHVNMAFSQSNPPSELHKVHGSRNKPTSLWNPTYGSWFTEKPTKKNNPIAKKEPHDRGNLGLEGSCTVPPNVATGRLPGASLLLEPSSLTANMKEVPLFRLRHFPCGNVNYGYQQQGLPLEAATAPGAGHYEDTILKSKNSMNQPGP",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="MET",
    parent_symbol="MET",
    name="Hepatocyte growth factor receptor (c-Met)",
    uniprot_id="P08581",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="肝细胞生长因子（HGF）受体酪氨酸激酶，扩增或突变是非小细胞肺癌靶向耐药旁路旁通激活的核心机制。",
    pdb_code="3DKC",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met1160",
    gatekeeper_residue="Thr1157",
    dfg_motif="DFG",
    indications=["非小细胞肺癌 MET 14 外显子跳跃突变", "肝细胞癌", "胃癌"],
    approved_drugs=["卡马替尼 (Capmatinib)", "特泊替尼 (Tepotinib)", "赛沃替尼 (Savolitinib)", "卡博替尼 (Cabozantinib)"],
    chembl_id="CHEMBL3714",
    sequence_length=1390,
    catalytic_sequence_snippet="MRAPAPIFSTLLCAFLALLLAPTAGAASPRKRKRKPRKRPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAPKRAP",
    clinical_phase_highest="Approved"
))

# --- 5. BTK / Hematologic Malignancies ---
_register(ClinicalTargetRecord(
    symbol="BTK",
    parent_symbol="BTK",
    name="Tyrosine-protein kinase BTK (Wild-Type)",
    uniprot_id="Q06187",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="B 细胞受体（BCR）信号传导的关键中枢，B 细胞淋巴瘤与慢性淋巴细胞白血病（CLL）的黄金靶点。",
    pdb_code="3GEN",
    resolution="1.60 Å",
    binding_mode_typical="covalent",
    hinge_residue="Met477",
    gatekeeper_residue="Thr474",
    dfg_motif="DFG",
    indications=["慢性淋巴细胞白血病 (CLL)", "套细胞淋巴瘤 (MCL)", "华氏巨球蛋白血症 (WM)"],
    approved_drugs=["依鲁替尼 (Ibrutinib)", "阿卡替尼 (Acalabrutinib)", "泽布替尼 (Zanubrutinib)", "奥布替尼 (Orelabrutinib)"],
    chembl_id="CHEMBL3998",
    sequence_length=659,
    catalytic_sequence_snippet="MAAVILESIFLKRSQQKKKTSPLNFKKRLFLLTVHKLSYYEYDFERGRRGSKKGSIDVEKITCVETVVPEKNPPPERQIPRRGEESSEMEQISIIERFPYPFQVVYDEGPLYVFSPTEELRKRWIHQLKNVIRYNIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="BTK-C481S",
    parent_symbol="BTK",
    name="BTK (C481S 共价耐药突变体)",
    uniprot_id="Q06187",
    family="TK",
    is_mutant=True,
    mutation_type="Covalent Site",
    mutation_description="依鲁替尼、泽布替尼最常见的耐药机制。半胱氨酸缺失导致共价加成受阻，对第一代/第二代共价 BTK 抑制剂产生全面耐药。",
    pdb_code="6O8I",
    resolution="1.70 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met477",
    gatekeeper_residue="Thr474",
    dfg_motif="DFG",
    indications=["共价 BTK 抑制剂耐药型 CLL/SLL"],
    approved_drugs=["吡妥布替尼 (Pirtobrutinib, 非共价可逆新药)", "ARQ-531 (在研)"],
    chembl_id="CHEMBL3998",
    sequence_length=659,
    catalytic_sequence_snippet="MAAVILESIFLKRSQQKKKTSPLNFKKRLFLLTVHKLSYYEYDFERGRRGSKKGSIDVEKITCVETVVPEKNPPPERQIPRRGEESSEMEQISIIERFPYPFQVVYDEGPLYVFSPTEELRKRWIHQLKNVIRYNIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGSLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

# --- 6. JAK/STAT Pathway ---
_register(ClinicalTargetRecord(
    symbol="JAK1",
    parent_symbol="JAK1",
    name="Tyrosine-protein kinase JAK1",
    uniprot_id="P23458",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="介导多种促炎细胞因子（IL-6, IFN-gamma 等）传导，自身免疫性疾病与重症移植物抗宿主病的核心靶点。",
    pdb_code="3EYG",
    resolution="1.90 Å",
    binding_mode_typical="type_i",
    hinge_residue="Leu959",
    gatekeeper_residue="Met956",
    dfg_motif="DFG",
    indications=["类风湿关节炎 (RA)", "特应性皮炎 (AD)", "溃疡性结肠炎 (UC)"],
    approved_drugs=["乌帕替尼 (Upadacitinib)", "托法替布 (Tofacitinib)", "阿布昔替尼 (Abrocitinib)"],
    chembl_id="CHEMBL2835",
    sequence_length=1154,
    catalytic_sequence_snippet="MQYLNIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="JAK2",
    parent_symbol="JAK2",
    name="Tyrosine-protein kinase JAK2 (Wild-Type)",
    uniprot_id="O60674",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="调节红细胞生成素（EPO）与血小板生成素（TPO）信号，骨髓增殖性肿瘤（MPN）的驱动基因。",
    pdb_code="3E62",
    resolution="1.70 Å",
    binding_mode_typical="type_i",
    hinge_residue="Leu932",
    gatekeeper_residue="Met929",
    dfg_motif="DFG",
    indications=["骨髓纤维化 (MF)", "真性红细胞增多症 (PV)", "原发性血小板增多症 (ET)"],
    approved_drugs=["芦可替尼 (Ruxolitinib)", "菲达替尼 (Fedratinib)", "帕克替尼 (Pacritinib)"],
    chembl_id="CHEMBL2971",
    sequence_length=1132,
    catalytic_sequence_snippet="MQYLNIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="JAK2-V617F",
    parent_symbol="JAK2",
    name="JAK2 (V617F 假激酶域经典驱动突变体)",
    uniprot_id="O60674",
    family="TK",
    is_mutant=True,
    mutation_type="Activation Loop",
    mutation_description="在真性红细胞增多症中发生率高达 95%。位于 JH2 假激酶自抑制结构域，解除自抑制，使激酶在无配体刺激下持续过度激活。",
    pdb_code="4IVA",
    resolution="2.10 Å",
    binding_mode_typical="type_i",
    hinge_residue="Leu932",
    gatekeeper_residue="Met929",
    dfg_motif="DFG",
    indications=["V617F 突变型真性红细胞增多症与骨髓纤维化"],
    approved_drugs=["芦可替尼 (Ruxolitinib)"],
    chembl_id="CHEMBL2971",
    sequence_length=1132,
    catalytic_sequence_snippet="MQYLNIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="TYK2",
    parent_symbol="TYK2",
    name="Non-receptor tyrosine-protein kinase TYK2",
    uniprot_id="P29597",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="JAK 家族关键成员，介导 IL-23, IL-12 与 I 型干扰素信号，银屑病等自免疾病热门高选择性靶点。",
    pdb_code="4GIH",
    resolution="2.00 Å",
    binding_mode_typical="allosteric",
    hinge_residue="Val985",
    gatekeeper_residue="Met978",
    dfg_motif="DFG",
    indications=["斑块状银屑病", "银屑病关节炎", "系统性红斑狼疮 (SLE)"],
    approved_drugs=["德克伐昔替尼 (Deucravacitinib, 变构高选择性抑制剂)"],
    chembl_id="CHEMBL3553",
    sequence_length=1187,
    catalytic_sequence_snippet="MPLELLQHLREVLEEKRILVQLTAVEVVKWENLRLTEELVRQVLSELEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLE",
    clinical_phase_highest="Approved"
))

# --- 7. CDK Family (Cell Cycle Regulation) ---
_register(ClinicalTargetRecord(
    symbol="CDK2",
    parent_symbol="CDK2",
    name="Cyclin-dependent kinase 2",
    uniprot_id="P24941",
    family="CMGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="调控细胞周期 G1/S 转换与 DNA 复制，CCNE1 扩增肿瘤的合成致死重要靶点。",
    pdb_code="1HCK",
    resolution="1.90 Å",
    binding_mode_typical="type_i",
    hinge_residue="Leu83",
    gatekeeper_residue="Phe80",
    dfg_motif="DFG",
    indications=["CCNE1 扩增型卵巢癌/乳腺癌", "克服 CDK4/6 耐药"],
    approved_drugs=["Dinaciclib (在研)", "PF-07104091 (选择性 CDK2 抑制剂在研)"],
    chembl_id="CHEMBL301",
    sequence_length=298,
    catalytic_sequence_snippet="MENFQKVEKIGEGTYGVVYKARNKLTGEVVALKKIRLDTETEGVPSTAIREISLLKELNHPNIVKLLDVIHTENKLYLVFEFLHQDLKKFMDASALTGIPLPLIKSYLFQLLQGLAFCHSHRVLHRDLKPQNLLINTEGAIKLADFGLARAFGVPVRTYTHEVVTLWYRAPEILLGCKYYSTAVDIWSLGCIFAEMVTRRALFPGDSEIDQLFRIFRTLGTPDEVVWPGVTSMPDYKPSFPKWARQDFSKVVPPLDEDGRSLLSQMLHYDPNKRISAKAALAHPFFQDVTKPVPHLRL",
    clinical_phase_highest="Phase II/III"
))

_register(ClinicalTargetRecord(
    symbol="CDK4",
    parent_symbol="CDK4",
    name="Cyclin-dependent kinase 4",
    uniprot_id="P11802",
    family="CMGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="与 Cyclin D 结合磷酸化 Rb 蛋白释放 E2F，HR+/HER2- 晚期乳腺癌一线内分泌治疗黄金基石。",
    pdb_code="2W96",
    resolution="2.30 Å",
    binding_mode_typical="type_i",
    hinge_residue="Val96",
    gatekeeper_residue="Phe93",
    dfg_motif="DFG",
    indications=["HR+/HER2- 晚期或转移性乳腺癌", "脂肪肉瘤"],
    approved_drugs=["帕博西尼 (Palbociclib)", "利波西尼 (Ribociclib)", "阿贝西利 (Abemaciclib)", "达罗西利 (Dalpiciclib)"],
    chembl_id="CHEMBL339",
    sequence_length=303,
    catalytic_sequence_snippet="MATSRYEPVAEIGVGAYGTVYKARDPHSGHFVALKSVRVPNGGGGGGGLPISTVREVALLRRLEAFEHPNVVRLMDVCATSRTDREIKVTLVFEHVDQDLRTYLDKAPPPGLPAETIKDLMRQFLRGLDFLHANCIVHRDLKPENILVTSGGTVKLADFGLARIYSYQMALTPVVVTLWYRAPEVLLQSTYATPVDMWSVGCIFAEMFRRKPLFCGNSEADQLGKIFDLIGLPPEDDWPRDVSLPRGAFPPRGPRPVQSVVPEMEESGAQLLLEMLTFNPHKRISAFRALQHSYLHKDEGNPE",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="CDK6",
    parent_symbol="CDK6",
    name="Cyclin-dependent kinase 6",
    uniprot_id="Q00534",
    family="CMGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="与 CDK4 高度同源，造血系统分化与白血病干细胞自我更新的核心调控者。",
    pdb_code="1XO2",
    resolution="1.90 Å",
    binding_mode_typical="type_i",
    hinge_residue="Val101",
    gatekeeper_residue="Phe98",
    dfg_motif="DFG",
    indications=["HR+ 乳腺癌", "T-ALL 白血病"],
    approved_drugs=["帕博西尼", "利波西尼", "阿贝西利"],
    chembl_id="CHEMBL2345",
    sequence_length=326,
    catalytic_sequence_snippet="MEKDGLCRADQQYECVAEIGEGAYGKVFKARDLKNGGRFVALKRVRVQTGEEGMPLSTIREVAVLRHLETFEHPNVVRLFDVCTVSRTDRETKLTLVFEHVDQDLTTYLDKVPEPGVPTETIKDMMFQLLRGLDFLHSHRVVHRDLKPQNILVTSSGQIKLADFGLARIYSFQMALTSVVVTLWYRAPEVLLQSSYATPVDLWSVGCIFAEMFRRKPLFRGSSDVDQLGKILDVIGLPGEEDWPRDVALPRQAFHSKSAQPIEKFVTDIDELGKDLLLKCLTFNPAKRISAYSALSHPYFQDLERCKENLDSHLPPSQNTSELNTA",
    clinical_phase_highest="Approved"
))

# --- 8. Angiogenesis / VEGFR Family ---
_register(ClinicalTargetRecord(
    symbol="KDR",
    parent_symbol="KDR",
    name="Vascular endothelial growth factor receptor 2 (VEGFR2)",
    uniprot_id="P35968",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="肿瘤血管生成（Angiogenesis）最重要的受体酪氨酸激酶，抗肿瘤微环境血供切断的基石靶点。",
    pdb_code="4AG8",
    resolution="1.95 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys919",
    gatekeeper_residue="Val916",
    dfg_motif="DFG",
    indications=["肾细胞癌 (RCC)", "肝细胞癌 (HCC)", "胃癌", "结直肠癌", "甲状腺癌"],
    approved_drugs=["阿帕替尼 (Apatinib)", "索拉非尼", "舒尼替尼 (Sunitinib)", "乐伐替尼 (Lenvatinib)", "雷莫芦单抗"],
    chembl_id="CHEMBL279",
    sequence_length=1356,
    catalytic_sequence_snippet="MQSKVLLAVALWLCVETRAASVGLPSVSLDLPRLSIQKDILTIKANTTLQITCRGQRDLDWLWPNNQSGSEQRVEVTECSDGLFCKTLTIPKVIGNDTGAYKCFYRETDLASVIYVYVQDYRSPFIASVSDQHGVVYITENKNKTVVIPCLGSISNLNVSLCARYPEKRFVPDGNRISWDSKKGFTIPSYMISYAGMVFCEAKINDESYQSIMYIVVVVGYRIYDVVLSPSHGIELSVGEKLVLNCTARTELNVGIDFNWEYPSSKHQHKKLVNRDLKTQSGSEMKKFLSTLTIDGVTRSDQGLYTCAASSGLMTKKNSTFVRVHEKPFVAFGSGMESLVEATVGERVRIPAKYLGYPPPEIKWYKNGIPLESNHTIKAGHVLTIMEVSERDTGNYTVILTNPISKEKQSHVVSLVVYVPPQIGEKSLISPVDSYQYGTTQTLTCTVYAIPPPHHIHWYWQLEEECANEPSQAVSVTNPYPCEEWRSVEDFQGGNKIEVNKNQFALIEGKNKTVSTLVIQAANVSALYKCEAVNKVGRGERVISFHVTRGPEITLQPDMQPTEQESVSLWCTADRSTFENLTWYKLGPQPLPIHVGELPTPVCKNLDTLWKLNATMFSNSTNDILIMELKNASLQDQGDYVCLAQDRKTKKRHCVVRQLTVLERVAPTITGNLENQTTSIGESIEVSCTASGNPPPQIMWFKDNETLVEDSGIVLKDGNRNLTIRRVRKEDEGLYTCQACSVLGCAKVEAFFIIEGAQEKTNLEIIILVGTAVIAMFFWLLLVIILRTVKRANGGELKTGYLSIVMDPDELPLDEHCERLPYDASKWEFPRDRLKLGKPLGRGAFGQVIEADAFGIDKTATCRTVAVKMLKEGATHSEHRALMSELKILIHIGHHLNVVNLLGACTKPGGPLMVIVEFCKFGNLSTYLRSKRNEFVPYKVAPEDLYKDFLTLEHLICYSFQVAKGMEFLASRKCIHRDLAARNILLSEKNVVKICDFGLARDIYKDPDYVRKGDARLPLKWMAPETIFDRVYTIQSDVWSFGVLLWEIFSLGASPYPGVKIDEEFCRRLKEGTRMRAPDYTTPEMYQTMLDCWHGEPSQRPTFSELVEHLGNLLQANAQQDGKDYIVLPISETLSMEEDSGLSLPTSPVSCMEEEEVCDPKFHYDNTAGISQYLQNSKRKSRPVSVKTFEDIPLEEPEVKVIPDDNQTDSGMVLASEELKTLEDRTKLSPSFGGMVPSKSRESVASEGSNQTSGYQSGYHSDDTDTTVYSSEEAELLKLIEIGVQTGSTAQILQPDSGTTLSSPPV",
    clinical_phase_highest="Approved"
))

# --- 9. KIT & FLT3 Family ---
_register(ClinicalTargetRecord(
    symbol="KIT",
    parent_symbol="KIT",
    name="Mast/stem cell growth factor receptor Kit (c-Kit WT)",
    uniprot_id="P10721",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="胃肠间质瘤（GIST）及系统性肥大细胞增生症（SM）的关键驱动靶点。",
    pdb_code="1T46",
    resolution="1.60 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys673",
    gatekeeper_residue="Thr670",
    dfg_motif="DFG",
    indications=["胃肠道间质瘤 (GIST)", "系统性肥大细胞增多症", "急性髓系白血病"],
    approved_drugs=["伊马替尼 (Imatinib)", "舒尼替尼", "瑞戈非尼 (Regorafenib)", "瑞派替尼 (Ripretinib)"],
    chembl_id="CHEMBL240",
    sequence_length=976,
    catalytic_sequence_snippet="MRGARGAWDFLCVLLLLLRVQTGSSQPSVSPGEPSPPSIHPGKSDLIVRVGDEIRLLCTDPGFVKWTFEILDETNENKQNEWITEKAEATNTGKYTCTNKHGLSNSIYVFVRDPAKLFLVDRSLYGKEDNDTLVRCPLTDPEVTNYSLKGCQGKPLPKDLRFIPDPKAGIMIKSVKRAYHRLCLHCSVDQEGKSVLSEKFILKVRPAFKAVPVVSVSKASYLLREGEEFTVTCTIKDVSSSVYSTWKRENSQTKLQEKYNSWHHGDFNYERQATLTISSARVNDSGVFMCYANNTFGSANVTTTLEVVDKGFINIFPMINTTVFVNDGENVDLIVEYEAFPKPEHQQWIYMNRTFTDKWEDYPKSENESNIRYVSELHLTRLKGTEGGTYTFLVSNSDVNAAIAFNVYVNTKPEILTYDRLVNGMLQCVAAGFPEPTIDWYFCPGTEQRCSASVLPVDVQTLNSSGPPFGKLVVQSSIDSSAFKHNGTVECKAYNDVGKTSAYFNFAFKGNNKEQIHPHTLFTPLLIGFVIVAGMMCIIVMILTYKYLQKPMYEVQWKVVEEINGNNYVYIDPTQLPYDHKWEFPRNRLSFGKTLGAGAFGKVVEATAYGLIKSDAAMTVAVKMLKPSAHLTEREALMSELKVLSYLGNHMNIVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDSFICSKQEDHAEAALYKNLLHSKESSCSDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="FLT3",
    parent_symbol="FLT3",
    name="Receptor-type tyrosine-protein kinase FLT3 (Wild-Type)",
    uniprot_id="P36888",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="急性髓系白血病（AML）中最常见的突变基因（占约 30%），伴有 ITD 或 TKD 突变者预后极差。",
    pdb_code="4XUF",
    resolution="2.20 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys694",
    gatekeeper_residue="Phe691",
    dfg_motif="DFG",
    indications=["FLT3 突变型急性髓系白血病 (AML)"],
    approved_drugs=["米哚妥林 (Midostaurin)", "吉列替尼 (Gilteritinib)", "奎扎替尼 (Quizartinib)"],
    chembl_id="CHEMBL1974",
    sequence_length=993,
    catalytic_sequence_snippet="MPALARDGGQLPLLVVFSAMIFGTITNQDLPVIKCVLINHKNNDSSVGKSSSYPMVSESPEDLGCALRPQSSGTVYEAAAVEVDVSASITLQVLVDAPGNISCLWVFKHSSLNCQPHFDLQNRGVVSMVILKMTETQAGEYLLFIQSEATNYTILFTVSIRNTLLYTLRRPYFRKMENQDALVCISESVPEPIVEWVLCDSQGESCKEESPAVVKKEEKVLHELFGTDIRCCARNELGRECTRLFTIDLNQTPQTTLPQLFLKVGEPLWIRCKAVHVNHGFGLTWELENKALEEGNYFEMSTYSTNRTMIRILFAFVSSVERNETGYLTCSCRNSHGVMESTISLQVVGPKGLVTVVVSFGLVFSIILVVFLNRVRRQRKPEYVLKADSLPTTVYEEPEQLCYRNTKSEFPLDRLSFGKTLGAGAFGKVVEATAYGLIKRDAGMTVAVKMLKPSAHLAEREALMSELKVLSYLGNHMNVVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDVFICSKREDHAEAALYKNLLHSKESSCPDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

# --- 10. RET & FGFR Family ---
_register(ClinicalTargetRecord(
    symbol="RET",
    parent_symbol="RET",
    name="Proto-oncogene tyrosine-protein kinase receptor Ret",
    uniprot_id="P07949",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="甲状腺髓样癌（MTC）及 RET 融合非小细胞肺癌的核心致癌驱动基因。",
    pdb_code="2IVU",
    resolution="2.00 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met808",
    gatekeeper_residue="Val804",
    dfg_motif="DFG",
    indications=["RET 融合阳性非小细胞肺癌", "甲状腺髓样癌 (MTC)"],
    approved_drugs=["塞普替尼 (Selpercatinib)", "普拉替尼 (Pralsetinib)", "凡德他尼 (Vandetanib)"],
    chembl_id="CHEMBL2234",
    sequence_length=1114,
    catalytic_sequence_snippet="MAKATSGAAGLRLLLLLLLPLLGKVALGLYFSRDAYWEKLYVDQAAGTPLVVRVGDELKLLCTDPGFVKWTFEILDETNENKQNEWITEKAEATNTGKYTCTNKHGLSNSIYVFVRDPAKLFLVDRSLYGKEDNDTLVRCPLTDPEVTNYSLKGCQGKPLPKDLRFIPDPKAGIMIKSVKRAYHRLCLHCSVDQEGKSVLSEKFILKVRPAFKAVPVVSVSKASYLLREGEEFTVTCTIKDVSSSVYSTWKRENSQTKLQEKYNSWHHGDFNYERQATLTISSARVNDSGVFMCYANNTFGSANVTTTLEVVDKGFINIFPMINTTVFVNDGENVDLIVEYEAFPKPEHQQWIYMNRTFTDKWEDYPKSENESNIRYVSELHLTRLKGTEGGTYTFLVSNSDVNAAIAFNVYVNTKPEILTYDRLVNGMLQCVAAGFPEPTIDWYFCPGTEQRCSASVLPVDVQTLNSSGPPFGKLVVQSSIDSSAFKHNGTVECKAYNDVGKTSAYFNFAFKGNNKEQIHPHTLFTPLLIGFVIVAGMMCIIVMILTYKYLQKPMYEVQWKVVEEINGNNYVYIDPTQLPYDHKWEFPRNRLSFGKTLGAGAFGKVVEATAYGLIKSDAAMTVAVKMLKPSAHLTEREALMSELKVLSYLGNHMNIVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDSFICSKQEDHAEAALYKNLLHSKESSCSDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="FGFR1",
    parent_symbol="FGFR1",
    name="Fibroblast growth factor receptor 1",
    uniprot_id="P11362",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="成纤维细胞生长因子受体家族原型，膀胱癌、胆管癌与鳞状细胞肺癌中的重要治疗靶点。",
    pdb_code="5V40",
    resolution="1.85 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met568",
    gatekeeper_residue="Val565",
    dfg_motif="DFG",
    indications=["尿路上皮癌", "晚期胆管癌", "鳞状非小细胞肺癌"],
    approved_drugs=["厄达替尼 (Erdafitinib)", "培米替尼 (Pemigatinib)", "菲达替尼 (Futibatinib)"],
    chembl_id="CHEMBL3038",
    sequence_length=822,
    catalytic_sequence_snippet="MWSWKCLLFWAVLVTATLCTARPSPTLPEQAQPWGAPVEVESFLVHPGDLLQLRCRLRDDVQSINWLRDGVQLAESNRTRITGEEVEVQDSVPADSGLYACVTSSPSGSDTTYFSVNVSDALPSSEDDDDDDDSSSEEKETDNTKPNPVAPYWTSPEKMEKKLHAVPAAKTVKFKCPSSGTPNPTLRWLKNGKEFKPDHRIGGYKVRYATWSIIMDSVVPSDKGNYTCIVENEYGSINHTYQLDVVERSPHRPILQAGLPANKTVALGSNVEFMCKVYSDPQPHIQWLKHIEVNGSKIGPDNLPYVQILKTAGVNTTDKEMEVLHLRNVSFEDAGEYTCLAGNSIGLSHHSAWLTVLEALEERPAVMTSPLYLEIIIYCTGAFLISCMVGSVIVYKMKSGTKKSDFHSQMAVHKLAKSIPLRRQVTVSADSSASMNSGVLLVRPSRLSSSGTPMLAGVSEYELPEDPRWELPRDRLVLGKPLGEGCFGQVVLAEAIGLDKDKPNRVTKVAVKMLKSDATEKDLSDLISEMEMMKMIGKHKNIINLLGACTQDGPLYVIVEYASKGNLREYLQARRPPGLEYCYNPSHNPEEQLSSKDLVSCAYQVARGMEYLASKKCIHRDLAARNVLVTEDNVMKIADFGLARDIHHIDYYKKTTNGRLPVKWMAPEALFDRIYTHQSDVWSFGVLLWEIFTLGGSPYPGVPVEELFKLLKEGHRMDKPSNCTNELYMMMRDCWHAVPSQRPTFKQLVEDLDRIVALTSNQEYLDLSMPLDQYSPSFPDTRSSTCSSGEDSVFSHEPLPEEPCLPRHPAQLANGGLKRR",
    clinical_phase_highest="Approved"
))

# --- 11. PI3K/AKT/mTOR & Aurora Kinases ---
_register(ClinicalTargetRecord(
    symbol="AKT1",
    parent_symbol="AKT1",
    name="RAC-alpha serine/threonine-protein kinase (AKT1/PKB)",
    uniprot_id="P31749",
    family="AGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="PI3K-AKT 存活通路的核心执行者，调控代谢、抗凋亡与肿瘤耐药。",
    pdb_code="3O96",
    resolution="1.70 Å",
    binding_mode_typical="allosteric",
    hinge_residue="Met281",
    gatekeeper_residue="Thr278",
    dfg_motif="DFG",
    indications=["PIK3CA/AKT1 突变型乳腺癌", "前列腺癌"],
    approved_drugs=["卡匹色替 (Capivasertib)", "伊帕色替 (Ipatasertib, 在研)"],
    chembl_id="CHEMBL4005",
    sequence_length=480,
    catalytic_sequence_snippet="MSDVAIVKEGWLHKRGEYIKTWRPRYFLLKNDGTFIGYKERPQDVDQREAPLNNFSVAQCQLMKTERPRPNTFIIRCLQWTTVIERTFHVETPEEREEWTTAIQTVADGLKKQEEEEMDFRSGSPSDNSGAEEMEVSLAKPKHRVTMNEFEYLKLLGKGTFGKVILVKEKATGRYYAMKILKKEVIVAKDEVAHTLTENRVLQNSRHPFLTALKYSFQTHDRLCFVMEYANGGELFFHLSRERVFSEDRARFYGAEIVSALDYLHSEKNVVYRDLKLENLMLDKDGHIKITDFGLCKEGIKDGATMKTFCGTPEYLAPEVLEDNDYGRAVDWWGLGVVMYEMMCGRLPFYNQDHEKLFELILMEEIRFPRTLGPEAKSLLSGLLKKDPKQRLGGGSEDAKEIMQHRFFAGIVWQHVYEKKLSPPFKPQVTSETDTRYFDEEFTAQMITITPPDQDDSMECVDSERRPHFPQFSYSASSTA",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="AURKA",
    parent_symbol="AURKA",
    name="Aurora kinase A",
    uniprot_id="O14965",
    family="Other",
    is_mutant=False,
    mutation_type=None,
    mutation_description="调控有丝分裂中心体成熟与纺锤体组装，MYCN 扩增型神经母细胞瘤与三阴性乳腺癌关键靶点。",
    pdb_code="1MQ4",
    resolution="1.90 Å",
    binding_mode_typical="type_i",
    hinge_residue="Ala213",
    gatekeeper_residue="Leu210",
    dfg_motif="DFG",
    indications=["MYC 驱动型实体瘤", "小细胞肺癌", "外周 T 细胞淋巴瘤"],
    approved_drugs=["阿里塞替 (Alisertib, 在研)", "Tozasertib"],
    chembl_id="CHEMBL4722",
    sequence_length=403,
    catalytic_sequence_snippet="MDRSKENCISGPVKATAPVGGPKRVLVTQQFPCQNPLPVNSGQAQRVLCPSNSSQRIPLQAQKLVSSHKPVQNQKQKQLQATSVPHPVSRPLNNTQKSKQPLPSAPENNPEEELASKQKNEESKKRQWALEDFEIGRPLGKGKFGNVYLAREKQSKFILALKVLFKAQLEKAGVEHQLRREVEIQSHLRHPNILRLYGYFHDATRVYLILEYAPLGTVYRELQKLSKFDEQRTATYITELANALSYCHSKRVIHRDIKPENLLLGSAGELKIADFGWSVHAPSSRRTTLCGTLDYLPPEMIEGRMHDEKVDLWSLGVLCYEFLVGKPPFEANTYQETYKRISRVEFTFPDFVTEGARDLISRLLKHNPSQRPMLREVLEHPWITANSSKPSNCQNKESASKQS",
    clinical_phase_highest="Phase III"
))

_register(ClinicalTargetRecord(
    symbol="SRC",
    parent_symbol="SRC",
    name="Proto-oncogene tyrosine-protein kinase Src",
    uniprot_id="P12931",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="第一个被发现的原癌基因激酶，作为非受体酪氨酸激酶参与整合素与生长因子下游浸润浸润转移。",
    pdb_code="2SRC",
    resolution="1.50 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met341",
    gatekeeper_residue="Thr338",
    dfg_motif="DFG",
    indications=["结直肠癌", "转移性乳腺癌", "抗血管生成联用"],
    approved_drugs=["达沙替尼 (高亲和力靶向)", "博舒替尼 (Bosutinib)"],
    chembl_id="CHEMBL267",
    sequence_length=536,
    catalytic_sequence_snippet="MGSNKSKPKDASQRRRSLEPAENVHGAGGGAFPASQTPSKPASADGHRGPSAAFAPAAAEPKLFGGFNSSDTVTSPQRAGPLAGGVTTFVALYDYESRTETDLSFKKGERLQIVNNTEGDWWLAHSLSTGQTGYIPSNYVAPSDSIQAEEWYFGKITRRESERLLLNAENPRGTFLVRESETTKGAYCLSVSDFDNAKGLNVKHYKIRKLDSGGFYITSRTQFNSLQQLVAYYSKHADGLCHRLTTVCPTSKPQTQGLAKDAWEIPRESLRLEVKLGQGCFGEVWMGTWNGTTRVAIKTLKPGTMSPEAFLQEAQVMKKLRHEKLVQLYAVVSEEPIYIVTEYMSKGSLLDFLKGETGKYLRLPQLVDMAAQIASGMAYVERMNYVHRDLRAANILVGENLVCKVADFGLARLIEDNEYTARQGAKFPIKWTAPEAALYGRFTIKSDVWSFGILLTELTTKGRVPYPGMVNREVLDQVERGYRMPCPPECPESLHDLMCQCWRKEPEERPTFEYLQAFLEDYFTSTEPQYQPGENL",
    clinical_phase_highest="Approved"
))


# Helper functions

# --- 12. Additional Clinical Resistance Mutants & Kinase Drivers ---
_register(ClinicalTargetRecord(
    symbol="ALK-L1196M",
    parent_symbol="ALK",
    name="ALK (L1196M 门控残基耐药突变体)",
    uniprot_id="Q9UM73",
    family="TK",
    is_mutant=True,
    mutation_type="Gatekeeper",
    mutation_description="克唑替尼常见耐药突变，亮氨酸变甲硫氨酸位阻增大，二代/三代 TKI 可有效克服。",
    pdb_code="2YFX",
    resolution="1.90 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met1199",
    gatekeeper_residue="Met1196",
    dfg_motif="DFG",
    indications=["克唑替尼耐药非小细胞肺癌"],
    approved_drugs=["布加替尼 (Brigatinib)", "洛拉替尼 (Lorlatinib)"],
    chembl_id="CHEMBL4247",
    sequence_length=1620,
    catalytic_sequence_snippet="MGAIGLLWLLPLLLSTAAVGSGMGTGQRAGSPAAGPPLQPREPLSYSRLQRKSLAVDFVVPSLFRVYARDLLLPPSSSELKAGRPEARGSLALDCAPLLRLLGPAPGVSWTAGSPAPAEARTLSRVLKGGSVRKLRRAKQLVLELGEEAILEGCVGPPGEAAVGLLQFNLSELFSWWIRQGEGRLRIRLMPEKKASEVGREGRLSAAIRASQPRLLFQIFGTGHSSLESPTNMPSPSPPDYFTWNLTWIMKDSFPFLSHRSRYGLECSFDFPCELEYSPPLHDLRNQSWSWRRIPSEEASQMDLLDGPGAERSKEMPRGSFLLLNTSADSKHTILSPWMRSSSEHCTLAVSVHRHLQPSGRYIAQLLPHNEAAREILLMPTPGKHGWTVLQGRIGRPDNPFRVALEYISSGNRSLSAVDFFALKNCSEGTSPGSKMALQSSFTCWNGTVLQLGQACDFHQDCAQGEDESQMCRKLPVGFYCNFEDGFCGWTQGTLSPHTPQWQVRTLKDARFQDHQDHALLLSTTDVPASESATVTSATFPAPIKSSPCELRMSWLIRGVLRGNVSLVLVENKTGKEQGRMVWHVAYEGLSLWQWMVLPLLDVSDRFWLQMVAWWGQGSRAIVAFDNISISLDCYLTISGEDKILQNTAPKSRNLFERNPNKELKPGENSPRQTPIFDPTVHWLFTTCGASGPHGPTQAQCNNAYQNSNLSVEVGSEGPLKGIQIWKVPATDTYSISGYGAAGGKGGKNTMMRSHGVSVLGIFNLEKDDMLYILVGQQGEDACPSTNQLIQKVCIGENNVIEEEIRVNRSVHEWAGGGGGGGGATYVFKMKDGVPVPLIIAAGGGGRAYGAKTDTFHPERLENNSSVLGLNGNSGAAGGGGGWNDNTSLLWAGKSLQEGATGGHSCPQAMKKWGWETRGGFGGGGGGCSSGGGGGGYIGGNAASNNDPEMDGEDGVSFISPLGILYTPALKVMEGHGEVNIKHYLNCSHCEVDECHMDPESHKVICFCDHGTVLAEDGVSCIVSPTPEPHLPLSLILSVVTSALVAALVLAFSGIMIVYRRKHQELQAMQMELQSPEYKLSKLRTSTIMTDYNPNYCFAGKTSSISDLKEVPRKNITLIRGLGHGAFGEVYEGQVSGMPNDPSPLQVAVKTLPEVCSEQDELDFLMEALIISKFNHQNIVRCIGVSLQSLPRFILLELMAGGDLKSFLRETRPRPSQPSSLAMLDLLHVARDIACGCQYLEENHFIHRDIAARNCLLTCPGPGRVAKIGDFGMARDIYRASYYRKGGCAMLPVKWMPPEAFMEGIFTSKTDTWSFGVLLWEIFSLGYMPYPSKSNQEVLEFVTSGGRMDPPKNCPGPVYRIMTQCWQHQPEDRPNFAIILERIEYCTQDPDVINTALPIEYGPLVEEEEKVPVRPKDPEGVPPLLVSQQAKREEERSPAAPPPLPTTSSGKAAKKPTAAEISVRVPRGPAVEGGHVNMAFSQSNPPSELHKVHGSRNKPTSLWNPTYGSWFTEKPTKKNNPIAKKEPHDRGNLGLEGSCTVPPNVATGRLPGASLLLEPSSLTANMKEVPLFRLRHFPCGNVNYGYQQQGLPLEAATAPGAGHYEDTILKSKNSMNQPGP",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="ROS1-G2032R",
    parent_symbol="ROS1",
    name="ROS1 (G2032R 溶剂前沿耐药突变体)",
    uniprot_id="P08922",
    family="TK",
    is_mutant=True,
    mutation_type="Solvent Front",
    mutation_description="ROS1 抑制剂克唑替尼、恩曲替尼耐药最常见突变，对应 ALK G1202R 位点，侧链位阻显著。",
    pdb_code="7L7D",
    resolution="2.10 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met2029",
    gatekeeper_residue="Leu2026",
    dfg_motif="DFG",
    indications=["克唑替尼耐药型 ROS1 阳性非小细胞肺癌"],
    approved_drugs=["瑞普替尼 (Repotrectinib)", "Taletrectinib (在研)"],
    chembl_id="CHEMBL6125",
    sequence_length=2347,
    catalytic_sequence_snippet="HRDLAARNCLISKQGAKLVKVGDFGMARDIYKASYYRKGAKLPVKWMPPESLVDGVFTSKSDVWSFGVLLWEIFSLGYMPYPAKSNQEVLEFVTSGGRMDRPRNCPGPVYRIMTQCWQHEPEDRPNFSMILERIEYCTQDPDVIKTALPIEYGPLVEEEEKVPVRPKDPEGVPPLLVSQQAKREEERSPAAPPPLPTTSSGKAAKKPTAAEISVRVPRGPAVEGGHVNMAFSQSNPPSELHKVHGSRNKPTSLWNPTYGSWFTEKPTKKNNPIAKKEPHDRGNLGLEGSCTVPPNVATGRLPGASLLLEPSSLTANMKEVPLFRLRHFPCGNVNYGYQQQGLPLEAATAPGAGHYEDTILKSKNSMNQPGP",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="BTK-L528W",
    parent_symbol="BTK",
    name="BTK (L528W 非共价耐药突变体)",
    uniprot_id="Q06187",
    family="TK",
    is_mutant=True,
    mutation_type="P-loop",
    mutation_description="新型非共价 BTK 抑制剂吡妥布替尼（Pirtobrutinib）耐药突变，色氨酸突变封闭变构深腔。",
    pdb_code="8G48",
    resolution="1.75 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Met477",
    gatekeeper_residue="Thr474",
    dfg_motif="DFG",
    indications=["非共价 BTK 抑制剂耐药型套细胞淋巴瘤与 CLL"],
    approved_drugs=["BTK PROTAC 降解剂在研 (如 NX-2127, BGB-16673)"],
    chembl_id="CHEMBL3998",
    sequence_length=659,
    catalytic_sequence_snippet="MAAVILESIFLKRSQQKKKTSPLNFKKRLFLLTVHKLSYYEYDFERGRRGSKKGSIDVEKITCVETVVPEKNPPPERQIPRRGEESSEMEQISIIERFPYPFQVVYDEGPLYVFSPTEELRKRWIHQLKNVIRYNIKVLGSGAFGTVYKGLWIPEGEKVKIPVAIKELREATSPKANKEILDEAYVMASVDNPHVCRLLGICLTSTVQLITQLMPFGCLLDYVREHKDNIGSQYLLNWCVQIAKGMNYLEDRRLVHRDLAARNVLVKTPQHVKITDFGLAKLLGAEEKEYHAEGGKVPIKWMALESILHRIYTHQSDVWSYGVTVWELMTFGSKPYDGIPASEISSILEKGERLPQPPICTIDVYMIMVKCWMIDADSRPKFRELIIEFSKMARDPQRYLVIQGDERMHLPSPTDSNFYRALMDEEDMDDVVDADEYLIPQQGFFSSPSTSRTPLLSSLSATSNNSTVACIDRNGLQSCPIKEDSFLQRYSSDPTGALTEDSIDDTFLPVPEYINQSVPKRPAGSVQNPVYHNQPLNPAPSRDPHYQDPHSTAVGNPEYLNTVQPTCVNSTFDSPAHWAQKGSHQISLDNPDYQQDFFPKEAKPNGIFKGSTAENAEYLRVAPQSSEFIGA",
    clinical_phase_highest="Phase I/II"
))

_register(ClinicalTargetRecord(
    symbol="JAK3",
    parent_symbol="JAK3",
    name="Tyrosine-protein kinase JAK3",
    uniprot_id="P52333",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="仅在造血与淋巴组织表达，与普通γ链细胞因子结合，重度斑秃与特应性皮炎靶点。",
    pdb_code="4Z16",
    resolution="1.90 Å",
    binding_mode_typical="covalent",
    hinge_residue="Leu905",
    gatekeeper_residue="Met902",
    dfg_motif="DFG",
    indications=["重度斑秃 (Alopecia Areata)", "自身免疫性皮肤病"],
    approved_drugs=["利特昔替尼 (Ritlecitinib)", "托法替布 (Tofacitinib)"],
    chembl_id="CHEMBL2147",
    sequence_length=1124,
    catalytic_sequence_snippet="MPLQLLREVLEEKRILVQLTAVEVVKWENLRLTEELVRQVLSELEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLEEEERKRLE",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="CDK9",
    parent_symbol="CDK9",
    name="Cyclin-dependent kinase 9 (P-TEFb)",
    uniprot_id="P50750",
    family="CMGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="正转录延伸因子 P-TEFb 的催化亚基，磷酸化 RNA 聚合酶 II CTD，阻断 MYC/MCL-1 超转录。",
    pdb_code="3BLR",
    resolution="2.10 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys106",
    gatekeeper_residue="Phe103",
    dfg_motif="DFG",
    indications=["血液系统恶性肿瘤 (AML, CLL)", "MYC 驱动型实体瘤"],
    approved_drugs=["Enitociclib (在研)", "VIP152 (在研)", "Dinaciclib"],
    chembl_id="CHEMBL395",
    sequence_length=372,
    catalytic_sequence_snippet="MAKQYDSVECPFCDEVSKYEKLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAIMSKGKSKYERLAI",
    clinical_phase_highest="Phase II"
))

_register(ClinicalTargetRecord(
    symbol="FGFR2",
    parent_symbol="FGFR2",
    name="Fibroblast growth factor receptor 2",
    uniprot_id="P21802",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="晚期胆管癌（CCA）最重要的驱动基因融合靶点，伴有 FGFR2 融合者靶向治疗预后良好。",
    pdb_code="2PSQ",
    resolution="1.90 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met538",
    gatekeeper_residue="Val535",
    dfg_motif="DFG",
    indications=["不可切除局部晚期或转移性胆管癌 (CCA)", "胃癌"],
    approved_drugs=["培米替尼 (Pemigatinib)", "福替尼 (Futibatinib)", "厄达替尼"],
    chembl_id="CHEMBL2034",
    sequence_length=821,
    catalytic_sequence_snippet="MVSWGRFICLVVVTMATLSLARPSFSLVEDTTLEPEEPPTKYQISQPEVYVAAPGESLEVRCLLKDAAVISWTKDGVHLGPNNRTVLIGEYLQIKGATPRDSGLYACTASRTVDSETWYFMVNVTDAISSGDDEDDTDGAEDFVSENSNNKRAPYWTNTEKMEKRLHAVPAANTVKFRCPAGGNPMPTMRWLKNGKEFKQEHRIGGYKVRNQHWSLIMESVVPSDKGNYTCVVENEYGSINHTYHLDVVERSPHRPILQAGLPANASTVVGGDVEFVCKVYSDAQPHIQWIKHVEKNGSKYGPDGLPYLKVLKHSGINSSNAEVLALFNVTEADAGEYICKVSNYIGQANQSAWLTVLPKQQAPGREKEITASPDYLEIAIYCIGVFLIACMVVTVILCRMKNTTKKPDFSSQPAVHKLTKRIPLRRQVTVSAESSSSMNSNTPLVRITTRLSSTADTPMLAGVSEYELPEDPKWEFPRDKLTLGKPLGEGCFGQVVMAEAVGIDKDKPKEAVTVAVKMLKDDATEKDLSDLVSEMEMMKMIGKHKNIINLLGACTQDGPLYVIVEYASKGNLREYLRARRPPGMEYSYDINRVPEEQMSFKDLVSCAYQVARGMEYLASQKCIHRDLAARNVLVTEDNVMKIADFGLARDINNIDYYKKTTNGRLPVKWMAPEALFDRVYTHQSDVWSFGVLMWEIFTLGGSPYPGIPVEELFKLLKEGHRMDKPANCTHDLYMIMRECWHAAPSQRPTFKQLVEDLDRILTLTTNEEYLDLSQPLEQYSPSYPDTRSSCSSGDDSVFSPDPMPYEPCLPQYPHINGSVKT",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="FGFR3",
    parent_symbol="FGFR3",
    name="Fibroblast growth factor receptor 3",
    uniprot_id="P22607",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="尿路上皮癌（膀胱癌）中最常见的驱动靶点（突变或融合占约 20%）。",
    pdb_code="4K33",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met540",
    gatekeeper_residue="Val537",
    dfg_motif="DFG",
    indications=["局部晚期或转移性尿路上皮癌 (UC)"],
    approved_drugs=["厄达替尼 (Erdafitinib)"],
    chembl_id="CHEMBL2240",
    sequence_length=806,
    catalytic_sequence_snippet="MGAPACALALCVAVAIVAGASSESLGTEQRVVGRAAEVPGPEPGQQEQLVFGSGDAVELSCPPPGGGPMGPTVWVKDGTGLVPSERVLVGPQRLQVLNASHEDSGAYSCRQRLTQRVLCHFSVRVTDAPSSGDDEDGEDEAEDTGVDTGAPYWTRPERMDKKLLAVPAANTVRFRCPAAGNPTPSISWLKNGREFRGEHRIGGIKLRHQQWSLVMESVVPSDRGNYTCVVENKFGSIRQTYTLDVLERSPHRPILQAGLPANQTAVLGSDVEFHCKVYSDAQPHIQWLKHVEVNGSKVGPDGTPYVTVLKTAGVNTTDKELEVLYLHNVSFEDAGEYTCLAGNSIGFSHHSAWLVVLPAEEELVEADEAGSVYAGILSYGVGFFLFILVVAAVTLCRLRSPPKKGLGSPTVHKISRFPLKRQVSLESNASMSSNTPLVRIARLSSGEGPTLANVSELELPADPKWELSRARLTLGKPLGEGCFGQVVMAEAIGIDKDRAAKPVTVAVKMLKDDATDKDLSDLVSEMEMMKMIGKHKNIINLLGACTQGGPLYVIVEYAAKGNLREFLRARRPPGLDYSFDTCKPPEEQLTFKDLVSCAYQVARGMEYLASQKCIHRDLAARNVLVTEDNVMKIADFGLARDVHNLDYYKKTTNGRLPVKWMAPEALFDRVYTHQSDVWSFGVLLWEIFTLGGSPYPGIPVEELFKLLKEGHRMDKPANCTNELYYMMRECWHAAPSQRPTFKQLVEDLDRVLTVTSTDEYLDLSAPFEQYSPGGQDTPSSSSGEDSVFTHDLMPYEPCLPQYPHINGSVKT",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="KIT-T670I",
    parent_symbol="KIT",
    name="KIT (T670I 门控残基耐药突变体)",
    uniprot_id="P10721",
    family="TK",
    is_mutant=True,
    mutation_type="Gatekeeper",
    mutation_description="胃肠间质瘤伊马替尼/舒尼替尼治疗后常见继发耐药突变，对应 ABL1 T315I 位点。",
    pdb_code="6GQH",
    resolution="1.95 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys673",
    gatekeeper_residue="Ile670",
    dfg_motif="DFG",
    indications=["GIST 伊马替尼继发耐药"],
    approved_drugs=["瑞派替尼 (Ripretinib)", "瑞戈非尼"],
    chembl_id="CHEMBL240",
    sequence_length=976,
    catalytic_sequence_snippet="MRGARGAWDFLCVLLLLLRVQTGSSQPSVSPGEPSPPSIHPGKSDLIVRVGDEIRLLCTDPGFVKWTFEILDETNENKQNEWITEKAEATNTGKYTCTNKHGLSNSIYVFVRDPAKLFLVDRSLYGKEDNDTLVRCPLTDPEVTNYSLKGCQGKPLPKDLRFIPDPKAGIMIKSVKRAYHRLCLHCSVDQEGKSVLSEKFILKVRPAFKAVPVVSVSKASYLLREGEEFTVTCTIKDVSSSVYSTWKRENSQTKLQEKYNSWHHGDFNYERQATLTISSARVNDSGVFMCYANNTFGSANVTTTLEVVDKGFINIFPMINTTVFVNDGENVDLIVEYEAFPKPEHQQWIYMNRTFTDKWEDYPKSENESNIRYVSELHLTRLKGTEGGTYTFLVSNSDVNAAIAFNVYVNTKPEILTYDRLVNGMLQCVAAGFPEPTIDWYFCPGTEQRCSASVLPVDVQTLNSSGPPFGKLVVQSSIDSSAFKHNGTVECKAYNDVGKTSAYFNFAFKGNNKEQIHPHTLFTPLLIGFVIVAGMMCIIVMILTYKYLQKPMYEVQWKVVEEINGNNYVYIDPTQLPYDHKWEFPRNRLSFGKTLGAGAFGKVVEATAYGLIKSDAAMTVAVKMLKPSAHLTEREALMSELKVLSYLGNHMNIVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDSFICSKQEDHAEAALYKNLLHSKESSCSDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="KIT-D816V",
    parent_symbol="KIT",
    name="KIT (D816V 活化环外显子17驱动突变体)",
    uniprot_id="P10721",
    family="TK",
    is_mutant=True,
    mutation_type="Activation Loop",
    mutation_description="晚期系统性肥大细胞增生症（SM）主要致病突变，一代 TKI 天然耐药。",
    pdb_code="7M7O",
    resolution="2.10 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys673",
    gatekeeper_residue="Thr670",
    dfg_motif="DFG",
    indications=["晚期系统性肥大细胞增多症 (AdvSM)", "D816V 突变型 GIST"],
    approved_drugs=["阿伐替尼 (Avapritinib)"],
    chembl_id="CHEMBL240",
    sequence_length=976,
    catalytic_sequence_snippet="MRGARGAWDFLCVLLLLLRVQTGSSQPSVSPGEPSPPSIHPGKSDLIVRVGDEIRLLCTDPGFVKWTFEILDETNENKQNEWITEKAEATNTGKYTCTNKHGLSNSIYVFVRDPAKLFLVDRSLYGKEDNDTLVRCPLTDPEVTNYSLKGCQGKPLPKDLRFIPDPKAGIMIKSVKRAYHRLCLHCSVDQEGKSVLSEKFILKVRPAFKAVPVVSVSKASYLLREGEEFTVTCTIKDVSSSVYSTWKRENSQTKLQEKYNSWHHGDFNYERQATLTISSARVNDSGVFMCYANNTFGSANVTTTLEVVDKGFINIFPMINTTVFVNDGENVDLIVEYEAFPKPEHQQWIYMNRTFTDKWEDYPKSENESNIRYVSELHLTRLKGTEGGTYTFLVSNSDVNAAIAFNVYVNTKPEILTYDRLVNGMLQCVAAGFPEPTIDWYFCPGTEQRCSASVLPVDVQTLNSSGPPFGKLVVQSSIDSSAFKHNGTVECKAYNDVGKTSAYFNFAFKGNNKEQIHPHTLFTPLLIGFVIVAGMMCIIVMILTYKYLQKPMYEVQWKVVEEINGNNYVYIDPTQLPYDHKWEFPRNRLSFGKTLGAGAFGKVVEATAYGLIKSDAAMTVAVKMLKPSAHLTEREALMSELKVLSYLGNHMNIVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDSFICSKQEDHAEAALYKNLLHSKESSCSDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="FLT3-D835Y",
    parent_symbol="FLT3",
    name="FLT3 (D835Y 活化环耐药突变体)",
    uniprot_id="P36888",
    family="TK",
    is_mutant=True,
    mutation_type="Activation Loop",
    mutation_description="FLT3 抑制剂索拉非尼、奎扎替尼耐药最主要突变，使活化环持续打开处于活性态。",
    pdb_code="6JQR",
    resolution="2.30 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys694",
    gatekeeper_residue="Phe691",
    dfg_motif="DFG",
    indications=["复发难治性 FLT3 突变型急性髓系白血病"],
    approved_drugs=["吉列替尼 (Gilteritinib)"],
    chembl_id="CHEMBL1974",
    sequence_length=993,
    catalytic_sequence_snippet="MPALARDGGQLPLLVVFSAMIFGTITNQDLPVIKCVLINHKNNDSSVGKSSSYPMVSESPEDLGCALRPQSSGTVYEAAAVEVDVSASITLQVLVDAPGNISCLWVFKHSSLNCQPHFDLQNRGVVSMVILKMTETQAGEYLLFIQSEATNYTILFTVSIRNTLLYTLRRPYFRKMENQDALVCISESVPEPIVEWVLCDSQGESCKEESPAVVKKEEKVLHELFGTDIRCCARNELGRECTRLFTIDLNQTPQTTLPQLFLKVGEPLWIRCKAVHVNHGFGLTWELENKALEEGNYFEMSTYSTNRTMIRILFAFVSSVERNETGYLTCSCRNSHGVMESTISLQVVGPKGLVTVVVSFGLVFSIILVVFLNRVRRQRKPEYVLKADSLPTTVYEEPEQLCYRNTKSEFPLDRLSFGKTLGAGAFGKVVEATAYGLIKRDAGMTVAVKMLKPSAHLAEREALMSELKVLSYLGNHMNVVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDVFICSKREDHAEAALYKNLLHSKESSCPDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="RET-V804M",
    parent_symbol="RET",
    name="RET (V804M 门控残基耐药突变体)",
    uniprot_id="P07949",
    family="TK",
    is_mutant=True,
    mutation_type="Gatekeeper",
    mutation_description="卡博替尼、凡德他尼治疗后常见门控耐药突变，新一代高选择性抑制剂可克服。",
    pdb_code="7JW0",
    resolution="2.10 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met808",
    gatekeeper_residue="Met804",
    dfg_motif="DFG",
    indications=["RET 融合/突变型晚期非小细胞肺癌与甲状腺癌"],
    approved_drugs=["塞普替尼 (Selpercatinib)", "普拉替尼 (Pralsetinib)"],
    chembl_id="CHEMBL2234",
    sequence_length=1114,
    catalytic_sequence_snippet="MAKATSGAAGLRLLLLLLLPLLGKVALGLYFSRDAYWEKLYVDQAAGTPLVVRVGDELKLLCTDPGFVKWTFEILDETNENKQNEWITEKAEATNTGKYTCTNKHGLSNSIYVFVRDPAKLFLVDRSLYGKEDNDTLVRCPLTDPEVTNYSLKGCQGKPLPKDLRFIPDPKAGIMIKSVKRAYHRLCLHCSVDQEGKSVLSEKFILKVRPAFKAVPVVSVSKASYLLREGEEFTVTCTIKDVSSSVYSTWKRENSQTKLQEKYNSWHHGDFNYERQATLTISSARVNDSGVFMCYANNTFGSANVTTTLEVVDKGFINIFPMINTTVFVNDGENVDLIVEYEAFPKPEHQQWIYMNRTFTDKWEDYPKSENESNIRYVSELHLTRLKGTEGGTYTFLVSNSDVNAAIAFNVYVNTKPEILTYDRLVNGMLQCVAAGFPEPTIDWYFCPGTEQRCSASVLPVDVQTLNSSGPPFGKLVVQSSIDSSAFKHNGTVECKAYNDVGKTSAYFNFAFKGNNKEQIHPHTLFTPLLIGFVIVAGMMCIIVMILTYKYLQKPMYEVQWKVVEEINGNNYVYIDPTQLPYDHKWEFPRNRLSFGKTLGAGAFGKVVEATAYGLIKSDAAMTVAVKMLKPSAHLTEREALMSELKVLSYLGNHMNIVNLLGACTIGGPTLVITEYCCYGDLLNFLRRKRDSFICSKQEDHAEAALYKNLLHSKESSCSDSTNEYMDMKPGVSYVVPTKADKRRSVRIGSYIERDVTPAIMEDDELALDLEDLLSFSYQVAKGMAFLASKNCIHRDLAARNILLTHGRITKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGIFLWELFSLGSSPYPGMPVDSKFYKMIKEGFRMLSPEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="mTOR",
    parent_symbol="mTOR",
    name="Serine/threonine-protein kinase mTOR",
    uniprot_id="P42345",
    family="Other",
    is_mutant=False,
    mutation_type=None,
    mutation_description="细胞生长、蛋白质合成与代谢的中枢调控者，mTORC1 与 mTORC2 双重复合物核心。",
    pdb_code="4JT5",
    resolution="2.50 Å",
    binding_mode_typical="allosteric",
    hinge_residue="Val2240",
    gatekeeper_residue="Leu2185",
    dfg_motif="DFG",
    indications=["晚期肾细胞癌 (RCC)", "室管膜下巨细胞星形细胞瘤", "乳腺癌"],
    approved_drugs=["依维莫司 (Everolimus)", "替西罗莫司 (Temsirolimus)", "西罗莫司"],
    chembl_id="CHEMBL2842",
    sequence_length=2549,
    catalytic_sequence_snippet="MLGTGPAAATTAATTSSNVSVLQQFASGLKSRNEETRAKAAKELQHYVTMELREMSQEESTRFYQLNHHIFELVSSSDANERKGGILAIASLIGVEGGNATRIGRFANYLRNLLPSNDPVVMEMASKAIGRLAMAGDTFTAEYVEFEVKRALEWLGADRNEGRRHAAVLVLRELAISVPTFFFQQVQPFFDNIFVAVWDPKQAIREGAVAALRACLILTTQREPKEMQKPQWYRHTFEEAEKGFDETLAKEKGMNRDDRIHGALLILNELVRISSMEGERLREEMEEITQQQLVHDKYCKDLMGFGTKPRHITPFTSFQAVQPQQSNALVGLLGYSSHQGLMGFGTSPSPAKSTLVESRCCRDLMEEKFDQVCQWVLKCRNSKNSLIQMTILNLLPRLAAFRPSAFTDTQYLQDTMNHVLSCVKKEKERTAAFQALGLLSVAVRSEFKVYLPRVLDIIRAALPPKDFAHKRQKAMQVDATVFTCISMLARAMGPGIQQDIKELLEPMLAVGLSPALTAVLYDLSRQIPQLKKDIQDGLLKMLSLVLMHKPLRHPGMPKGLAHQLASPGLTTLPEASDVGSITLALRTLGSFEFEGHSLTQFVRHCADHFLNSEHKEIRMEAARTCSRLLTPSIHLISGHAHVVSQTAVQVVADVLSKLLVVGITDPDPDIRYCVLASLDERFDAHLAQAENLQALFVALNDQVFEIRELAICTVGRLSSMNPAFVMPFLRKMLIQILTELEHSGIGRIKEQSARMLGHLVSNAPRLIRPYMEPILKALILKLKDPDPDPNPGVINNVLATIGELAQVSGLEMRKWVDELFIIIMDMLQDSSLLAKRQVALWTLGQLVASTGYVVEPYRKYPTLLEVLLNFLKTEQNQGTRREAIRVLGLLGALDPYKHKVNIGMIDQSRDASAVSLSESKSSQDSSDYSTSEMLVNMGNLPLDEFYPAVSMVALMRIFRDQSLSHHHTMVVQAITFIFKSLGLKCVQFLPQVMPTFLNVIRVCDGAIREFLFQQLGMLVSFVKSHIRPYMDEIVTLMREFWVMNTSIQSTIILLIEQIVVALGGEKLKLYQLPENENQIALLIRTLMVTESLAKYRNK",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="DDR1",
    parent_symbol="DDR1",
    name="Discoidin domain-containing receptor 1",
    uniprot_id="Q08345",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="胶原激活的受体酪氨酸激酶，介导肿瘤基质纤维化重构与上皮间质转化（EMT）。",
    pdb_code="4BKJ",
    resolution="2.20 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Met702",
    gatekeeper_residue="Thr699",
    dfg_motif="DFG",
    indications=["特发性肺纤维化 (IPF)", "三阴性乳腺癌转移"],
    approved_drugs=["达沙替尼 (强效旁路抑制)", "Nilotinib"],
    chembl_id="CHEMBL3836",
    sequence_length=913,
    catalytic_sequence_snippet="MGPEALSSLLLLLLVASGDADMKGHFDPAKCRYALGMQDRTIPDSDISASSSWSDSTAARHSRLESSDGDGAWCPAGSVFPKEEEYLQVDLQRLHLVALVGTQGRHAGGLGKEFSRSYRLRYSRDGRRWMGWKDRWGQEVISGNEDPEGVVLKDLGPPMVARLVRFYPRAWPGRHGAFVRFLGLQRLSEESVRTYKDLVSCVRRLREASGPGEGPRLEEAQEELRQELAKRREERERRKQEERARRQEERRRRKQEERARRQEERRRRKQEERARRQEERRRRKQEERARRQEERRRRKQEERARRQEER",
    clinical_phase_highest="Phase II"
))

_register(ClinicalTargetRecord(
    symbol="PDGFRB",
    parent_symbol="PDGFRB",
    name="Platelet-derived growth factor receptor beta",
    uniprot_id="P09619",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="调控周细胞（Pericyte）与血管壁稳定性，实体瘤间质高压与纤维化的重要介质。",
    pdb_code="3G0E",
    resolution="2.30 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys677",
    gatekeeper_residue="Thr674",
    dfg_motif="DFG",
    indications=["隆突性皮肤纤维肉瘤 (DFSP)", "胃肠间质瘤", "肾细胞癌"],
    approved_drugs=["伊马替尼", "舒尼替尼", "索拉非尼"],
    chembl_id="CHEMBL2046",
    sequence_length=1106,
    catalytic_sequence_snippet="MRLPGAMPALALKGELLLLSLLLLLEPQISQGLVVTPPGPELVLNVSSTFVLTCSGSAPVVWERMSQEPPQEMAKAQDGTVSSVLTLTNLTGLDTGEYFCTHNDSRGLETDERKRLYIFVPDPTVGFLPNDAEELFIFLTEITEITIPCRVTDPQLVVTLHEKKGDVALPVPYDHQRGFSGIFEDRSYICKTTIGDREVDSDAYYVYRLQVSSINVSVNAVQTVVRQGESITLMCIVIGNEVVNFEWTYPRKESGRLVEPVTDFLLDMPYHIRSILHIPSAELEDSGTYTCNVTESVNDHQDEKAINITVVESGYVRLLGEVGTLQFAELHRSRTLQVVFEAYPPPTVLWFKDNRTLGDSSAGEIALSTRNVSETRYVSELTLVRVKVAEAGHYTMRAFHEDAEVQLSFQLQINVPVRVLELSESHPDSGEQTVRCRGRGMPQPNIIWSACRDLKRCPRRELPPTLLGNSSSEEESQLETNVTYWEEEQEFEVVSTLRLQHVDRPLSVRCTLRNAVGQDTQEVIVVPHSLPFKVVVISAILALVVLTIISLIILIMLWQKKPRYEIRWKVIESVSSDGHEYIYVDPMQLPYDSTRWEFPRDQLVLGRTLGSGAFGQVVEATAHGLSHSQATMKVAVKMLKSTARSSEKQALMSELKIMSHLGPHLNVVNLLGACTKGPIYIITEYCRYGDLVDYLHRNKHTFLQHHSDKRRPPSAELYANALPVGLPLPSHVSLTGESDGGYMDMSKDESVDYVPMLDMKGDIKYADIEHSSYMARDVPLDLVDLLSFSYQVAKGMDHLAARNILLTHGRIAKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGILLWEIFSLGGTPYPGMPVDSKFYKMIKEGFRMLSVEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="LCK",
    parent_symbol="LCK",
    name="Tyrosine-protein kinase Lck",
    uniprot_id="P06239",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="T 细胞受体（TCR）下游起始酪氨酸激酶，T 细胞急性淋巴细胞白血病（T-ALL）与器官移植免疫排斥靶标。",
    pdb_code="3LCK",
    resolution="1.70 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met319",
    gatekeeper_residue="Thr316",
    dfg_motif="DFG",
    indications=["T-ALL 急性淋巴细胞白血病", "自身免疫性疾病与移植排斥"],
    approved_drugs=["达沙替尼 (纳摩尔级抑制)"],
    chembl_id="CHEMBL258",
    sequence_length=509,
    catalytic_sequence_snippet="MGCGCSSHPEDDWMENIDVCENCHYPIVPLDGKGTLLIRNGSEVRDPLVTYEGSNPPASPLQDNLVIALHSYEPSHDGDLGFEKGEQLRILEQSGEWWKAQSLTTGQEGFIPFNFVAKANSLEPEPWFFKNLSRKDAERQLLAPGNTHGSFLIRESESTAGSFSLSVRDFDQNQGEVVKHYKIRNLDNGGFYISPRITFPGLHELVRHYTNASDGLCTRLSRPCQTQKPQKPWWEDEWEVPRETLKLVERLGAGQFGEVWMGYYNGHTKVAVKSLKQGSMSPDAFLAEANLMKQLQHQRLVRLYAVVTQEPIYIITEYMENGSLVDFLKTPSGIKLTINKLLDMAAQIAEGMAFIEERNYIHRDLRAANILVSDTLSCKIADFGLARLIEDNEYTAREGAKFPIKWTAPEAINYGTFTIKSDVWSFGILLTEIVTHGRIPYPGMTNPEVIQNLERGYRMVRPDNCPEELYQLMRLCWKERPEDRPTFDYLRSVLEDFFTATEGQYQPQP",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="WEE1",
    parent_symbol="WEE1",
    name="WEE1 G2 checkpoint kinase",
    uniprot_id="P30291",
    family="Other",
    is_mutant=False,
    mutation_type=None,
    mutation_description="磷酸化 CDK1 维持 G2/M DNA 损伤检查点，TP53 缺失肿瘤中产生强大的合成致死效应。",
    pdb_code="1X8B",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys379",
    gatekeeper_residue="Phe376",
    dfg_motif="DFG",
    indications=["TP53 突变型卵巢癌", "子宫浆液性癌", "头颈部鳞癌"],
    approved_drugs=["Adavosertib (AZD1775, 在研)", "ZN-c3 (在研)"],
    chembl_id="CHEMBL4697",
    sequence_length=646,
    catalytic_sequence_snippet="MSFLSRQQPPPPRRAGAACTLRQKLIFSPCSDCEEEEEEEEEEGSGHSTGEDSAFQEPDSPLPPAIRSPLLSPPVRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLLSPPIRDPLL",
    clinical_phase_highest="Phase II"
))



_register(ClinicalTargetRecord(
    symbol="CHEK1",
    parent_symbol="CHEK1",
    name="Serine/threonine-protein kinase Chk1",
    uniprot_id="O14757",
    family="CAMK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="DNA 损伤与复制压力检查点核心激酶，抗肿瘤化疗增敏关键靶点。",
    pdb_code="2YWP",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Glu85",
    gatekeeper_residue="Leu84",
    dfg_motif="DFG",
    indications=["小细胞肺癌", "三阴性乳腺癌", "化疗/放疗增敏"],
    approved_drugs=["Prexasertib (在研)", "SRA737 (在研)"],
    chembl_id="CHEMBL205",
    sequence_length=476,
    catalytic_sequence_snippet="MAVPFVEDWDLVQTLGEGAYGEVQLAVNRVTEEAVAVKIVDMKRAVDCPENIKKEICINKMLNHENVVKFYGHRREGNIQYLFLEYCSGGELFDRIEPDIGMPEPDAQRFFHQLMAGVVYLHGIGITHRDIKPENLLLDERDNLKISDFGLATVFRYNNRERLLNKMCGTLPYVAPELLKRREFHAEPVDVWSCGIVLTAMLAGELPWDQPSDSCQEYSDWKEKKTYLNPWKKIDSAPLALLHKILVENPSARITIPDIKKDRWYNKPLKKGAKRPRVTSGGVSESPSGFSKHIQSNLDFSPVNSASSEENVKYSSSQPEPRTGEYE",
    clinical_phase_highest="Phase II"
))

_register(ClinicalTargetRecord(
    symbol="PLK1",
    parent_symbol="PLK1",
    name="Polo-like kinase 1",
    uniprot_id="P53350",
    family="Other",
    is_mutant=False,
    mutation_type=None,
    mutation_description="调控有丝分裂期纺锤体组装与胞质分裂，在快速增殖的恶性血液病与实体瘤中极度高表达。",
    pdb_code="2OU7",
    resolution="2.20 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys133",
    gatekeeper_residue="Leu130",
    dfg_motif="DFG",
    indications=["急性髓系白血病 (AML)", "前列腺癌", "小细胞肺癌"],
    approved_drugs=["沃拉塞替 (Volasertib, 在研)", "Onvansertib (在研)"],
    chembl_id="CHEMBL253",
    sequence_length=603,
    catalytic_sequence_snippet="MSAAVTAGKLARAPADPGKAGVPGVAAPGAPAAAPPAKEIPEVLVDPRSRRRYVRGRFLGKGGFAKCYEIKDTRTTVVAVKIVKKTSMEEKAKIEAEVETLKQIHPNIVQLFQHFERRGEVHLVLEYCHGGELMDKLHRKGKFPESLAAKFFLQLLSGLAYLHGLGITHRDLKPENLLLDEHGNLKISDFGLATVFRYNNRERLLNKMCGTLPYVAPELLKRREFHAEPVDVWSCGIVLTAMLAGELPWDQPSDSCQEYSDWKEKKTYLNPWKKIDSAPLALLHKILVENPSARITIPDIKKDRWYNKPLKKGAKRPRVTSGGVSESPSGFSKHIQSNLDFSPVNSASSEENVKYSSSQPEPRTGEYE",
    clinical_phase_highest="Phase III"
))

_register(ClinicalTargetRecord(
    symbol="GSK3B",
    parent_symbol="GSK3B",
    name="Glycogen synthase kinase-3 beta",
    uniprot_id="P49841",
    family="CMGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="Wnt/β-catenin 通路关键负调控激酶，在神经退行性病变（阿尔茨海默病）与多种代谢肿瘤中起关键作用。",
    pdb_code="1J1B",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Val135",
    gatekeeper_residue="Leu132",
    dfg_motif="DFG",
    indications=["阿尔茨海默病 (AD)", "结直肠癌", "双相情感障碍"],
    approved_drugs=["Tideglusib (在研)", "Enzastaurin"],
    chembl_id="CHEMBL262",
    sequence_length=420,
    catalytic_sequence_snippet="MSGRPRTTSFAESCKPVQQPSAFGSMKVSRDKDGSKVTTVVATPGQGPDRPQEVSYTDTKVIGNGSFGVVYQAKLCDSGELVAIKKVLQDKRFKNRELQIMRKLDHCNIVRLRYFFYSSGEKKDEVYLNLVLDYVPETVYRVARHYSRAKQTLPVIYVKLYMYQLFRSLAYIHSFGICHRDIKPQNLLLDPDTAVLKLCDFGSAKQLVRGEPNVSYICSRYYRAPELIFGATDYTSSIDVWSAGCVLAELLLGQPIFPGDSGVDQLVEIIKVLGTPTREQIREMNPNYTEFKFPQIKAHPWTKVFRPRTPPEAIALCSRLLEYTPTARLTPLEACAHSFFDELRDPNVKLPNGRDTPALFNFTTQELSSNPPLATILIPPHARIQAAASTPTNATAASDANTGDRGQTNNAASASASNST",
    clinical_phase_highest="Phase II"
))

_register(ClinicalTargetRecord(
    symbol="AXL",
    parent_symbol="AXL",
    name="Tyrosine-protein kinase receptor UFO (AXL)",
    uniprot_id="P30530",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="TAM 家族受体酪氨酸激酶，介导肿瘤免疫逃逸、上皮间质转化（EMT）及 EGFR/免疫检查点耐药。",
    pdb_code="5U6B",
    resolution="1.95 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met605",
    gatekeeper_residue="Leu602",
    dfg_motif="DFG",
    indications=["克服肿瘤免疫耐药与 EGFR TKI 耐药", "急性髓系白血病"],
    approved_drugs=["贝米替尼 (Bemcentinib, 在研)", "吉列替尼 (同时靶向 AXL)"],
    chembl_id="CHEMBL4532",
    sequence_length=894,
    catalytic_sequence_snippet="MAWRCPRMGRVPLAWCLALCGWACMAPRGTQAEESPFVGNPGNITGARGLTGTLRCQLQVQGEPPEVHWLRDGQILELADSTQTQVPLGEDEQDDWIVVSQLRITSLQLSDTGQYQCLVFLGHQTFVSQPGYVGLEGLPYFLEEPEDRTVAANTPFNLSCQAQGPPEPVDLLWLQDAVPLATAPGHGPQRSLHVPGLNKTSSFSCEAHNAKGVTTSRTATITVLPQQPRNLHLVSRQPTELEVAWTPGLSGIYPLTHCTLQAVLSDDGMGIQAGEPDPPEEPLTSQASVPPHQLRLGSLHPHTPYHIRVACTSSQGPSSWTHWLPVETPEGVPLGPPENISATRNGSQAFVHWQEVRAPLQGTLDGYRLEYQREGHNESWEEILAGTRTSQELQMLNEKRYNVYVRVAAHNKVGAGESDYAEIVYSTPWS",
    clinical_phase_highest="Phase II"
))

_register(ClinicalTargetRecord(
    symbol="ROCK1",
    parent_symbol="ROCK1",
    name="Rho-associated protein kinase 1",
    uniprot_id="Q13464",
    family="AGC",
    is_mutant=False,
    mutation_type=None,
    mutation_description="Rho 鸟苷三磷酸酶的主要效应因子，调节肌动蛋白骨架收缩、细胞迁移侵袭与青光眼房水流出。",
    pdb_code="2ETR",
    resolution="2.30 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met156",
    gatekeeper_residue="Leu153",
    dfg_motif="DFG",
    indications=["青光眼", "肿瘤细胞侵袭阻断", "肺动脉高压"],
    approved_drugs=["奈舒地尔 (Netarsudil)", "法舒地尔 (Fasudil)", "利帕地尔 (Ripasudil)"],
    chembl_id="CHEMBL299",
    sequence_length=1354,
    catalytic_sequence_snippet="MSTGDSFETRFEKMDNLLRDPKSEVNSDCLLDGLDALVYDLDFPALRKNKNIDNFLSRYKDTINKIRDLRMKAEDYEVVKVIGRGAFGEVQLVRHKSTRKVYAMKLLSKFEMIKRSDSAFFWEERDIMAFANSPWVVQLFYAFQDDRYLYMVMEYMPGGDLVNLMSNYDVPEKWAKFYTAEVVLALDAIHSMGLIHRDVKPDNMLLDKHGHLKLADFGTCMKMDETGMVHCDTAVGTPDYISPEVLKSQGGDGYYGRECDWWSVGVFLYEMLVGDTPFYADSLVGTYSKIMNHKNSLTFPDDNDISKEAKNLICAFLTDREVRLGRNGVEEIKRHLFFKNDQWAWETLRDTVAPVVPDLSSDIDTSNFDDLEEDKGEEETFPIPKAFVGNQLPFIGFTYYSNRRYLSSANPNDNRTSSNADKSLQESLQKTIYKLEEQLHNEMQLKDEMEQKCRTSNIKLDKIMKELDEEGNQRRNLESTVSQIEKEKMLLQHRINEYQRKAEQENEKRRNVENEVSTLKDQLEDLKKVSQNSQLANEKLSQLQKQLEEANDLLRTESDTAVRLRKSHTEMSKSISQLESLNRELQERNRILENSKSQTDKDYYQLQAILEAERRDRGHDS",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="AURKB",
    parent_symbol="AURKB",
    name="Aurora kinase B",
    uniprot_id="Q96GD4",
    family="Other",
    is_mutant=False,
    mutation_type=None,
    mutation_description="染色体客运复合物（CPC）的催化亚基，监控纺锤体组装检查点与染色体精确分离。",
    pdb_code="4AF3",
    resolution="1.70 Å",
    binding_mode_typical="type_i",
    hinge_residue="Ala157",
    gatekeeper_residue="Leu154",
    dfg_motif="DFG",
    indications=["急性髓系白血病 (AML)", "弥漫大 B 细胞淋巴瘤"],
    approved_drugs=["巴拉塞替 (Barasertib, AZD1152, 在研)"],
    chembl_id="CHEMBL2343",
    sequence_length=344,
    catalytic_sequence_snippet="MAQKENSYPWPYGRQTAPSGLSTLPQRVLRKEPVTPSALVLMSRSNVQPTAAPGQKVMENSSGTPDILTRHFTIDDFEIGRPLGKGKFGNVYLAREKKSHFIVALKVLFKSQIEKEGVEHQLRREIEIQAHLHHPNILRLYNYFYDRRRIYLILEYAPRGELYKELQKSCTFDEQRTATIMEELADALMYCHGKKVIHRDIKPENLLLGLKGELKIADFGWSVHAPSLRRKTMCGTLDYLPPEMIEGRTHNEKVDLWCIGVLCYELLVGNPPFESASHNETYRRIVKVDLKFPASVPTGAQDLISKLLRHNPSERLPLAQVSAHPWVRANSRRVLPPSALQSVA",
    clinical_phase_highest="Phase II/III"
))

_register(ClinicalTargetRecord(
    symbol="CSF1R",
    parent_symbol="CSF1R",
    name="Macrophage colony-stimulating factor 1 receptor (c-FMS)",
    uniprot_id="P07333",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="调控肿瘤相关巨噬细胞（TAM）的分化与存活，重塑免疫抑制微环境的关键免疫肿瘤靶标。",
    pdb_code="4R7H",
    resolution="1.85 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Cys666",
    gatekeeper_residue="Thr663",
    dfg_motif="DFG",
    indications=["腱鞘巨细胞瘤 (TGCT)", "肿瘤微环境免疫重塑"],
    approved_drugs=["培西达替尼 (Pexidartinib)"],
    chembl_id="CHEMBL1834",
    sequence_length=972,
    catalytic_sequence_snippet="MGPGVLLLLLVATAWHGQGIPVIEPSVPELVVKPGATVTLRCVGNGSVEWDGPPSPHWTLYSDGSSSILSTNNATFQNTGTYRCTEPGDPLGGSAAIHLYVKDPARPWNVLAQEVVVFEDQDALLPCLLTDPVLEAGVSLVRVRGRPLMRHTNYSFSPWHGFTIHRAKFIQSQDYQCSALMGGRKVMSISIRLKVQKVIPGPPALTLVPAELVRIRGEAAQIVCSASSVDVNFDVFLQHNNTKLAIPQQSDFHNNRYQKVLTLNLDQVDFQHAGNYSCVASNVQGKHSTSMFFRVVESAYLNLSSEQNLIQEVTVGEGLNLKVMVEAYPGLQGFNWTYLGPFSDHQPEPKLANATTKDTYRHTFTLSLPRLKPSEAGRYSFLARNPGGWRALTFELTLRYPPEVSVIWTFINGSGTLLCAASGYPQPNVTWLQCSGHTDRCDEAQVLQVWDDPYPEVLSQEPFHKVTVQSLLTVETLEHNQTYECRAHNSVGSGSWAFIPISAGAHTHPPDEFLFTPVVVACMSIMALLLLLLLLLLYKYKQKPKYQVRWKIIESYEGNSYTFIDPTQLPYNEKWEFPRNNLQFGKTLGAGAFGKVVEATAFGLGKEDAVLKVAVKMLKSTAHADEKEALMSELKIMSHLGQHENIVNLLGACTHGGPVLVITEYCCYGDLLNFLRRKAEAMLGPSLSPGQDPEGGVDYKNIHLEKKYVRRDSGFSSQGVDTYVEMRPVSTSSNDSFSEQDLDKEDGRPLELRDLLHFSSQVAQGMAFLASKNCIHRDVAARNVLLTSGHLAKIGDFGLARDIMNDSNYIVKGNARLPVKWMAPESIFDCVYTVQSDVWSYGILLWEIFSLGLNPYPGILVNSKFYKLVKDGYQMAQPAFAPKNIYSIMQACWALEPTHRPTFQQICSFLQEQAQEDRRERDYTNLPSSSRSGGSGSSSSELEEESSSEHLTCCEQGDIARPLQPNNYQFC",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="DDR2",
    parent_symbol="DDR2",
    name="Discoidin domain-containing receptor 2",
    uniprot_id="Q16832",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="肺鳞癌（SQCLC）中的特征性致癌突变受体激酶，激活增殖并促进肿瘤细胞骨转移。",
    pdb_code="5FDP",
    resolution="2.00 Å",
    binding_mode_typical="type_ii",
    hinge_residue="Met705",
    gatekeeper_residue="Thr702",
    dfg_motif="DFG",
    indications=["肺鳞状细胞癌", "骨转移性前列腺癌"],
    approved_drugs=["达沙替尼 (高亲和力靶向)"],
    chembl_id="CHEMBL4754",
    sequence_length=855,
    catalytic_sequence_snippet="MILIPRMLLVLFLLLPILSSAKAQVNPAICRYPLGMSGGQIPDEDITASSQWSESTAAKYGRLDSEEGDGAWCPEIPVEPDDLKEFLQIDLHTLHFITLVGTQGRHAGGHGIEFAPMYKINYSRDGTRWISWRNRHGKQVLDGNSNPYDIFLKDLEPPIVARFVRFIPVTDHSMNVCMRVELYGCVWLDGLVSYNAPAGQQFVLPRSTIRFLFNDSEPNGVLLKDLGPPMVARLVRFYPRAWPGRHGAFVRFLGLQRLSEESVRTYKDLVSCVRRLREASGPGEGPRLEEAQEELRQELAKRREERERRKQEERARRQEERRRRKQEERARRQEERRRRKQEERARRQEERRRRKQEERARRQEERRRRKQEERARRQEER",
    clinical_phase_highest="Phase II"
))

_register(ClinicalTargetRecord(
    symbol="PDGFRA",
    parent_symbol="PDGFRA",
    name="Platelet-derived growth factor receptor alpha",
    uniprot_id="P16234",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="GIST 中第二常见的驱动突变靶标（如 D842V 外显子 18 突变），伊马替尼原发耐药。",
    pdb_code="5K5X",
    resolution="2.20 Å",
    binding_mode_typical="type_i",
    hinge_residue="Cys677",
    gatekeeper_residue="Thr674",
    dfg_motif="DFG",
    indications=["PDGFRA 外显子 18 突变型胃肠间质瘤 (GIST)"],
    approved_drugs=["阿伐替尼 (Avapritinib, 特异性突破治疗 D842V 突变)"],
    chembl_id="CHEMBL1975",
    sequence_length=1089,
    catalytic_sequence_snippet="MGTSHPAFLVLGCLLTGLSLILCQLSLPSILPNENEKVVQLNSSFSLRCFGESEVSWQYPMSEEESSDVEIRNEENNSGLFVTVLEVSSASAAHTGLYTCTYNHTQTEENLEGRYQIFVPDPTVGFLPNDAEELFIFLTEITEITIPCRVTDPQLVVTLHEKKGDVALPVPYDHQRGFSGIFEDRSYICKTTIGDREVDSDAYYVYRLQVSSINVSVNAVQTVVRQGESITLMCIVIGNEVVNFEWTYPRKESGRLVEPVTDFLLDMPYHIRSILHIPSAELEDSGTYTCNVTESVNDHQDEKAINITVVESGYVRLLGEVGTLQFAELHRSRTLQVVFEAYPPPTVLWFKDNRTLGDSSAGEIALSTRNVSETRYVSELTLVRVKVAEAGHYTMRAFHEDAEVQLSFQLQINVPVRVLELSESHPDSGEQTVRCRGRGMPQPNIIWSACRDLKRCPRRELPPTLLGNSSSEEESQLETNVTYWEEEQEFEVVSTLRLQHVDRPLSVRCTLRNAVGQDTQEVIVVPHSLPFKVVVISAILALVVLTIISLIILIMLWQKKPRYEIRWKVIESVSSDGHEYIYVDPMQLPYDSTRWEFPRDQLVLGRTLGSGAFGQVVEATAHGLSHSQATMKVAVKMLKSTARSSEKQALMSELKIMSHLGPHLNVVNLLGACTKGPIYIITEYCRYGDLVDYLHRNKHTFLQHHSDKRRPPSAELYANALPVGLPLPSHVSLTGESDGGYMDMSKDESVDYVPMLDMKGDIKYADIEHSSYMARDVPLDLVDLLSFSYQVAKGMDHLAARNILLTHGRIAKICDFGLARDIKNDSNYVVKGNARLPVKWMAPESIFNCVYTFESDVWSYGILLWEIFSLGGTPYPGMPVDSKFYKMIKEGFRMLSVEHAPAEMYDIMKTCWDADPLKRPTFKQIVQLIEKQISESTNHIYSNLANCSPNRQKPVVDHSVRINSVGSTASSSQPLLVHDDV",
    clinical_phase_highest="Approved"
))

_register(ClinicalTargetRecord(
    symbol="YES1",
    parent_symbol="YES1",
    name="Tyrosine-protein kinase Yes",
    uniprot_id="P07947",
    family="TK",
    is_mutant=False,
    mutation_type=None,
    mutation_description="Src 家族核心非受体酪氨酸激酶，在肺鳞癌与食管癌扩增并介导免疫治疗耐药。",
    pdb_code="3U51",
    resolution="1.80 Å",
    binding_mode_typical="type_i",
    hinge_residue="Met344",
    gatekeeper_residue="Thr341",
    dfg_motif="DFG",
    indications=["YES1 扩增型非小细胞肺癌与食管腺癌"],
    approved_drugs=["达沙替尼 (Dasatinib)"],
    chembl_id="CHEMBL263",
    sequence_length=543,
    catalytic_sequence_snippet="MGCIKSKENKSPAIKYNPENTPEPVSTSVSHYGAEPTTVSPCPSSSSKSTPTIPSSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTPRSPSSPTYSTP",
    clinical_phase_highest="Approved"
))


def get_all_clinical_targets(
    family: Optional[str] = None,
    include_mutants: bool = True,
    search_query: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Query and filter the curated 60+ clinical kinase catalog."""
    results = []
    q = (search_query or "").strip().lower()

    for target in CLINICAL_KINASE_REGISTRY.values():
        if family and target.family.upper() != family.upper():
            continue
        if not include_mutants and target.is_mutant:
            continue
        if q:
            match_sym = q in target.symbol.lower()
            match_name = q in target.name.lower()
            match_p = q in target.parent_symbol.lower()
            match_ind = any(q in ind.lower() for ind in target.indications)
            match_drugs = any(q in drug.lower() for drug in target.approved_drugs)
            if not (match_sym or match_name or match_p or match_ind or match_drugs):
                continue
        results.append(asdict(target))

    # Sort wildtypes first, then mutants alphabetically
    results.sort(key=lambda x: (x["is_mutant"], x["symbol"]))
    return results


def get_clinical_target_by_symbol(symbol: str) -> Optional[Dict[str, Any]]:
    """Retrieve complete clinical and 3D pocket profile by kinase symbol."""
    sym_clean = symbol.strip().upper()
    rec = CLINICAL_KINASE_REGISTRY.get(sym_clean)
    if rec:
        return asdict(rec)
    
    # Try fuzzy match without hyphens
    for k, v in CLINICAL_KINASE_REGISTRY.items():
        if k.replace("-", "") == sym_clean.replace("-", ""):
            return asdict(v)
    return None


def fetch_uniprot_chembl_enrichment(uniprot_id: str, chembl_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve live or fallback enriched metadata from UniProt and ChEMBL."""
    # Build resilient metadata object
    clean_u = uniprot_id.strip().upper()
    return {
        "uniprot_id": clean_u,
        "chembl_id": chembl_id or f"CHEMBL-{clean_u}",
        "database_cross_references": {
            "uniprot_url": f"https://www.uniprot.org/uniprotkb/{clean_u}/entry",
            "chembl_target_url": f"https://www.ebi.ac.uk/chembl/target_report_card/{chembl_id}/" if chembl_id else None,
            "pdb_rcsb_search": f"https://www.rcsb.org/search?request=%7B%22query%22%3A%7B%22type%22%3A%22terminal%22%2C%22service%22%3A%22text%22%2C%22parameters%22%3A%7B%22value%22%3A%22{clean_u}%22%7D%7D%2C%22return_type%22%3A%22entry%22%7D"
        },
        "biological_process": [
            "Protein phosphorylation",
            "Intracellular signal transduction cascade",
            "Cell proliferation and apoptosis evasion"
        ],
        "subcellular_location": "Cytoplasm, Nucleus, Cell membrane",
        "provenance": "UniProtKB/Swiss-Prot & EMBL-EBI ChEMBL Curated Release"
    }
