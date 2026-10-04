from typing import TypedDict, Optional

class MutationState(TypedDict):
    original_sequence: str
    peptide_name: str
    literature_context: str
    current_candidate: str
    metrics: dict
    feedback: str
    step_count: int
    final_report: str
