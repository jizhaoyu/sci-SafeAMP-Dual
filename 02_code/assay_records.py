"""Unified biological assay measurement representation and label derivation.

Separates raw measurements from discrete labels:
- measurement_present: Whether an assay record exists.
- endpoint_eligible: Whether target species/cell, metric, and units match criteria.
- label_observed: Whether a definitive binary label is derived.

Unknown reasons:
- not_measured
- incompatible_target
- incompatible_endpoint
- unsupported_unit
- ambiguous_censoring
- intermediate_range
- conflicting_measurements
- unsupported_modification
- unresolved_evidence
"""
from dataclasses import dataclass, field, asdict
import json
import math
from pathlib import Path
import re
from typing import Optional, Any
from feature_extractor import MOLECULAR_WEIGHTS, STANDARD_AMINO_ACIDS, clean_sequence
from research_utils import sha256


POSITIVE_CUTOFF_AMP = 32.0   # E. coli MIC <= 32 ug/ml
NEGATIVE_CUTOFF_AMP = 128.0  # E. coli MIC >= 128 ug/ml

POSITIVE_CUTOFF_HEMO = 100.0  # Human erythrocytes HC50 <= 100 ug/ml
NEGATIVE_CUTOFF_HEMO = 250.0  # Human erythrocytes HC50 >= 250 ug/ml


def parse_measurement_bounds(value_str: Any) -> Optional[tuple[float, float, str]]:
    """Parse numeric concentration bounds and operator.
    
    Returns (low, high, operator_type) or None if unparseable.
    operator_type in: 'exact', 'less_equal', 'greater_equal', 'interval'
    """
    if value_str is None:
        return None
    text = str(value_str).strip().replace('≤', '<=').replace('≥', '>=')
    number = r'(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
    
    # Check operator + number: <= X, < X, >= X, > X, = X, X
    m = re.fullmatch(r'([<>]=?|=)?\s*(' + number + r')', text)
    if m:
        op = m.group(1) or '='
        try:
            x = float(m.group(2))
        except ValueError:
            return None
        if x <= 0 or math.isnan(x) or math.isinf(x):
            return None
        if op in ('<=', '<'):
            return 0.0, x, 'less_equal'
        if op in ('>=', '>'):
            return x, math.inf, 'greater_equal'
        return x, x, 'exact'

    # Check interval: X - Y or X – Y
    m_int = re.fullmatch(r'(' + number + r')\s*[-–]\s*(' + number + r')', text)
    if m_int:
        try:
            low, high = float(m_int.group(1)), float(m_int.group(2))
        except ValueError:
            return None
        if 0 < low <= high and not (math.isnan(low) or math.isnan(high) or math.isinf(low) or math.isinf(high)):
            return low, high, 'interval'
            
    return None


def calculate_mw(sequence: str) -> float:
    """Calculate monoisotopic molecular weight of canonical linear peptide."""
    return sum(MOLECULAR_WEIGHTS[aa] for aa in sequence) - 18.0152 * (len(sequence) - 1)


def normalize_concentration_to_ug_ml(low: float, high: float, unit_str: str, sequence: str) -> Optional[tuple[float, float]]:
    """Convert concentration to ug/mL based on sequence molecular weight."""
    u = unit_str.replace('μ', 'u').replace('µ', 'u').lower().replace(' ', '')
    if u in ('ug/ml', 'mg/l', 'mcg/ml'):
        factor = 1.0
    elif u in ('um', 'micromolar', 'umol/l'):
        mw = calculate_mw(sequence)
        factor = mw / 1000.0  # (umol / L) * (g / mol) = ug / mL
    else:
        return None
    
    high_conv = math.inf if math.isinf(high) else high * factor
    return low * factor, high_conv


@dataclass
class SingleAssayObservation:
    endpoint: str            # 'amp' or 'hemo'
    target_organism_or_cell: str
    metric_name: str         # 'MIC', 'HC50', etc.
    raw_value: str
    raw_unit: str
    conditions: str = ''
    reference: str = ''
    
    # Derived properties
    eligible: bool = False
    ineligibility_reason: str = ''
    normalized_low_ug_ml: Optional[float] = None
    normalized_high_ug_ml: Optional[float] = None
    derived_label: Optional[int] = None   # 1, 0, or None


@dataclass
class StandardizedMoleculeRecord:
    record_id: str
    sequence: str
    source_dataset: str
    source_accession: str
    source_url: str
    source_role: str = 'development'
    evidence_reference: str = ''
    modifications: str = 'none'
    evidence_type: str = 'experimental'
    is_synthetic: bool = False
    raw_path: str = ''
    raw_sha256: str = ''
    
    observations: list[SingleAssayObservation] = field(default_factory=list)
    
    # Aggregated binary labels
    amp_label: Optional[int] = None
    hemo_label: Optional[int] = None
    
    amp_unknown_reasons: list[str] = field(default_factory=list)
    hemo_unknown_reasons: list[str] = field(default_factory=list)


def evaluate_assay_for_amp(assay: SingleAssayObservation, sequence: str) -> None:
    """Evaluate observation against E. coli MIC criteria."""
    if not any(assay.target_organism_or_cell.lower().startswith(ec) for ec in ['escherichia coli', 'e. coli']):
        assay.eligible = False
        assay.ineligibility_reason = 'incompatible_target'
        return

    if assay.metric_name.upper() not in ('MIC', 'MINIMUM INHIBITORY CONCENTRATION'):
        assay.eligible = False
        assay.ineligibility_reason = 'incompatible_endpoint'
        return

    parsed = parse_measurement_bounds(assay.raw_value)
    if parsed is None:
        assay.eligible = False
        assay.ineligibility_reason = 'ambiguous_censoring'
        return

    low, high, op = parsed
    conv = normalize_concentration_to_ug_ml(low, high, assay.raw_unit, sequence)
    if conv is None:
        assay.eligible = False
        assay.ineligibility_reason = 'unsupported_unit'
        return

    norm_low, norm_high = conv
    assay.normalized_low_ug_ml = norm_low
    assay.normalized_high_ug_ml = norm_high
    assay.eligible = True

    # Cutoffs: <= 32 positive, >= 128 negative
    if norm_high <= POSITIVE_CUTOFF_AMP:
        assay.derived_label = 1
    elif norm_low >= NEGATIVE_CUTOFF_AMP:
        assay.derived_label = 0
    else:
        assay.derived_label = None
        assay.ineligibility_reason = 'intermediate_range'


def evaluate_assay_for_hemo(assay: SingleAssayObservation, sequence: str) -> None:
    """Evaluate observation against Human Erythrocyte HC50 criteria."""
    target_clean = assay.target_organism_or_cell.lower()
    if 'human' not in target_clean or not any(rbc in target_clean for rbc in ['erythrocyte', 'red blood', 'rbc']):
        assay.eligible = False
        assay.ineligibility_reason = 'incompatible_target'
        return

    metric_clean = assay.metric_name.upper().replace(' ', '')
    if metric_clean not in ('HC50', '50%HEMOLYSIS', '50%HAEMOLYSIS'):
        assay.eligible = False
        assay.ineligibility_reason = 'incompatible_endpoint'
        return

    parsed = parse_measurement_bounds(assay.raw_value)
    if parsed is None:
        assay.eligible = False
        assay.ineligibility_reason = 'ambiguous_censoring'
        return

    low, high, op = parsed
    conv = normalize_concentration_to_ug_ml(low, high, assay.raw_unit, sequence)
    if conv is None:
        assay.eligible = False
        assay.ineligibility_reason = 'unsupported_unit'
        return

    norm_low, norm_high = conv
    assay.normalized_low_ug_ml = norm_low
    assay.normalized_high_ug_ml = norm_high
    assay.eligible = True

    # Cutoffs: <= 100 positive, >= 250 negative
    if norm_high <= POSITIVE_CUTOFF_HEMO:
        assay.derived_label = 1
    elif norm_low >= NEGATIVE_CUTOFF_HEMO:
        assay.derived_label = 0
    else:
        assay.derived_label = None
        assay.ineligibility_reason = 'intermediate_range'


def process_molecule_record(record: StandardizedMoleculeRecord) -> tuple[Optional[dict], Optional[str]]:
    """Validate sequence, evaluate observations, aggregate labels, and check conflicts."""
    clean_seq = clean_sequence(record.sequence)
    if not (10 <= len(clean_seq) <= 50) or set(clean_seq) - set(STANDARD_AMINO_ACIDS):
        return None, 'noncanonical_or_length'
    
    record.sequence = clean_seq

    amp_labels = set()
    hemo_labels = set()
    amp_reasons = []
    hemo_reasons = []

    for obs in record.observations:
        if obs.endpoint == 'amp':
            evaluate_assay_for_amp(obs, clean_seq)
            if obs.derived_label is not None:
                amp_labels.add(obs.derived_label)
            elif obs.ineligibility_reason:
                amp_reasons.append(obs.ineligibility_reason)
        elif obs.endpoint == 'hemo':
            evaluate_assay_for_hemo(obs, clean_seq)
            if obs.derived_label is not None:
                hemo_labels.add(obs.derived_label)
            elif obs.ineligibility_reason:
                hemo_reasons.append(obs.ineligibility_reason)

    # Determine final labels
    if len(amp_labels) == 1:
        record.amp_label = next(iter(amp_labels))
    elif len(amp_labels) > 1:
        record.amp_label = None
        record.amp_unknown_reasons.append('conflicting_measurements')
    else:
        record.amp_label = None
        record.amp_unknown_reasons.extend(amp_reasons or ['not_measured'])

    if len(hemo_labels) == 1:
        record.hemo_label = next(iter(hemo_labels))
    elif len(hemo_labels) > 1:
        record.hemo_label = None
        record.hemo_unknown_reasons.append('conflicting_measurements')
    else:
        record.hemo_label = None
        record.hemo_unknown_reasons.extend(hemo_reasons or ['not_measured'])

    if record.amp_label is None and record.hemo_label is None:
        return None, 'missing_or_conflicting_endpoints'

    # Build row matching REQUIRED contract
    row = {
        'record_id': record.record_id,
        'seq': record.sequence,
        'amp': record.amp_label,
        'hemo': record.hemo_label,
        'source_dataset': record.source_dataset,
        'source_accession': record.source_accession,
        'source_url': record.source_url,
        'evidence_reference': record.evidence_reference,
        'label_basis': 'Ecoli_MIC_ugml_32_128;human_HC50_ugml_100_250;conflicts_missing',
        'assay_conditions': json.dumps([asdict(o) for o in record.observations if o.eligible], ensure_ascii=False),
        'modifications': record.modifications,
        'evidence_type': record.evidence_type,
        'is_synthetic': record.is_synthetic,
        'source_role': record.source_role,
        'raw_path': record.raw_path,
        'raw_sha256': record.raw_sha256,
    }
    return row, None
