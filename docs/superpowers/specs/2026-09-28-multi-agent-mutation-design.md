# SafeAMP-Dual 3.0 LangGraph Multi-Agent Mutation Engine Design

## Goal
Upgrade the backend AI Optimizer to a robust, loop-based Multi-Agent system using LangGraph. The system will take a native peptide, retrieve literature via PubMed, propose mutations, calculate scientific metrics via the existing SafeAMP-Dual models, and validate them through an AI validator until physical criteria are met.

## Architecture

**State Schema (`MutationState`):**
- `original_sequence: str`
- `peptide_name: str`
- `literature_context: str`
- `current_candidate: str`
- `metrics: dict`
- `feedback: str`
- `step_count: int`
- `final_report: str`

**Agents & Nodes:**
1. **Researcher Node:** Uses `Bio.Entrez` to search PubMed for `<peptide_name> AMP mutation toxicity`. Summarizes the abstracts and populates `literature_context`. Runs exactly once.
2. **Biologist Node:** Uses LLM (`temperature=0.0`) to propose a new sequence, leveraging `literature_context`, `original_sequence`, and `feedback`.
3. **Toxicology Node:** A pure Python node that computes $P_{Hemo}$, $P_{AMP}$, charge, and hydrophobic moment using the existing `ai_optimizer` and `helical_wheel` modules. Populates `metrics`.
4. **Validator Node:** Uses LLM (`temperature=0.0`) to evaluate `metrics`. If Hemolysis is too high or AMP too low, it generates `feedback` and routes back to the Biologist. If successful, it generates the `final_report`.

**Routing Constraints:**
- The graph stops and returns the best candidate if `step_count > 3` (prevent infinite loops).

## Implementation Rules
- Must use `typing.TypedDict` for the State.
- Must maintain SEP-2026 determinism protocols for LLM responses.
- Backend FastAPI endpoint `/api/ai_optimize` will be updated to execute this graph.
