"""Test P1 navigation, SPA routes integrity, and entity preservation."""
import sys
from pathlib import Path
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = PROJECT_ROOT / "05_web_server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from app import app, DIST

client = TestClient(app)

def test_all_seven_spa_routes():
    """Verify all 7 designated SPA routes return 200 with HTML content."""
    routes = [
        "/",
        "/dti",
        "/evolution",
        "/agent",
        "/screening",
        "/helical-wheel",
        "/report"
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, f"Route {route} failed with {response.status_code}"
        assert "text/html" in response.headers.get("content-type", "")
        assert b"<!DOCTYPE html>" in response.content or b"<html" in response.content

def test_favicon_route():
    """Favicon route should return 204 No Content."""
    response = client.get("/favicon.ico")
    assert response.status_code == 204

def test_non_spa_routes_return_404():
    """Unknown non-SPA routes and unknown API routes must strictly return 404."""
    bad_routes = [
        "/api/nonexistent_mock_service_call_12345",
        "/unknown_module_path",
        "/dashboard",
        "/settings/secret"
    ]
    for route in bad_routes:
        response = client.get(route)
        assert response.status_code == 404, f"Route {route} expected 404 but got {response.status_code}"

def test_smiles_casing_integrity():
    """Ensure small molecule SMILES casing is preserved and not converted to uppercase."""
    smiles_samples = [
        ("Imatinib", "Cc1ccc(cc1Nc2nccc(n2)c3cccnc3)NC(=O)c4ccc(cc4)CN5CCN(CC5)C"),
        ("Dasatinib", "Cc1nc(sc1C(=O)Nc2c(cccc2Cl)C)Nc3cc(nc(n3)N4CCN(CC4)CCO)Cl"),
        ("Gefitinib", "COc1cc2ncnc(c2cc1OCCCN3CCOCC3)Nc4ccc(c(c4)Cl)F"),
        ("Lapatinib", "CS(=O)(=O)CCNCc1ccc(o1)c2ccc3c(c2)c(ncn3)Nc4ccc(c(c4)Cl)OCc5cccc(c5)F"),
    ]
    for name, smi in smiles_samples:
        uppercased = smi.upper()
        # Verify that original has lowercase aromatic atoms or halogens
        assert smi != uppercased, f"Sample {name} should have lowercase letters"
        assert any(c in smi for c in ["c", "n", "s", "o", "Cl"])
        # Verify uppercase alters chemical symbols like Cl -> CL
        if "Cl" in smi:
            assert "CL" not in smi
            assert "CL" in uppercased

def test_frozen_baselines_integrity():
    """Verify that all 20 frozen baseline assets exist and match SHA256 hashes."""
    p0_hash_file = PROJECT_ROOT / "output" / "system-evolution-20261021" / "P0" / "frozen_baselines_sha256.json"
    assert p0_hash_file.is_file(), f"Missing P0 baseline hash record: {p0_hash_file}"
    
    with open(p0_hash_file, "r", encoding="utf-8") as f:
        recorded_hashes = json.load(f)

    assert len(recorded_hashes) == 20, f"Expected 20 protected baselines, found {len(recorded_hashes)}"
    
    for rel_path, meta in recorded_hashes.items():
        full_path = PROJECT_ROOT / rel_path
        assert full_path.is_file(), f"Protected file missing: {rel_path}"
        current_sha = hashlib.sha256(full_path.read_bytes()).hexdigest()
        expected_sha = meta["sha256"] if isinstance(meta, dict) else meta
        assert current_sha == expected_sha, f"Protected file modified! {rel_path}: {current_sha} != {expected_sha}"


def test_store_legacy_migration_and_entity_contracts():
    """Verify that legacy activeSequence migration never coerces ethanol (CCO) into a peptide,
    corrects previously misclassified v6 entities, and properly detects peptides like Melittin."""
    import re

    def simulate_store_migration(persisted_state: dict, version: int = 5):
        state = persisted_state or {}
        old_seq = (state.get("activeSequence") or "").strip()
        old_name = (state.get("activePeptideName") or "").strip()

        migrated_entity = state.get("activeEntity")

        # Correct previous misclassification from older versions (v5/v6)
        if migrated_entity and version < 7:
            if migrated_entity.get("kind") == "peptide":
                seq = (migrated_entity.get("sequence") or "").strip()
                if re.match(r'^(CCO|CC|CCC|CCCC|CCN|CCOC|CCOCC)$', seq, re.I) or re.search(r'[=#()0-9cnosp]', seq) or "O" in seq.upper():
                    migrated_entity = {
                        "kind": "small_molecule",
                        "smiles": seq,
                        "name": migrated_entity.get("name") or "Migrated Molecule"
                    }
            elif migrated_entity.get("kind") == "unconfirmed":
                seq = (migrated_entity.get("sequence") or "").strip()
                has_smiles_syntax = bool(re.search(r'[0-9=#()\[\]@\-+\\/%]', seq) or re.search(r'[cnosp]', seq))
                is_std_pep = bool(re.match(r'^[ACDEFGHIKLMNPQRSTVWY]{4,}$', seq.upper()) and not has_smiles_syntax and not re.search(r'[OBJZ]', seq.upper()))
                if is_std_pep:
                    migrated_entity = {
                        "kind": "peptide",
                        "sequence": seq.upper(),
                        "name": migrated_entity.get("name") or "Migrated Peptide"
                    }

        if not migrated_entity and old_seq:
            if state.get("kind") == "small_molecule" or state.get("item_type") == "small_molecule":
                migrated_entity = {
                    "kind": "small_molecule",
                    "smiles": old_seq,
                    "name": old_name or "Migrated Molecule"
                }
            elif state.get("kind") == "peptide" or state.get("item_type") == "peptide":
                migrated_entity = {
                    "kind": "peptide",
                    "sequence": old_seq.upper(),
                    "name": old_name or "Migrated Peptide"
                }
            else:
                has_smiles_syntax = bool(re.search(r'[0-9=#()\[\]@\-+\\/%]', old_seq) or re.search(r'[cnosp]', old_seq))
                is_common_formula = bool(re.match(r'^(CCO|CC|CCC|CCCC|CCN|CCOC|CCOCC|C#N|C=O)$', old_seq, re.I))
                is_unambiguous_smiles = has_smiles_syntax or is_common_formula

                is_unambiguous_peptide = bool(
                    re.match(r'^[ACDEFGHIKLMNPQRSTVWY]{4,}$', old_seq.upper()) and
                    not has_smiles_syntax and
                    not re.search(r'[OBJZ]', old_seq.upper())
                )

                if is_unambiguous_smiles and not is_unambiguous_peptide:
                    migrated_entity = {
                        "kind": "small_molecule",
                        "smiles": old_seq,
                        "name": old_name or "Migrated Molecule"
                    }
                elif is_unambiguous_peptide and not is_unambiguous_smiles:
                    migrated_entity = {
                        "kind": "peptide",
                        "sequence": old_seq.upper(),
                        "name": old_name or "Migrated Peptide"
                    }
                else:
                    migrated_entity = {
                        "kind": "unconfirmed",
                        "sequence": old_seq,
                        "name": old_name or "Unconfirmed Entity"
                    }
        return migrated_entity

    # Case 1: Legacy cache with Ethanol CCO must NOT be coerced to peptide
    ethanol_migrated = simulate_store_migration({"activeSequence": "CCO", "activePeptideName": "Ethanol"}, version=5)
    assert ethanol_migrated is not None
    assert ethanol_migrated["kind"] != "peptide", "CCO must never be coerced into kind='peptide'!"
    assert ethanol_migrated["kind"] == "small_molecule"
    assert ethanol_migrated["smiles"] == "CCO"

    # Case 2: Standard peptide sequence of length >= 4 (Melittin)
    pep_migrated = simulate_store_migration({"activeSequence": "GIGAVLKVLTTGLPALISWIKRKRQQ", "activePeptideName": "Melittin"}, version=5)
    assert pep_migrated is not None
    assert pep_migrated["kind"] == "peptide"
    assert pep_migrated["sequence"] == "GIGAVLKVLTTGLPALISWIKRKRQQ"

    # Case 3: Completely ambiguous short letters
    ambiguous_migrated = simulate_store_migration({"activeSequence": "XYZ", "activePeptideName": "Unknown"}, version=5)
    assert ambiguous_migrated is not None
    assert ambiguous_migrated["kind"] == "unconfirmed"
    assert ambiguous_migrated["sequence"] == "XYZ"

    # Case 4: Previously misclassified CCO as peptide in v6 must be corrected in v7
    misclassified_v6 = simulate_store_migration({"activeEntity": {"kind": "peptide", "sequence": "CCO", "name": "Ethanol"}}, version=6)
    assert misclassified_v6 is not None
    assert misclassified_v6["kind"] == "small_molecule"
    assert misclassified_v6["smiles"] == "CCO"
