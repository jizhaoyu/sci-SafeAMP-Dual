"""Exercise the actual audit code, not copies of its predicates."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import evidence_audit as audit


class EvidenceAuditTests(unittest.TestCase):
    def test_dermatoxin_primary_sequence_and_all_ecoli_assays(self):
        records = {c['candidate_id']: c for c in audit.read_primary(audit.RAW)}
        c = records['PMC_42653830']
        self.assertEqual(c['sequence'], 'SLGSFLKGVGKGLATVGKIVADQFGKLLEAGK')
        self.assertEqual([a['raw_value'] for a in c['assays'] if a['endpoint'] == 'MIC'], ['4', '2', '2'])
        self.assertEqual(c['assays'][-1]['target'], 'Horse erythrocytes')
        self.assertFalse(audit.is_human_hc50(c['assays'][-1]))

    def test_arg2_primary_sequence_mic_and_rabbit_target(self):
        c = next(c for c in audit.read_primary(audit.RAW) if c['candidate_id'] == 'PMC_42370696')
        self.assertEqual(c['sequence'], 'LRLKALLAVAKKIL')
        self.assertEqual(c['assays'][0]['raw_value'], '2')
        self.assertEqual(c['assays'][0]['unit'], 'µM')
        self.assertEqual(c['assays'][1]['target'], 'Rabbit erythrocytes')

    def test_han_no_effect_not_invented_numeric_mic(self):
        c = next(c for c in audit.read_primary(audit.RAW) if c['candidate_id'] == 'PMC_42221479')
        self.assertEqual(c['assays'][0]['raw_value'], 'No effect')
        self.assertEqual(c['sequence'], '')
        self.assertEqual(audit.label_assay(c['assays'][0], c)['label'], 'unknown')

    def test_brevinin_censored_mic_and_hc50_unknown(self):
        c = next(c for c in audit.read_primary(audit.RAW) if c['candidate_id'] == 'PMC_40864826')
        self.assertEqual(c['sequence'], 'FLGALFKVASKLVPAAICSFSKKC')
        self.assertEqual(c['assays'][0]['raw_value'], '>24.8')
        self.assertEqual(c['assays'][1]['raw_value'], '41.87')
        self.assertTrue(audit.is_human_hc50(c['assays'][1]))
        self.assertEqual([audit.label_assay(a, c)['label'] for a in c['assays']], ['unknown', 'unknown'])

    def test_unverified_measurement_cannot_make_label(self):
        a = {'endpoint': 'MIC', 'target': 'Escherichia coli', 'raw_value': '1', 'unit': 'µg/ml', 'reviewed': False}
        self.assertEqual(audit.label_assay(a, {})['label'], 'unknown')

    def test_non_ecoli_mic_cannot_make_label(self):
        a = {'endpoint': 'MIC', 'target': 'Staphylococcus aureus', 'raw_value': '1', 'unit': 'µg/ml', 'reviewed': True}
        self.assertEqual(audit.label_assay(a, {})['label'], 'unknown')

    def test_single_concentration_and_cell_death_not_hc50(self):
        for endpoint in ('single_concentration_percentage', 'CC50', 'IC50'):
            a = {'endpoint': endpoint, 'target': 'Human erythrocytes', 'raw_value': '50', 'unit': 'µg/ml', 'reviewed': True}
            self.assertFalse(audit.is_human_hc50(a))
            self.assertEqual(audit.label_assay(a, {})['label'], 'unknown')

    def test_censored_and_threshold_boundaries(self):
        for raw, endpoint, label in [('32', 'MIC', 1), ('128', 'MIC', 0), ('>10', 'MIC', 'unknown'), ('100', 'HC50', 1), ('250', 'HC50', 0)]:
            a = {'endpoint': endpoint, 'target': 'Human erythrocytes' if endpoint == 'HC50' else 'Escherichia coli', 'raw_value': raw, 'unit': 'µg/ml', 'reviewed': True}
            self.assertEqual(audit.label_assay(a, {})['label'], label)

    def test_unknown_units_or_mass_not_guessed(self):
        for unit in ('unknown', 'µM'):
            a = {'endpoint': 'MIC', 'target': 'Escherichia coli', 'raw_value': '1', 'unit': unit, 'reviewed': True}
            self.assertEqual(audit.label_assay(a, {})['label'], 'unknown')

    def test_conflicting_labels_block(self):
        self.assertEqual(audit.resolve_labels([1, 0]), 'conflict')
        self.assertEqual(audit.resolve_labels([1, 'unknown']), 'unknown')
        self.assertEqual(audit.resolve_labels([1, 1]), 1)

    def test_zero_point_four_actual_alignment_is_blocked(self):
        pairs, maxima = audit.similarities([{'candidate_id': 'c', 'sequence': 'AAAACCCCCC'}], [{'record_id': 'd', 'seq': 'AAAADDDDDD'}])
        self.assertEqual(pairs[0]['identity'], .4)
        self.assertTrue(pairs[0]['violates_cutoff'])
        self.assertEqual(audit.homology_status(maxima['c'][0], True), 'failed')
        self.assertEqual(audit.homology_status(.2, False), 'pending_sequence_review')

    def test_gap_and_duplicate_alignment(self):
        pairs, _ = audit.similarities([{'candidate_id': 'c', 'sequence': 'AAAA'}], [{'record_id': 'd', 'seq': 'AAAAAA'}, {'record_id': 'e', 'seq': 'AAAA'}])
        self.assertAlmostEqual(pairs[0]['identity'], 4 / 6)
        self.assertEqual(pairs[1]['identity'], 1)

    def test_doi_alias_normalization(self):
        self.assertEqual(audit.normalize_alias('https://doi.org/10.1000/ABC'), 'doi:10.1000/abc')
        self.assertEqual(audit.normalize_alias('PMID:123'), 'pmid:123')

    def test_input_tampering_is_rejected_by_real_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = root / 'source.txt'
            p.write_text('original', encoding='utf-8')
            bindings = {'files': {'source.txt': hashlib.sha256(p.read_bytes()).hexdigest()}, 'required_files': ['source.txt']}
            audit.verify_bindings(root, bindings)
            p.write_text('tampered', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                audit.verify_bindings(root, bindings)

    def test_missing_coverage_and_path_escape_rejected(self):
        for bindings in ({'files': {}, 'required_files': ['missing.xml']}, {'files': {'../outside': 'a' * 64}, 'required_files': ['../outside']}):
            with self.assertRaises(ValueError):
                audit.verify_bindings(audit.ROOT, bindings)

    def test_existing_output_rejected_before_reading_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(audit, 'load_inputs', side_effect=AssertionError('must not read')):
                with self.assertRaises(FileExistsError):
                    audit.run(Path('missing'), 'bad', Path(temp))

    def test_bad_manifest_anchor_prevents_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = Path(temp) / 'manifest.json'
            manifest.write_text('{}', encoding='utf-8')
            out = Path(temp) / 'out'
            with self.assertRaisesRegex(ValueError, 'anchor'):
                audit.run(manifest, '0' * 64, out)
            self.assertFalse(out.exists())

    def test_actual_gates_require_all_conditions(self):
        c = {'source_reviewed': True, 'sequence_verified': True, 'sequence': 'AAAACCCCCC', 'molecular_form': 'linear_unmodified_free_ends_L'}
        self.assertEqual(audit.candidate_decision(c, 1, 0, .2, 'passed')['gate_decision'], 'candidate_ready_for_independent_review')
        for mic, hemo, identity, study in [('unknown', 0, .2, 'passed'), (1, 0, .4, 'passed'), (1, 0, .2, 'pending_measurement_study_alias_review')]:
            self.assertNotEqual(audit.candidate_decision(c, mic, hemo, identity, study)['gate_decision'], 'candidate_ready_for_independent_review')
        c['molecular_form'] = 'c_terminal_amide'
        self.assertEqual(audit.candidate_decision(c, 1, 0, .2, 'passed')['molecule_status'], 'failed')

    def test_end_to_end_no_fit_and_tampered_artifact_rejected(self):
        from contextlib import ExitStack
        from sklearn.linear_model import LogisticRegression
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.dummy import DummyClassifier
        from sklearn.preprocessing import StandardScaler
        manifest = audit.BUNDLE / 'input_manifest.json'
        with tempfile.TemporaryDirectory() as temp, ExitStack() as stack:
            for cls in (LogisticRegression, RandomForestClassifier, DummyClassifier, StandardScaler):
                stack.enter_context(patch.object(cls, 'fit', side_effect=AssertionError('fit forbidden')))
            stack.enter_context(patch('socket.create_connection', side_effect=AssertionError('network forbidden')))
            out = Path(temp) / 'results'
            result = audit.run(manifest, audit.sha(manifest), out)
            self.assertEqual(audit.validate_output(out), result)
            self.assertEqual(result['counts']['verified_human_hc50'], 1)
            self.assertEqual(result['counts']['pending_primary_article_review'], 78)
            self.assertEqual(result['counts']['eligible_external'], 0)
            self.assertEqual(result['counts']['missing_sequence'], 1)
            self.assertEqual(result['counts']['candidate_development_comparisons'], 82 * 417)
            self.assertEqual(result['model_fit_calls'], 0)
            self.assertIn('待原文复核 78 条', (out / 'report.md').read_text(encoding='utf-8'))
            with self.assertRaises(FileExistsError):
                audit.run(manifest, audit.sha(manifest), out)
            (out / 'report.md').write_text('tampered', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'SHA256'):
                audit.validate_output(out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
