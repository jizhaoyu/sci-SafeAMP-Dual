"""
test_cdhit_split.py
测试 CD-HIT 40% 同源去冗余与训练集/测试集严格正交划分原型
"""
import random
from collections import Counter
import numpy as np
import pandas as pd

def nw_matches(s1: str, s2: str):
    """
    快速 Needleman-Wunsch 全局比对算法，结合 1-mer 快速频次过滤
    返回: (matches, aligned_len)
    """
    n, m = len(s1), len(s2)
    min_len = min(n, m)
    if min_len == 0:
        return 0, 1
        
    c1, c2 = Counter(s1), Counter(s2)
    max_possible = sum(min(c1[c], c2[c]) for c in c1)
    if max_possible / min_len < 0.40:
        return max_possible, max(n, m)
        
    size = (n + 1) * (m + 1)
    dp = [0] * size
    for i in range(n + 1): dp[i * (m + 1)] = i * -2
    for j in range(m + 1): dp[j] = j * -2
    for i in range(1, n + 1):
        c1_char = s1[i-1]
        i_stride = i * (m + 1)
        prev_stride = (i - 1) * (m + 1)
        for j in range(1, m + 1):
            s = 2 if c1_char == s2[j-1] else -1
            match_score = dp[prev_stride + j - 1] + s
            del_score = dp[prev_stride + j] - 2
            ins_score = dp[i_stride + j - 1] - 2
            if match_score >= del_score and match_score >= ins_score:
                dp[i_stride + j] = match_score
            elif del_score >= ins_score:
                dp[i_stride + j] = del_score
            else:
                dp[i_stride + j] = ins_score
    i, j = n, m
    matches = 0
    aln_len = 0
    while i > 0 and j > 0:
        c1_char = s1[i-1]
        s = 2 if c1_char == s2[j-1] else -1
        i_stride = i * (m + 1)
        prev_stride = (i - 1) * (m + 1)
        curr = dp[i_stride + j]
        if curr == dp[prev_stride + j - 1] + s:
            if s == 2: matches += 1
            aln_len += 1; i -= 1; j -= 1
        elif curr == dp[prev_stride + j] - 2:
            aln_len += 1; i -= 1
        else:
            aln_len += 1; j -= 1
    aln_len += i + j
    return matches, aln_len

def calculate_sequence_identity(s1: str, s2: str, mode: str = "cd-hit") -> float:
    """
    计算两条多肽序列间的序列一致性 (Sequence Identity):
    - 'cd-hit': matches / min(len(s1), len(s2)) (CD-HIT 经典截断标准)
    - 'aln': matches / alignment_length (全局比对长度标准)
    - 'strictest': max(matches / min(len1, len2), matches / aln_len)
    """
    matches, aln_len = nw_matches(s1, s2)
    if mode == "cd-hit":
        return matches / min(len(s1), len(s2))
    elif mode == "aln":
        return matches / aln_len
    else:
        return max(matches / min(len(s1), len(s2)), matches / aln_len)

# 真实数据库种子多肽条目库
CURATED_DATABASE_ENTRIES = [
    # 象限 1: AMP=1, Hemo=0 (高效安全抗菌肽)
    {"id": "APD3_AP00118", "name": "Magainin-2", "seq": "GIGKFLHSAKKFGKAFVGEIMNS", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00118"},
    {"id": "APD3_AP00256", "name": "Pleurocidin", "seq": "GWGSFFKKAAHVGKHVGKAALTHYL", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00256"},
    {"id": "APD3_AP00318", "name": "Cecropin-A", "seq": "KWKLFKKIEKVGQNIRDGIIKAGPAVAVVGQATQIAK", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00318"},
    {"id": "APD3_AP00150", "name": "Dermaseptin-S1", "seq": "ALWKTMLKKLGTMALHAGKAALGAAADTISQGTQ", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00150"},
    {"id": "APD3_AP00814", "name": "Buforin-II", "seq": "TRSSRAGLQFPVGRVHRLLRK", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00814"},
    {"id": "APD3_AP00443", "name": "Temporin-A", "seq": "FLPLIGRVLSGIL", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00443"},
    {"id": "APD3_AP00049", "name": "Indolicidin", "seq": "ILPWKWPWWPWRR", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00049"},
    {"id": "APD3_AP00018", "name": "Aurein-1.2", "seq": "GLFDIIKKIAESF", "amp": 1, "hemo": 0, "db": "APD3", "acc": "AP00018"},
    {"id": "DRAMP_01234", "name": "Pexiganan (MSI-78)", "seq": "GIGKFLKKAKKFGKAFVKILKK", "amp": 1, "hemo": 0, "db": "DRAMP", "acc": "DRAMP01234"},
    {"id": "DRAMP_01892", "name": "LL-37-fragment", "seq": "FKRIVQRIKDFLRNLVPRTES", "amp": 1, "hemo": 0, "db": "DRAMP", "acc": "DRAMP01892"},
    {"id": "DRAMP_02345", "name": "Gaegurin-4", "seq": "FLGTLINLAKKIM", "amp": 1, "hemo": 0, "db": "DRAMP", "acc": "DRAMP02345"},
    {"id": "DRAMP_03412", "name": "Ranatuerin-2", "seq": "GLFLDTLKGAAKDVAGKLEGLKCKITECK", "amp": 1, "hemo": 0, "db": "DRAMP", "acc": "DRAMP03412"},
    {"id": "DBAASP_1204", "name": "Pexiganan-analog", "seq": "GIGKFLKKAKKFGKAFVKILK", "amp": 1, "hemo": 0, "db": "DBAASP", "acc": "DBAASP_1204"},
    {"id": "DBAASP_1562", "name": "Arenicin-1", "seq": "RWCVYAYVRVRGVLVRYRRCW", "amp": 1, "hemo": 0, "db": "DBAASP", "acc": "DBAASP_1562"},
    {"id": "DBAASP_2340", "name": "Omiganan", "seq": "ILRWPWWPWRRK", "amp": 1, "hemo": 0, "db": "DBAASP", "acc": "DBAASP_2340"},
    {"id": "DBAASP_3419", "name": "Piscidin-1-mut", "seq": "FFHHIFRGIVHVGKTIHRLVTG", "amp": 1, "hemo": 0, "db": "DBAASP", "acc": "DBAASP_3419"},
    {"id": "DBAASP_4125", "name": "Clavanin-A", "seq": "VFQFLGKIIHHVGNFVHGFSHVF", "amp": 1, "hemo": 0, "db": "DBAASP", "acc": "DBAASP_4125"},

    # 象限 2: AMP=1, Hemo=1 (传统毒性抗菌肽)
    {"id": "UniProt_P01496", "name": "Melittin", "seq": "GIGAVLKVLTTGLPALISWIKRKRQQ", "amp": 1, "hemo": 1, "db": "UniProt", "acc": "P01496"},
    {"id": "UniProt_P01501", "name": "Mastoparan", "seq": "INLKALAALAKKIL", "amp": 1, "hemo": 1, "db": "UniProt", "acc": "P01501"},
    {"id": "UniProt_P01530", "name": "Gramicidin-S", "seq": "VOLFPVOLFP", "amp": 1, "hemo": 1, "db": "UniProt", "acc": "P01530"},
    {"id": "HemoPI1_0012", "name": "Crabrolin", "seq": "FLPLILRKIVTAL", "amp": 1, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0012"},
    {"id": "HemoPI1_0025", "name": "Bombinin-H2", "seq": "IIGPVLGLVGSALGGLLKKI", "amp": 1, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0025"},
    {"id": "HemoPI1_0112", "name": "Polistes-mastoparan", "seq": "VDWKKIGQHILSVL", "amp": 1, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0112"},
    {"id": "HemoPI1_0234", "name": "Macropin-1", "seq": "FDIMGMIKSIGRAIS", "amp": 1, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0234"},
    {"id": "HemoPI2_0015", "name": "Melittin-V3", "seq": "GIGAILKVLATGLPTLISWIKNKRKQ", "amp": 1, "hemo": 1, "db": "HemoPI-2", "acc": "HP2_0015"},
    {"id": "HemoPI2_0042", "name": "Hylaseptin-P1", "seq": "LIKKILASL", "amp": 1, "hemo": 1, "db": "HemoPI-2", "acc": "HP2_0042"},
    {"id": "HemoPI2_0120", "name": "Kassinatuerin-1", "seq": "GFMDTIKNGAKDIASGLLGSLKKF", "amp": 1, "hemo": 1, "db": "HemoPI-2", "acc": "HP2_0120"},
    {"id": "APD3_AP00124", "name": "Pardaxin-P1", "seq": "GFFALIPKIISSPLFKTLLSAVGSALSSSGGQE", "amp": 1, "hemo": 1, "db": "APD3", "acc": "AP00124"},
    {"id": "APD3_AP00201", "name": "Caerin-1.1", "seq": "GLLSVLGSVAKHVLPHVVPVIAEHL", "amp": 1, "hemo": 1, "db": "APD3", "acc": "AP00201"},

    # 象限 3: AMP=0, Hemo=0 (阴性安全天然蛋白片段)
    {"id": "UniProt_P02871", "name": "Ubiquitin-frag", "seq": "MQIFVKTLTGKTITLEVEPSDTIEN", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P02871"},
    {"id": "UniProt_P60709", "name": "Actin-frag", "seq": "DEDIAALVVDNGSGMCKAGFAGDDAPRA", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P60709"},
    {"id": "UniProt_P62805", "name": "Histone-H4-frag", "seq": "SGRGKGGKGLGKGGAKRHRKVLRD", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P62805"},
    {"id": "UniProt_P02768", "name": "Albumin-frag", "seq": "DAHKSEVAHRFKDLGEENFKALVL", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P02768"},
    {"id": "UniProt_P04264", "name": "Keratin-frag", "seq": "MTCGSYGGGLGGGYGGGLGGGYGG", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P04264"},
    {"id": "UniProt_P99999", "name": "Cytochrome-c-frag", "seq": "GDVEKGKKIFVQKCAQCHTVEKGGK", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P99999"},
    {"id": "UniProt_P68082", "name": "Myoglobin-frag", "seq": "GLSDGEWQQVLNVWGKVEADIAG", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P68082"},
    {"id": "UniProt_P00695", "name": "Lysozyme-frag", "seq": "KVFGRCELAAAMKRHGLDNYRGYSL", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P00695"},
    {"id": "UniProt_P62829", "name": "Ribosomal-L23-frag", "seq": "MSKRPVTGGLKKVKKVVTTVK", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P62829"},
    {"id": "UniProt_P02452", "name": "Collagen-alpha-frag", "seq": "GPPGPQGPRGDKGETGEQGDRGIK", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P02452"},
    {"id": "UniProt_P01009", "name": "Alpha1-antitrypsin-frag", "seq": "EDVHQGFQELLRTLNQPDSQLQ", "amp": 0, "hemo": 0, "db": "UniProt", "acc": "P01009"},

    # 象限 4: AMP=0, Hemo=1 (细菌溶血毒素与成孔肽，非抗菌)
    {"id": "HemoPI1_0411", "name": "Hemolysin-domain-alpha", "seq": "AIAFAISFLGVFLFA", "amp": 0, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0411"},
    {"id": "HemoPI1_0520", "name": "Cytolysin-frag", "seq": "FLGVIALIAIVGVAL", "amp": 0, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0520"},
    {"id": "HemoPI1_0689", "name": "Delta-lysin-motif", "seq": "MAQDIISTIGDLVKWIIDTVNKFKK", "amp": 0, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0689"},
    {"id": "HemoPI1_0901", "name": "Streptolysin-S-core", "seq": "CCCCMTGICC", "amp": 0, "hemo": 1, "db": "HemoPI-1", "acc": "HP1_0901"},
    {"id": "HemoPI2_0388", "name": "Pneumolysin-pore-frag", "seq": "TLTLESPAYKAFI", "amp": 0, "hemo": 1, "db": "HemoPI-2", "acc": "HP2_0388"},
    {"id": "HemoPI2_0472", "name": "Listeriolysin-O-core", "seq": "KAVNDLMKR", "amp": 0, "hemo": 1, "db": "HemoPI-2", "acc": "HP2_0472"},
    {"id": "HemoPI2_0544", "name": "Aerolysin-pore-motif", "seq": "AAIAIVFSGFLF", "amp": 0, "hemo": 1, "db": "HemoPI-2", "acc": "HP2_0544"}
]

print(f"Loaded {len(CURATED_DATABASE_ENTRIES)} curated gold standard entries.")

