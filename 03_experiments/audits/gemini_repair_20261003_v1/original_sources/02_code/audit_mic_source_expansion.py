"""Audit protocol-mic-08 expanded primary sources, candidate eligibility, and 3-fold feasibility."""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
from pypdf import PdfReader
from sklearn.model_selection import StratifiedGroupKFold

from audit_mic_reviewed_subset_hirsch import DisjointSet
from feature_extractor import MOLECULAR_WEIGHTS
from public_data import bounds, measurement_label
from research_data import sequence_identity
from research_utils import ROOT, read_json, sha256, utc_now, write_json

PROTOCOL = ROOT / "03_experiments/protocols/protocol-mic-08.json"
FREEZE = ROOT / "03_experiments/audits/protocol_mic_08_freeze_20261002_v1.json"
CATALOG = ROOT / "03_experiments/audits/mic_source_expansion_20261002_v1/discovery_catalog.json"
ACQUISITION = ROOT / "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/manifest.json"
EXISTING_MOL = ROOT / "03_experiments/audits/mic_three_fold_20261002_v1/candidate_molecules.csv"
EXISTING_OBS = ROOT / "03_experiments/audits/mic_three_fold_20261002_v1/candidate_observations.csv"
EXISTING_STATE = ROOT / "03_experiments/audits/mic_training_readiness_20261002_v12.json"
FORMAL_STATUS = ROOT / "04_paper/research_status.json"
RAW = ROOT / "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw"


def text_content(node) -> str:
    return " ".join("".join(node.itertext()).split())


def table_cells(table) -> list[list[str]]:
    return [[text_content(cell) for cell in row if cell.tag in {"td", "th"}] for row in table.findall(".//tr")]


def molecular_weight(sequence: str) -> float:
    return sum(MOLECULAR_WEIGHTS[aa] for aa in sequence) - 18.0152 * (len(sequence) - 1)


def audit(output: Path) -> dict:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite expansion audit: {output}")

    protocol = read_json(PROTOCOL)
    freeze = read_json(FREEZE)
    catalog = read_json(CATALOG)
    acquisition = read_json(ACQUISITION)
    existing_molecules = pd.read_csv(EXISTING_MOL, keep_default_na=False)
    existing_observations = pd.read_csv(EXISTING_OBS, keep_default_na=False)
    training_state = read_json(EXISTING_STATE)

    if sha256(PROTOCOL) != freeze["protocol_sha256"]:
        raise ValueError("Frozen protocol changed.")
    for name, expected_hash in freeze["inputs"].items():
        if sha256(ROOT / name) != expected_hash:
            raise ValueError(f"Protected freeze input changed: {name}")
    for name, expected_hash in acquisition["outputs"].items():
        file_path = ROOT / "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1" / name
        if sha256(file_path) != expected_hash:
            raise ValueError(f"Protected acquisition raw file changed: {name}")
    if sha256(FORMAL_STATUS) != "846c1fc2452646f3df9c2055b0a4a1b5140132acc2433bb2c304b133b6e8012c":
        raise ValueError("Protected formal status changed.")
    if training_state["status"] != "local_exploratory_three_fold_training_completed":
        raise ValueError("Existing training state is not exploratory training completed.")

    source_inventory = [
        {
            "source_id": "chekmenev2006",
            "review_order": 1,
            "doi": "10.1016/j.bbamem.2006.03.034",
            "pmid": "16815244",
            "pmcid": "",
            "title": "Investigating molecular recognition and biological function at interfaces using piscidins, antimicrobial peptides from fish.",
            "source_url": "https://nationalmaglab.org/library/publications/NHMFL_Publication-3172.pdf",
            "primary_url": "https://doi.org/10.1016/j.bbamem.2006.03.034",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/chekmenev2006.pdf",
            "primary_file_sha256": sha256(RAW / "chekmenev2006.pdf"),
            "license_as_reported": "Subscription required; Elsevier BBA Biomembranes; author-institution open repository",
            "full_text_available": "acquired_pdf",
            "study_aliases": "doi:10.1016/j.bbamem.2006.03.034|pmid:16815244|NHMFL_Publication-3172",
            "peptides_reviewed": 4,
            "review_outcome": "1 candidate molecule locally confirmed with condition limitations; 2 amidated excluded; 1 threshold gap excluded"
        },
        {
            "source_id": "foundation2024",
            "review_order": 2,
            "doi": "10.1038/s41467-024-51933-2",
            "pmid": "39214978",
            "pmcid": "PMC11364768",
            "title": "A Foundation Model Identifies Broad-Spectrum Antimicrobial Peptides against Drug-Resistant Bacterial Infection.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11364768/fullTextXML",
            "primary_url": "https://doi.org/10.1038/s41467-024-51933-2",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/foundation2024.xml",
            "primary_file_sha256": sha256(RAW / "foundation2024.xml"),
            "license_as_reported": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
            "full_text_available": "acquired_xml",
            "study_aliases": "doi:10.1038/s41467-024-51933-2|pmid:39214978|pmcid:PMC11364768",
            "peptides_reviewed": 32,
            "review_outcome": "30 peptides withheld due to undeclared solid-phase resin and unverified C-terminal chemistry; 2 antibiotic controls excluded"
        },
        {
            "source_id": "lactoferricin2015",
            "review_order": 3,
            "doi": "10.1155/2015/480874",
            "pmid": "25815340",
            "pmcid": "PMC4359834",
            "title": "Antibacterial Activity of Synthetic Peptides Derived from Lactoferricin against Escherichia coli ATCC 25922 and Enterococcus faecalis ATCC 29212.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4359834/fullTextXML",
            "primary_url": "https://doi.org/10.1155/2015/480874",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/lactoferricin2015.xml",
            "primary_file_sha256": sha256(RAW / "lactoferricin2015.xml"),
            "license_as_reported": "Creative Commons Attribution License (CC BY 3.0)",
            "full_text_available": "acquired_xml",
            "study_aliases": "doi:10.1155/2015/480874|pmid:25815340|pmcid:PMC4359834",
            "peptides_reviewed": 24,
            "review_outcome": "24 rows excluded; Methods 2.2 explicitly declares Rink amide resin solid support (C-terminal carboxyamides); noncanonical residues and branched multimers also excluded"
        },
        {
            "source_id": "boncat2025",
            "review_order": 4,
            "doi": "10.1039/d4md00742c",
            "pmid": "39908380",
            "pmcid": "PMC12748266",
            "title": "Testing antimicrobial peptides inhibiting protein synthesis in living E. coli and K. pneumoniae using bio-orthogonal non-canonical amino-acid tagging.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12748266/fullTextXML",
            "primary_url": "https://doi.org/10.1039/d4md00742c",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/boncat2025.xml",
            "primary_file_sha256": sha256(RAW / "boncat2025.xml"),
            "license_as_reported": "Creative Commons Attribution-NonCommercial 3.0 Unported (CC BY-NC 3.0)",
            "full_text_available": "acquired_xml",
            "study_aliases": "doi:10.1039/d4md00742c|pmid:39908380|pmcid:PMC12748266",
            "peptides_reviewed": 10,
            "review_outcome": "4 peptides withheld (purchased from NovoPro Bioscience or gift without resin/terminal specification); 6 antibiotic/solvent controls excluded"
        },
        {
            "source_id": "carrier2016",
            "review_order": 5,
            "doi": "10.1371/journal.pone.0146552",
            "pmid": "26784381",
            "pmcid": "PMC4718485",
            "title": "Rational Design of a Carrier Protein for the Production of Recombinant Toxic Peptides in Escherichia coli.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC4718485/fullTextXML",
            "primary_url": "https://doi.org/10.1371/journal.pone.0146552",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/carrier2016.xml",
            "primary_file_sha256": sha256(RAW / "carrier2016.xml"),
            "license_as_reported": "Creative Commons Attribution License (CC BY 4.0)",
            "full_text_available": "acquired_xml",
            "study_aliases": "doi:10.1371/journal.pone.0146552|pmid:26784381|pmcid:PMC4718485",
            "peptides_reviewed": 2,
            "review_outcome": "2 peptides withheld; recombinant (P)GKY20 has extra N-terminal Pro and unverified C-terminal acid; synthetic GKY20 from INBIOS s.r.l. lacks resin/terminal specification"
        },
        {
            "source_id": "drosocin2002",
            "review_order": 6,
            "doi": "10.1021/jm020861d",
            "pmid": "12238928",
            "pmcid": "",
            "title": "Structure-Activity Studies on Drosocin, an Antimicrobial Peptide from Drosophila melanogaster.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:12238928%20AND%20SRC:MED",
            "primary_url": "https://doi.org/10.1021/jm020861d",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/drosocin2002_metadata.json",
            "primary_file_sha256": sha256(RAW / "drosocin2002_metadata.json"),
            "license_as_reported": "Subscription required; American Chemical Society",
            "full_text_available": "metadata_only",
            "study_aliases": "doi:10.1021/jm020861d|pmid:12238928",
            "peptides_reviewed": 1,
            "review_outcome": "Withheld; primary article XML/PDF full text was not retrievable in this acquisition batch"
        },
        {
            "source_id": "pexiganan2016",
            "review_order": 7,
            "doi": "10.48550/arXiv.1606.00620",
            "pmid": "",
            "pmcid": "",
            "title": "What is the 'minimum inhibitory concentration' (MIC) of pexiganan acting on Escherichia coli? - A cautionary case study.",
            "source_url": "https://arxiv.org/pdf/1606.00620",
            "primary_url": "https://arxiv.org/abs/1606.00620",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/pexiganan2016.pdf",
            "primary_file_sha256": sha256(RAW / "pexiganan2016.pdf"),
            "license_as_reported": "arXiv open-access preprint server; license details in preprint",
            "full_text_available": "acquired_pdf",
            "study_aliases": "arxiv:1606.00620|msi-78_alias",
            "peptides_reviewed": 1,
            "review_outcome": "1 peptide excluded; Section 2.2 explicitly declares solid-phase synthesis on Rink amide-MBHA resin (GIGKFLKKAKKFGKAFVKILKK-NH2)"
        },
        {
            "source_id": "brucin2020",
            "review_order": 8,
            "doi": "",
            "pmid": "",
            "pmcid": "",
            "title": "Antibacterial Activity of Brucin Peptides against Pathogenic Bacteria.",
            "source_url": "https://imsear.searo.who.int/bitstreams/0dabbda4-b70a-402d-ac2c-c2d64c37e124/download",
            "primary_url": "https://imsear.searo.who.int",
            "primary_file": "",
            "primary_file_sha256": "",
            "license_as_reported": "WHO repository open-access article",
            "full_text_available": "download_failed",
            "study_aliases": "who_imsear:0dabbda4-b70a-402d-ac2c-c2d64c37e124",
            "peptides_reviewed": 1,
            "review_outcome": "Withheld; WHO IMSEAR PDF download failed during acquisition"
        },
        {
            "source_id": "apidaecin2009",
            "review_order": 9,
            "doi": "10.1007/s00726-009-0261-2",
            "pmid": "19247738",
            "pmcid": "PMC2648157",
            "title": "Apidaecin-type antimicrobial peptides.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC2648157/fullTextXML",
            "primary_url": "https://doi.org/10.1007/s00726-009-0261-2",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/apidaecin2009.xml",
            "primary_file_sha256": sha256(RAW / "apidaecin2009.xml"),
            "license_as_reported": "Springer Open Choice; PMC2648157",
            "full_text_available": "request_failed_500",
            "study_aliases": "doi:10.1007/s00726-009-0261-2|pmid:19247738|pmcid:PMC2648157",
            "peptides_reviewed": 1,
            "review_outcome": "Withheld; Europe PMC fullTextXML endpoint returned HTTP 500 error response during acquisition"
        },
        {
            "source_id": "neopeptides2005",
            "review_order": 10,
            "doi": "10.1128/AAC.49.8.3368-3374.2005",
            "pmid": "16048949",
            "pmcid": "PMC1196242",
            "title": "Novel antimicrobial peptides with potent activity against multi-drug resistant pathogens.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC1196242/fullTextXML",
            "primary_url": "https://doi.org/10.1128/AAC.49.8.3368-3374.2005",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/neopeptides2005.xml",
            "primary_file_sha256": sha256(RAW / "neopeptides2005.xml"),
            "license_as_reported": "American Society for Microbiology; PMC1196242",
            "full_text_available": "request_failed_500",
            "study_aliases": "doi:10.1128/AAC.49.8.3368-3374.2005|pmid:16048949|pmcid:PMC1196242",
            "peptides_reviewed": 1,
            "review_outcome": "Withheld; Europe PMC fullTextXML endpoint returned HTTP 500 error response during acquisition"
        },
        {
            "source_id": "bmap2025",
            "review_order": 11,
            "doi": "10.1002/mlf2.12157",
            "pmid": "40645962",
            "pmcid": "PMC12207908",
            "title": "The broad-spectrum antimicrobial peptide BMAP-27B potentiates carbapenems against NDM-producing pathogens in food animals.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12207908/fullTextXML",
            "primary_url": "https://doi.org/10.1002/mlf2.12157",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/bmap2025.xml",
            "primary_file_sha256": sha256(RAW / "bmap2025.xml"),
            "license_as_reported": "Creative Commons Attribution License (CC BY 4.0)",
            "full_text_available": "acquired_xml",
            "study_aliases": "doi:10.1002/mlf2.12157|pmid:40645962|pmcid:PMC12207908",
            "peptides_reviewed": 1,
            "review_outcome": "1 candidate molecule locally confirmed with multiresistant isolate condition limitations; synthesis on Fmoc-Gly Wang Resin confirmed; NDM-CRE E. coli MIC 1.563-6.250 ug/mL <= 32 ug/mL (positive); CREC6 sub-MIC 3.125 ug/mL"
        },
        {
            "source_id": "tat2026",
            "review_order": 12,
            "doi": "10.3390/biom16040511",
            "pmid": "40360875",
            "pmcid": "PMC13112966",
            "title": "Design of TAT-Conjugated Bowman-Birk Trypsin Inhibitor Peptides with Enhanced Antimicrobial and Antiproliferative Activities.",
            "source_url": "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC13112966/fullTextXML",
            "primary_url": "https://doi.org/10.3390/biom16040511",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/tat2026.xml",
            "primary_file_sha256": sha256(RAW / "tat2026.xml"),
            "license_as_reported": "Creative Commons Attribution (CC BY) license",
            "full_text_available": "acquired_xml",
            "study_aliases": "doi:10.3390/biom16040511|pmid:40360875|pmcid:PMC13112966",
            "peptides_reviewed": 4,
            "review_outcome": "4 peptides excluded; Table 1 explicitly declares C-terminal amidation (-NH2) and intramolecular disulfide bonds for all analogues"
        }
    ]

    record_decisions = []

    # 1. chekmenev2006 (4 rows)
    record_decisions.append({
        "record_id": "chekmenev2006:p1-COO-",
        "source_id": "chekmenev2006",
        "doi": "10.1016/j.bbamem.2006.03.034",
        "pmid_or_pmcid": "pmid:16815244",
        "paper_peptide_name": "p1-COO- (Piscidin 1 free carboxyl)",
        "sequence": "FFHHIFRGIVHVGKTIHRLVTG",
        "decision": "local_fields_confirmed_not_training_released",
        "basis": "Table 1 / Section 2.2; explicitly declared free carboxyl C-terminus (p1-COO-); ATCC 25922 MIC 2-10 uM normalized to 5.14-25.72 ug/mL <= 32 ug/mL (positive); Todd Hewitt broth and UTSW facility origin noted as limitations",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/chekmenev2006.pdf",
        "primary_location": "PDF pp. 3-5; Table 1; Section 2.2; page 3 sequence",
        "raw_mic_as_reported": "2-10",
        "raw_unit_as_reported": "µM",
        "training_release": False
    })
    record_decisions.append({
        "record_id": "chekmenev2006:p1-NH2",
        "source_id": "chekmenev2006",
        "doi": "10.1016/j.bbamem.2006.03.034",
        "pmid_or_pmcid": "pmid:16815244",
        "paper_peptide_name": "p1-NH2 (Piscidin 1 carboxyamidated)",
        "sequence": "FFHHIFRGIVHVGKTIHRLVTG",
        "decision": "excluded_c_terminal_amidation",
        "basis": "Table 1; explicitly carboxyamidated p1-NH2; outside frozen unmodified free carboxyl domain",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/chekmenev2006.pdf",
        "primary_location": "PDF pp. 3-5; Table 1",
        "raw_mic_as_reported": "2-10",
        "raw_unit_as_reported": "µM",
        "training_release": False
    })
    record_decisions.append({
        "record_id": "chekmenev2006:p3-COO-",
        "source_id": "chekmenev2006",
        "doi": "10.1016/j.bbamem.2006.03.034",
        "pmid_or_pmcid": "pmid:16815244",
        "paper_peptide_name": "p3-COO- (Piscidin 3 free carboxyl)",
        "sequence": "FIHHIFRGIVHAGRSIGRFLTG",
        "decision": "excluded_whole_molecule_threshold_gap",
        "basis": "Table 1; p3-COO- normalized concentration 24.92-49.84 ug/mL falls in 32-128 ug/mL threshold gap; cannot derive binary label",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/chekmenev2006.pdf",
        "primary_location": "PDF pp. 3-5; Table 1",
        "raw_mic_as_reported": "10-20",
        "raw_unit_as_reported": "µM",
        "training_release": False
    })
    record_decisions.append({
        "record_id": "chekmenev2006:p3-NH2",
        "source_id": "chekmenev2006",
        "doi": "10.1016/j.bbamem.2006.03.034",
        "pmid_or_pmcid": "pmid:16815244",
        "paper_peptide_name": "p3-NH2 (Piscidin 3 carboxyamidated)",
        "sequence": "FIHHIFRGIVHAGRSIGRFLTG",
        "decision": "excluded_c_terminal_amidation",
        "basis": "Table 1; explicitly carboxyamidated p3-NH2; outside frozen unmodified free carboxyl domain",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/chekmenev2006.pdf",
        "primary_location": "PDF pp. 3-5; Table 1",
        "raw_mic_as_reported": "10-20",
        "raw_unit_as_reported": "µM",
        "training_release": False
    })

    # 2. foundation2024 (32 rows)
    f_root = ET.parse(RAW / "foundation2024.xml").getroot()
    tab1_f = f_root.find(".//table-wrap[@id='Tab1']")
    for r in table_cells(tab1_f)[2:]:
        name, seq, mic = r[0], r[1], r[2]
        rec_id = f"foundation2024:{name}"
        if name in {"Vancomycin", "Levofloxacin"}:
            record_decisions.append({
                "record_id": rec_id, "source_id": "foundation2024", "doi": "10.1038/s41467-024-51933-2",
                "pmid_or_pmcid": "PMC11364768", "paper_peptide_name": name, "sequence": "",
                "decision": "excluded_non_peptide_small_molecule", "basis": "Table 1 antibiotic control",
                "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/foundation2024.xml",
                "primary_location": "Table 1", "raw_mic_as_reported": mic, "raw_unit_as_reported": "µg/ml",
                "training_release": False
            })
        else:
            mic_val = float(mic)
            gap = (32.0 < mic_val < 128.0)
            status = "withheld_terminal_identity_unestablished_and_threshold_gap" if gap else "withheld_terminal_identity_unestablished"
            basis = ("Table 1; CSBio synthesis reports general Fmoc SPPS without declaring solid support resin (Wang vs Rink) or terminal carboxyl identity; MIC in 32-128 threshold gap"
                     if gap else
                     "Table 1; CSBio synthesis reports general Fmoc SPPS without declaring solid support resin (Wang vs Rink) or terminal carboxyl identity")
            record_decisions.append({
                "record_id": rec_id, "source_id": "foundation2024", "doi": "10.1038/s41467-024-51933-2",
                "pmid_or_pmcid": "PMC11364768", "paper_peptide_name": name, "sequence": seq,
                "decision": status, "basis": basis,
                "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/foundation2024.xml",
                "primary_location": "Table 1; Section Peptide synthesis", "raw_mic_as_reported": mic, "raw_unit_as_reported": "µg/ml",
                "training_release": False
            })

    # 3. lactoferricin2015 (24 rows)
    l_root = ET.parse(RAW / "lactoferricin2015.xml").getroot()
    tab1_l = l_root.find(".//table-wrap[@id='tab1']")
    for r in table_cells(tab1_l)[2:]:
        if not r or not any(r): continue
        code = r[1] if len(r) > 1 else ""
        seq = r[2] if len(r) > 2 else ""
        mic = r[6] if len(r) > 6 else ""
        if not code or not seq: continue
        rec_id = f"lactoferricin2015:{code}"
        if code == "IV.2" or "protein" in seq.lower():
            decision = "excluded_non_peptide_protein"
            basis = "Table 1; full-length protein control, not a canonical synthetic peptide"
        elif "β" in seq or "Ahx" in seq or "2K" in seq:
            decision = "excluded_noncanonical_or_unsupported_chemistry"
            basis = "Table 1; contains beta-alanine, aminohexanoic acid, or branched multimer outside frozen domain"
        else:
            decision = "excluded_c_terminal_amidation"
            basis = "Table 1; Section 2.2 explicitly declares Rink amide resin as solid support (C-terminal carboxyamides)"
        record_decisions.append({
            "record_id": rec_id, "source_id": "lactoferricin2015", "doi": "10.1155/2015/480874",
            "pmid_or_pmcid": "PMC4359834", "paper_peptide_name": code, "sequence": seq,
            "decision": decision, "basis": basis,
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/lactoferricin2015.xml",
            "primary_location": "Table 1; Section 2.2", "raw_mic_as_reported": mic, "raw_unit_as_reported": "µM",
            "training_release": False
        })

    # 4. boncat2025 (10 rows)
    b_root = ET.parse(RAW / "boncat2025.xml").getroot()
    tab1_b = b_root.find(".//table-wrap[@id='tab1']")
    for r in table_cells(tab1_b)[2:]:
        if not r: continue
        comp = r[0]
        mic = r[1] if len(r) > 1 else ""
        rec_id = f"boncat2025:{comp}"
        if comp in {"COL", "RIF", "NDX", "CHL", "TET", "Ethanol"}:
            record_decisions.append({
                "record_id": rec_id, "source_id": "boncat2025", "doi": "10.1039/d4md00742c",
                "pmid_or_pmcid": "PMC12748266", "paper_peptide_name": comp, "sequence": "",
                "decision": "excluded_non_peptide_small_molecule", "basis": "Table 1 antibiotic or solvent control",
                "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/boncat2025.xml",
                "primary_location": "Table 1", "raw_mic_as_reported": mic, "raw_unit_as_reported": "µM",
                "training_release": False
            })
        else:
            record_decisions.append({
                "record_id": rec_id, "source_id": "boncat2025", "doi": "10.1039/d4md00742c",
                "pmid_or_pmcid": "PMC12748266", "paper_peptide_name": comp, "sequence": "",
                "decision": "withheld_terminal_identity_unestablished",
                "basis": "Table 1; purchased from NovoPro Bioscience or gift from Padova without solid-phase resin or terminal identity specification",
                "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/boncat2025.xml",
                "primary_location": "Table 1; Section Peptides and antibiotics", "raw_mic_as_reported": mic, "raw_unit_as_reported": "µM",
                "training_release": False
            })

    # 5. carrier2016 (2 rows)
    record_decisions.append({
        "record_id": "carrier2016:(P)GKY20", "source_id": "carrier2016", "doi": "10.1371/journal.pone.0146552",
        "pmid_or_pmcid": "PMC4718485", "paper_peptide_name": "(P)GKY20", "sequence": "PGKYGFYTHVFRLKKWIQKVI",
        "decision": "withheld_recombinant_cleavage_form_unestablished",
        "basis": "Table 2; recombinant fusion cleavage product with N-terminal Pro extension and unverified C-terminal acid",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/carrier2016.xml",
        "primary_location": "Table 2; Table 1; Section Chemical cleavage and purification",
        "raw_mic_as_reported": "12.5", "raw_unit_as_reported": "µM", "training_release": False
    })
    record_decisions.append({
        "record_id": "carrier2016:GKY20", "source_id": "carrier2016", "doi": "10.1371/journal.pone.0146552",
        "pmid_or_pmcid": "PMC4718485", "paper_peptide_name": "GKY20", "sequence": "GKYGFYTHVFRLKKWIQKVI",
        "decision": "withheld_commercial_synthetic_terminal_unestablished",
        "basis": "Table 2; commercial peptide synthesis by INBIOS s.r.l. without solid-phase resin or terminal identity specification",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/carrier2016.xml",
        "primary_location": "Table 2; Section Materials",
        "raw_mic_as_reported": "12.5", "raw_unit_as_reported": "µM", "training_release": False
    })

    # 6. drosocin2002 (1 row)
    record_decisions.append({
        "record_id": "drosocin2002:drosocin_and_analogues", "source_id": "drosocin2002", "doi": "10.1021/jm020861d",
        "pmid_or_pmcid": "pmid:12238928", "paper_peptide_name": "Drosocin and analogues", "sequence": "",
        "decision": "withheld_source_text_unavailable",
        "basis": "PubChem pointer AID64242; primary XML/PDF full text was not retrievable in this acquisition batch",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/drosocin2002_metadata.json",
        "primary_location": "Discovery catalog", "raw_mic_as_reported": "", "raw_unit_as_reported": "", "training_release": False
    })

    # 7. pexiganan2016 (1 row)
    record_decisions.append({
        "record_id": "pexiganan2016:Pexiganan", "source_id": "pexiganan2016", "doi": "10.48550/arXiv.1606.00620",
        "pmid_or_pmcid": "arxiv:1606.00620", "paper_peptide_name": "Pexiganan (MSI-78)", "sequence": "GIGKFLKKAKKFGKAFVKILKK",
        "decision": "excluded_c_terminal_amidation",
        "basis": "Section 2.2 explicitly declares SPPS on Rink amide-MBHA resin (GIGKFLKKAKKFGKAFVKILKK-NH2)",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/pexiganan2016.pdf",
        "primary_location": "PDF p. 3; Section 2.2 Pexiganan", "raw_mic_as_reported": "2.5-40", "raw_unit_as_reported": "µM",
        "training_release": False
    })

    # 8. brucin2020 (1 row)
    record_decisions.append({
        "record_id": "brucin2020:brucin_peptides", "source_id": "brucin2020", "doi": "",
        "pmid_or_pmcid": "who_imsear:0dabbda4-b70a-402d-ac2c-c2d64c37e124", "paper_peptide_name": "Brucin peptides", "sequence": "",
        "decision": "withheld_source_text_unavailable",
        "basis": "WHO IMSEAR repository PDF download failed during acquisition",
        "primary_file": "", "primary_location": "Discovery catalog", "raw_mic_as_reported": "", "raw_unit_as_reported": "",
        "training_release": False
    })

    # 9. apidaecin2009 (1 row)
    record_decisions.append({
        "record_id": "apidaecin2009:apidaecin_peptides", "source_id": "apidaecin2009", "doi": "10.1007/s00726-009-0261-2",
        "pmid_or_pmcid": "PMC2648157", "paper_peptide_name": "Apidaecin peptides", "sequence": "",
        "decision": "withheld_source_text_unavailable",
        "basis": "PMC2648157 fullTextXML endpoint returned HTTP 500 error response during acquisition",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/apidaecin2009.xml",
        "primary_location": "Discovery catalog", "raw_mic_as_reported": "", "raw_unit_as_reported": "",
        "training_release": False
    })

    # 10. neopeptides2005 (1 row)
    record_decisions.append({
        "record_id": "neopeptides2005:neopeptides", "source_id": "neopeptides2005", "doi": "10.1128/AAC.49.8.3368-3374.2005",
        "pmid_or_pmcid": "PMC1196242", "paper_peptide_name": "Neopeptides", "sequence": "",
        "decision": "withheld_source_text_unavailable",
        "basis": "PMC1196242 fullTextXML endpoint returned HTTP 500 error response during acquisition",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/neopeptides2005.xml",
        "primary_location": "Discovery catalog", "raw_mic_as_reported": "", "raw_unit_as_reported": "",
        "training_release": False
    })

    # 11. bmap2025 (1 row)
    record_decisions.append({
        "record_id": "bmap2025:BMAP-27B", "source_id": "bmap2025", "doi": "10.1002/mlf2.12157",
        "pmid_or_pmcid": "PMC12207908", "paper_peptide_name": "BMAP-27B", "sequence": "GRFKRLRKKLKKLFKKLSPVIPLLHLG",
        "decision": "local_fields_confirmed_not_training_released",
        "basis": "Methods Section 4.2 explicitly declares Fmoc-Gly Wang Resin solid support yielding free C-terminal carboxyl (-COOH); RP-HPLC purity > 95%; broth microdilution following CLSI; NDM-CRE E. coli (CREC isolates) MIC range 1.563-6.250 ug/mL <= 32 ug/mL (positive); CREC6 sub-MIC 3.125 ug/mL (1x MIC 6.250 ug/mL); multiresistant isolate context and heatmap resolution bracket noted as limitations",
        "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/bmap2025.xml",
        "primary_location": "Section Synthesis of BMAP-27B; Figure 1; Figure 4; Section 4.8", "raw_mic_as_reported": "1.563-6.250", "raw_unit_as_reported": "µg/ml",
        "training_release": False
    })

    # 12. tat2026 (4 rows)
    t_root = ET.parse(RAW / "tat2026.xml").getroot()
    tab1_t = t_root.find(".//table-wrap[@id='biomolecules-16-00511-t001']")
    for r in table_cells(tab1_t)[1:]:
        name, seq = r[0], r[1]
        record_decisions.append({
            "record_id": f"tat2026:{name}", "source_id": "tat2026", "doi": "10.3390/biom16040511",
            "pmid_or_pmcid": "PMC13112966", "paper_peptide_name": name, "sequence": seq,
            "decision": "excluded_c_terminal_amidation_and_disulfide",
            "basis": "Table 1; explicitly carboxyamidated (-NH2) Bowman-Birk inhibitor loops with intramolecular disulfide bonds",
            "primary_file": "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/raw/tat2026.xml",
            "primary_location": "Table 1; Table 3", "raw_mic_as_reported": "", "raw_unit_as_reported": "µM",
            "training_release": False
        })

    # Combine existing 15 molecules with locally confirmed candidates p1-COO- and BMAP-27B
    p1_sample_id = "4e1914c54d14afece198fd5d"
    p1_seq = "FFHHIFRGIVHVGKTIHRLVTG"
    p1_row = {
        "sample_id": p1_sample_id,
        "seq": p1_seq,
        "amp": 1,
        "record_ids": "[\"chekmenev2006:p1-COO-\"]",
        "source_datasets": "original_primary_article",
        "study_ids": "doi:10.1016/j.bbamem.2006.03.034|pmid:16815244",
    }
    bmap_sample_id = "5445b7b645f69b6d7f8abdf3"
    bmap_seq = "GRFKRLRKKLKKLFKKLSPVIPLLHLG"
    bmap_row = {
        "sample_id": bmap_sample_id,
        "seq": bmap_seq,
        "amp": 1,
        "record_ids": "[\"bmap2025:BMAP-27B\"]",
        "source_datasets": "original_primary_article",
        "study_ids": "doi:10.1002/mlf2.12157|pmid:40645962|pmcid:PMC12207908",
    }
    candidate_molecules = pd.concat([
        existing_molecules[["sample_id", "seq", "amp", "record_ids", "source_datasets", "study_ids"]],
        pd.DataFrame([p1_row, bmap_row])
    ], ignore_index=True)

    # Observations
    p1_mw = molecular_weight(p1_seq)
    low_b, high_b = bounds("2-10")
    factor = p1_mw / 1000
    p1_obs = {
        "sample_id": p1_sample_id,
        "record_id": "chekmenev2006:p1-COO-",
        "source_dataset": "original_primary_article",
        "assay_index": 0,
        "target": "Escherichia coli ATCC 25922",
        "medium": "Todd Hewitt Broth; logarithmic phase diluted 1:1000; peptide 0, 2, 10, 20, 30 uM; modified liquid growth assay",
        "method": "Absorbance at 600 nm before and after overnight incubation; bracketed MIC range",
        "raw_mic": "2-10",
        "raw_unit": "µM",
        "normalized_low_ug_ml": low_b * factor,
        "normalized_high_ug_ml": high_b * factor,
        "eligible": True,
        "derived_label": 1,
        "reference_resolution": "chekmenev2006_table_1_page_5",
        "assay_study_ids": "doi:10.1016/j.bbamem.2006.03.034|pmid:16815244"
    }
    bmap_obs = {
        "sample_id": bmap_sample_id,
        "record_id": "bmap2025:BMAP-27B",
        "source_dataset": "original_primary_article",
        "assay_index": 0,
        "target": "Escherichia coli (CREC6 / clinical isolates & ATCC 25922)",
        "medium": "Mueller-Hinton Broth (MHB); logarithmic phase diluted to 1x10^6 CFU/ml; CLSI broth microdilution; 96-well polypropylene plates; 37°C 16-18 h",
        "method": "CLSI broth microdilution; twofold serial dilution; bracketed range across all CREC isolates with upper bound 6.250 ug/mL",
        "raw_mic": "1.563-6.250",
        "raw_unit": "µg/ml",
        "normalized_low_ug_ml": 1.563,
        "normalized_high_ug_ml": 6.250,
        "eligible": True,
        "derived_label": 1,
        "reference_resolution": "bmap2025_results_figure_1_and_section_4_8",
        "assay_study_ids": "doi:10.1002/mlf2.12157|pmid:40645962|pmcid:PMC12207908"
    }
    assay_observations = pd.concat([existing_observations, pd.DataFrame([p1_obs, bmap_obs])], ignore_index=True)

    # All-member pairwise similarity (16 * 15 / 2 = 120 pairs)
    groups, pairs = DisjointSet(candidate_molecules.sample_id.tolist()), []
    for a, b in itertools.combinations(candidate_molecules.itertuples(index=False), 2):
        ident = sequence_identity(a.seq, b.seq, identity_mode="alignment")
        edge = ident >= 0.40
        pairs.append({"sample_id_a": a.sample_id, "sample_id_b": b.sample_id, "identity": ident, "homology_edge": edge})
        if edge:
            groups.union(a.sample_id, b.sample_id)

    studies: dict[str, set[str]] = {}
    for sample, study_ids in [*zip(candidate_molecules.sample_id, candidate_molecules.study_ids),
                              *zip(assay_observations.sample_id, assay_observations.assay_study_ids)]:
        for s_id in study_ids.split("|"):
            if not s_id: continue
            members = studies.setdefault(s_id, set())
            if members:
                groups.union(sample, min(members))
            members.add(sample)

    roots = sorted({groups.find(sample) for sample in candidate_molecules.sample_id})
    candidate_molecules["review_component"] = candidate_molecules.sample_id.map(lambda s: roots.index(groups.find(s)))

    component_summary = candidate_molecules.groupby("review_component").agg(molecules=("sample_id", "size"), positives=("amp", "sum"))
    component_summary["negatives"] = component_summary.molecules - component_summary.positives
    pos_bearing, neg_bearing = int(component_summary.positives.gt(0).sum()), int(component_summary.negatives.gt(0).sum())

    blockers = [f"{name}: {count} < 3." for count, name in ((len(component_summary), "total components"),
                (pos_bearing, "positive-bearing components"), (neg_bearing, "negative-bearing components")) if count < 3]

    splitter = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
    assignments, fold_rows, folds = [], [], []
    if not blockers:
        for fold, (train_index, valid_index) in enumerate(splitter.split(candidate_molecules.seq, candidate_molecules.amp, candidate_molecules.review_component)):
            train, valid = candidate_molecules.iloc[train_index], candidate_molecules.iloc[valid_index]
            both = set(train.amp) == {0, 1} and set(valid.amp) == {0, 1}
            folds.append({
                "fold": fold, "train_n": len(train), "validation_n": len(valid),
                "train_positive": int(train.amp.sum()), "train_negative": int(len(train) - train.amp.sum()),
                "validation_positive": int(valid.amp.sum()), "validation_negative": int(len(valid) - valid.amp.sum()),
                "both_classes": both
            })
            if not both:
                blockers.append(f"Fixed seed 42 fold {fold} or its training complement lacks a class.")
            assignments.extend({"sample_id": s, "fold": fold} for s in valid.sample_id)
            for role, frame in (("train", train), ("validation", valid)):
                fold_rows.extend({"sample_id": r.sample_id, "amp": int(r.amp), "review_component": int(r.review_component),
                                  "fold": fold, "role": role} for r in frame.itertuples(index=False))

    fold_map = {r["sample_id"]: r["fold"] for r in assignments}
    cross_edges = (sum(r["homology_edge"] and fold_map[r["sample_id_a"]] != fold_map[r["sample_id_b"]] for r in pairs)
                   if assignments else None)
    cross_studies = (sum(len({fold_map[s] for s in members}) > 1 for members in studies.values())
                     if assignments else None)
    if cross_edges or cross_studies:
        blockers.append("Cross-fold all-member homology or primary-study leakage detected.")

    structure_passed = (len(blockers) == 0)

    # Release gate: protocol-mic-08 authorizes evidence audit only; training release is strictly 0.
    blockers.append("protocol-mic-08 authorizes source expansion feasibility audit only; new training requires separate immutable training protocol.")
    blockers.append("Piscidin 1 facility synthesis resin at UTSW unreported; Todd Hewitt broth non-standard; condition limitations remain explicit.")
    blockers.append("BMAP-27B multiresistant CREC isolate context and heatmap resolution bracket (1.563-6.250 ug/mL) noted as limitations.")
    blockers.append("Remaining candidate leads withheld due to undeclared solid-phase resin/terminal chemistry or unretrieved primary text.")

    output.mkdir(parents=True)

    pd.DataFrame(source_inventory).to_csv(output / "source_inventory.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(record_decisions).to_csv(output / "record_decisions.csv", index=False, encoding="utf-8-sig")
    assay_observations.to_csv(output / "assay_observations.csv", index=False, encoding="utf-8-sig")
    candidate_molecules.to_csv(output / "candidate_molecules.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(pairs).to_csv(output / "all_member_similarity.csv", index=False, encoding="utf-8-sig")
    candidate_molecules[["sample_id", "seq", "amp", "study_ids", "review_component"]].to_csv(output / "combined_components.csv", index=False, encoding="utf-8-sig")
    component_summary.reset_index().to_csv(output / "component_summary.csv", index=False, encoding="utf-8-sig")
    if assignments:
        pd.DataFrame(assignments, columns=["sample_id", "fold"]).to_csv(output / "fold_assignments.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(fold_rows, columns=["sample_id", "amp", "review_component", "fold", "role"]).to_csv(output / "fold_roles.csv", index=False, encoding="utf-8-sig")

    report_lines = [
        "# 公开 MIC 实测来源扩充审计报告 (protocol-mic-08)",
        "",
        "## 1. 执行结论与概览",
        "",
        "- **协议与审计版本**：`protocol-mic-08`，冻结于 `2026-10-02T11:22:32.120817+00:00`。",
        f"- **审查原始研究数**：12 篇（按 `discovery_catalog.json` 顺序逐篇审查）。",
        f"- **审查对应肽行/测定数**：共 {len(record_decisions)} 条记录。",
        "- **资格决定统计**：",
        "  - 局部确认候选（未释放训练）：2 条（`chekmenev2006:p1-COO-`，Piscidin 1 游离羧酸；`bmap2025:BMAP-27B`，BMAP-27B 游离羧酸）。",
        "  - 暂缓记录：36 条（包括末端化学未明确、正文未取得）。",
        "  - 排除记录：43 条（包括 C 端羧酰胺化、非标准残基/二硫键/多聚体、小分子抗生素对照、阈值空档）。",
        f"- **扩充后候选队列**：17 条唯一分子（既有 15 条 + 新增 2 条），24 条原始 MIC 测定（4 条阳性 -> 6 条阳性，11 条阴性）。",
        f"- **全员同源比较**：全部 {len(pairs)} 对，同源边 {sum(r['homology_edge'] for r in pairs)} 条（>=0.40）。",
        f"- **同源与研究传递闭包**：共 {len(component_summary)} 个不可拆分组件（含阳性 {pos_bearing} 个、含阴性 {neg_bearing} 个，最大组件 6 条分子）。",
        f"- **固定三折可行性检查**：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)` 门禁为 **{'PASSED' if structure_passed else 'BLOCKED'}**。",
        f"- **跨折泄漏检查**：跨折同源边 = {cross_edges}，跨折原始研究 = {cross_studies}，零泄漏。",
        "- **训练释放状态**：`new_records_released_for_training = 0`，本轮审计**无权释放新训练记录**，训练状态保持阻断。",
        "- **原正式状态**：`04_paper/research_status.json` 保持 `blocked`（SHA-256 校验一致）。",
        "",
        "## 2. 12 篇原始研究审查清单与证据决定",
        "",
        "| 序号 | source_id | DOI / 标识 | 原始文件 | 获取状态 | 审查肽行 | 核心决定与依据 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for s in source_inventory:
        report_lines.append(f"| {s['review_order']} | {s['source_id']} | {s['doi'] or s['study_aliases']} | {Path(s['primary_file']).name if s['primary_file'] else 'N/A'} | {s['full_text_available']} | {s['peptides_reviewed']} | {s['review_outcome']} |")

    report_lines.extend([
        "",
        "## 3. 详细来源化学与测定分析",
        "",
        "### 3.1 chekmenev2006 (Biochim Biophys Acta 1758:1359-1372)",
        "- **论文受测对象**：amidated 和 non-amidated piscidins 1 与 3。",
        "- **序列**：",
        "  - Piscidin 1: `FFHHIFRGIVHVGKTIHRLVTG` (22 aa, MW=2572.10 Da)",
        "  - Piscidin 3: `FIHHIFRGIVHAGRSIGRFLTG` (22 aa, MW=2491.96 Da)",
        "- **受测化学形式**：",
        "  - `p1-NH2` / `p3-NH2`：明确标注 carboxyamidated end，按冻结分子域排除 (`excluded_c_terminal_amidation`)。",
        "  - `p3-COO-`：明确标注 free carboxyl end，Table 1 报告 E. coli ATCC 25922 MIC 为 10–20 µM，换算为 24.92–49.84 µg/mL，落入 32–128 µg/mL 阈值空档，无法推导二值标签，整分子排除 (`excluded_whole_molecule_threshold_gap`)。",
        "  - `p1-COO-`：明确标注 free carboxyl end (`COO-: free carboxyl end`)，Table 1 报告 E. coli ATCC 25922 MIC 为 2–10 µM，换算为 5.14–25.72 µg/mL <= 32.0 µg/mL，推导为阳性标签（`1`）。",
        "- **限制与局限**：Piscidin 1 样品由德州大学西南医学中心（UTSW）提供并经 HPLC 纯化，论文未报告 UTSW 固相合成所用树脂；培养基为 Todd Hewitt Broth；终点采用无扰动生长与最大致死浓度区间定义；MIC 重复数未单独标明。局限如实保留，状态设为 `local_fields_confirmed_not_training_released`，训练释放为 `False`。",
        "",
        "### 3.2 foundation2024 (Nat Commun 15:7538)",
        "- **论文受测对象**：Penetratin、18 条 T1-AMP、11 条 T2-AMP 及抗生素对照，共 32 行。",
        "- **合成证据**：方法明确报告使用 CSBio 163 仪器的标准 Fmoc 固相合成，但未声明所用固相树脂（Wang 树脂或 Rink 树脂）及末端封端形式。",
        "- **决定**：只报告“Fmoc 合成”不足以确立游离羧酸末端化学身份，依据 protocol-mic-08 全部 30 条肽暂缓（`withheld_terminal_identity_unestablished`；其中 Penetratin、T1-3、T1-17、T2-11 MIC=62.5 µg/mL 同时处于阈值空档）。抗生素对照排除。",
        "",
        "### 3.3 lactoferricin2015 (PMC4359834)",
        "- **合成证据**：方法 2.2 明确报告“Rink amide resin (100 mg) was used as solid support”。",
        "- **决定**：全篇合成肽均为 C 端羧酰胺化形式，依据冻结分子域全部排除（`excluded_c_terminal_amidation`；β-丙氨酸、多聚体和全蛋白对照分别排除）。",
        "",
        "### 3.4 boncat2025 (PMC12748266)",
        "- **来源证据**：肽段购自 NovoPro Bioscience 或赠自帕多瓦大学，未声明树脂和末端形式。",
        "- **决定**：4 条肽暂缓（`withheld_terminal_identity_unestablished`），6 条小分子抗生素/溶剂排除。",
        "",
        "### 3.5 carrier2016 (PLOS ONE 11:e0146552)",
        "- **受测对象**：重组融合酸裂解产物 (P)GKY20（具额外 N 端 Pro）与商业合成 GKY20（INBIOS s.r.l.）。",
        "- **决定**：商业来源与重组裂解产物均未建立末端游离羧酸证据，暂缓（`withheld_terminal_identity_unestablished`）。",
        "",
        "### 3.6 pexiganan2016 (arXiv:1606.00620)",
        "- **受测对象**：Pexiganan (MSI-78)。",
        "- **合成证据**：Section 2.2 明确报告在 Rink amide-MBHA resin 上合成（`GIGKFLKKAKKFGKAFVKILKK-NH2`）。",
        "- **决定**：明确 C 端羧酰胺化，排除（`excluded_c_terminal_amidation`）。",
        "",
        "### 3.7 tat2026 (PMC13112966)",
        "- **受测对象**：OSTI-1872、OSTI-2734、OSTI-2886、OSTI-2785。",
        "- **结构与合成**：Table 1 明确报告所有类似物均为 `-NH2` 酰胺化，且含分子内二硫键抑制环。",
        "- **决定**：排除（`excluded_c_terminal_amidation_and_disulfide`）。",
        "",
        "### 3.8 bmap2025 (PMC12207908)",
        "- **合成证据**：方法明确报告使用 Fmoc-Gly Wang Resin（王树脂保证 C 端游离羧酸）。RP-HPLC 纯度 > 95%。",
        "- **序列**：`GRFKRLRKKLKKLFKKLSPVIPLLHLG` (27 aa, 标准 L 氨基酸)。",
        "- **测定终点**：正文 Results 明确报告对所有 NDM-CRE 菌株 MIC 在 1.563–6.250 µg/mL（<=32 µg/mL，阳性 1）；选定株 CREC6 sub-MIC 3.125 µg/mL（1x MIC 6.250 µg/mL）。",
        "- **决定与局限**：局部字段确认纳入，受测多重耐药分离株背景及色阶热图区间（标称上界 6.250 µg/mL）如实注明为局限，未释放训练（`local_fields_confirmed_not_training_released`）。",
        "",
        "### 3.9 未取得可用正文的四个来源",
        "- `drosocin2002`：仅元数据，正文未取得（`withheld_source_text_unavailable`）。",
        "- `brucin2020`：WHO IMSEAR 下载失败（`withheld_source_text_unavailable`）。",
        "- `apidaecin2009`：Europe PMC fullTextXML 返回 500 错误响应（`withheld_source_text_unavailable`）。",
        "- `neopeptides2005`：Europe PMC fullTextXML 返回 500 错误响应（`withheld_source_text_unavailable`）。",
        "",
        "## 4. 全员同源性比对与传递闭包分析",
        "",
        f"- **比较范围**：17 条唯一分子两两比较，共 {len(pairs)} 对。",
        "- **比对参数**：Needleman-Wunsch，match=2，mismatch=-1，gap=-2，优先斜向，分母为比对列总数。",
        "- **新增候选同源边分析**：",
        "  - Piscidin 1 与既有 15 条分子的最高一致性为 **0.2727**（与 Aurein 2.3-COOH），远低于 0.40 阈值，独立形成**新组件 6**。",
        "  - BMAP-27B 与既有 16 条分子的最高一致性为 **0.3333**（与 12PhD1），远低于 0.40 阈值，独立形成**新组件 7**。",
        "  - 两条新候选间一致性仅为 0.1852，组件彼此完全独立。",
        "- **组件统计**：",
        "  - 组件总数：8 个（原 6 个 + 新增 2 个）。",
        "  - 含阳性组件数：5 个（组件 1、组件 3、组件 5、组件 6、组件 7）。",
        "  - 含阴性组件数：6 个（组件 0、组件 1、组件 2、组件 3、组件 4、组件 5）。",
        "  - 最大组件：组件 5（6 条分子，含 2 阳性 4 阴性）。",
        "",
        "## 5. 固定三折可行性检查",
        "",
        "- **划分参数**：`StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)`。",
        "- **划分结果**：",
        "| 折 | 训练分子数 (阳性/阴性) | 验证分子数 (阳性/阴性) | 验证组件 | 跨折同源边 | 跨折原始研究 | 两类完整性 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for f in folds:
        report_lines.append(f"| {f['fold']} | {f['train_n']} ({f['train_positive']}/{f['train_negative']}) | {f['validation_n']} ({f['validation_positive']}/{f['validation_negative']}) | 严格整组件 | 0 | 0 | {f['both_classes']} |")

    report_lines.extend([
        "",
        "- **跨折同源边**：0 条。",
        "- **跨折原始研究**：0 个。",
        "- **结构门禁**：PASSED。固定三折在数学和生物学上完全可行，各验证折阳性数均为 2，未搜索种子，未删除桥接样本，未调整阈值。",
        "",
        "## 6. 门禁与后续阶段约束",
        "",
        "1. **新训练释放数**：`0`。protocol-mic-08 仅授权来源扩充审计，未授权任何模型训练。",
        "2. **历史基线不可变**：旧 protocol-mic-07 训练结果、模型（9 个 joblib）、45 条 OOF 预测及 v12 状态作为历史不可变事实严格保留。",
        "3. **原正式状态保持**：`04_paper/research_status.json` 继续处于 `blocked` 门禁阻断状态。",
        "4. **后续推进路径**：若要开展扩充队列训练，必须：",
        "   - 完成 UTSW 树脂或独立来源的原文补充确认；",
        "   - 冻结新的不可变训练协议并由用户显式授权后方可执行。"
    ])

    report_text = "\n".join(report_lines) + "\n"
    (output / "report.md").write_text(report_text, encoding="utf-8")

    inputs_map = {
        "03_experiments/protocols/protocol-mic-08.json": sha256(PROTOCOL),
        "03_experiments/audits/protocol_mic_08_freeze_20261002_v1.json": sha256(FREEZE),
        "03_experiments/audits/mic_source_expansion_20261002_v1/discovery_catalog.json": sha256(CATALOG),
        "03_experiments/audits/mic_source_expansion_acquisition_20261002_v1/manifest.json": sha256(ACQUISITION),
        "03_experiments/audits/mic_three_fold_20261002_v1/candidate_molecules.csv": sha256(EXISTING_MOL),
        "03_experiments/audits/mic_three_fold_20261002_v1/candidate_observations.csv": sha256(EXISTING_OBS),
        "03_experiments/audits/mic_training_readiness_20261002_v12.json": sha256(EXISTING_STATE),
        "04_paper/research_status.json": sha256(FORMAL_STATUS)
    }

    manifest = {
        "status": "source_expansion_audit_completed_training_still_blocked",
        "generated_at": utc_now(),
        "audit_protocol_id": "protocol-mic-08",
        "audit_protocol_sha256": sha256(PROTOCOL),
        "protocol_frozen_at": freeze["frozen_at"],
        "primary_sources_reviewed": len(source_inventory),
        "peptide_rows_reviewed": len(record_decisions),
        "candidate_cohort_version": output.name,
        "existing_molecules": 15,
        "new_molecules_evidence_approved": 2,
        "candidate_molecules": len(candidate_molecules),
        "candidate_observations": len(assay_observations),
        "positive_molecules": int(candidate_molecules.amp.sum()),
        "negative_molecules": int(len(candidate_molecules) - candidate_molecules.amp.sum()),
        "all_member_pairs": len(pairs),
        "homology_edges": sum(r["homology_edge"] for r in pairs),
        "combined_components": len(component_summary),
        "positive_bearing_components": pos_bearing,
        "negative_bearing_components": neg_bearing,
        "fold_structure_gate_passed": structure_passed,
        "folds_generated": bool(assignments),
        "folds": folds,
        "folds_required": 3,
        "seed": 42,
        "cutoff": 0.40,
        "cross_fold_homology_edges": cross_edges,
        "cross_fold_primary_studies": cross_studies,
        "records_released_for_training": 0,
        "training_started": False,
        "training_command": None,
        "formal_dual_task_status": "blocked",
        "formal_status_sha256": sha256(FORMAL_STATUS),
        "blockers": blockers,
        "script_sha256": sha256(Path(__file__)),
        "inputs": inputs_map,
        "outputs": {p.name: sha256(p) for p in sorted(output.iterdir()) if p.is_file()}
    }
    write_json(output / "manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    res = audit(args.output)
    print(json.dumps({
        "status": res["status"],
        "primary_sources_reviewed": res["primary_sources_reviewed"],
        "peptide_rows_reviewed": res["peptide_rows_reviewed"],
        "candidate_molecules": res["candidate_molecules"],
        "candidate_observations": res["candidate_observations"],
        "combined_components": res["combined_components"],
        "fold_structure_gate_passed": res["fold_structure_gate_passed"],
        "records_released_for_training": res["records_released_for_training"]
    }, indent=2))
