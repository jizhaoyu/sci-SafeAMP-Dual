from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent_state import MutationState
from agent_tools import search_pubmed, run_toxicology_calc
import os
from dotenv import load_dotenv

# Load env before initializing LLM
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Initialize LLM with strict determinism (SEP-2026)
# Note: Users should configure os.environ["OPENAI_API_KEY"] and os.environ["OPENAI_API_BASE"] correctly.
llm = ChatOpenAI(
    model="deepseek-chat",
    temperature=0.0
)

def researcher_node(state: MutationState) -> MutationState:
    query = f"{state['peptide_name']} antimicrobial peptide mutation toxicity hemolysis"
    context = search_pubmed(query)
    state["literature_context"] = context
    return state

def biologist_node(state: MutationState) -> MutationState:
    # Use deterministic LLM to propose a mutation
    prompt = f"""You are a structural biologist agent.
Your task is to propose exactly one mutated sequence for the peptide '{state['peptide_name']}'.
Original Sequence: {state['original_sequence']}
Feedback from previous round: {state.get('feedback', 'None. This is the first round.')}

Literature Context for optimization:
{state.get('literature_context', 'No context provided.')}

Instructions:
1. Preserve the antimicrobial core.
2. Reduce hemolysis by disrupting the hydrophobic moment or adjusting net charge.
3. Respond with ONLY the raw uppercase mutated peptide sequence (e.g., GIGAVLKVLTTGLPALISWIKRKRQQ). Do NOT output any other text or markdown.
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    mutated_seq = response.content.strip().replace("\n", "").upper()
    state["current_candidate"] = mutated_seq
    
    # Increment step counter
    state["step_count"] = state.get("step_count", 0) + 1
    return state

def toxicology_node(state: MutationState) -> MutationState:
    metrics = run_toxicology_calc(state["current_candidate"])
    state["metrics"] = metrics
    return state

def validator_node(state: MutationState) -> MutationState:
    metrics = state["metrics"]
    
    prompt = f"""You are a strict toxicology validator (SEP-2026 Protocol).
Candidate Sequence: {state['current_candidate']}
Metrics:
- P_AMP: {metrics['p_amp']:.4f}
- P_Hemo: {metrics['p_hemo']:.4f}
- TSI: {metrics['tsi']:.4f}
- Net Charge: {metrics['net_charge']:.4f}
- Hydrophobic Moment: {metrics['hydrophobic_moment']:.4f}

Rules:
- P_Hemo must be < 0.5.
- P_AMP must be > 0.8.

Evaluate if the candidate passes. 
If it FAILS, output a brief chemical explanation starting with "REJECT:".
If it PASSES, output a structured final report starting with "ACCEPT:".
"""
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    
    if content.startswith("REJECT:"):
        state["feedback"] = content
        state["final_report"] = ""
    else:
        state["feedback"] = "SUCCESS"
        state["final_report"] = content
        
    return state

def router(state: MutationState) -> str:
    if state.get("feedback") == "SUCCESS":
        return END
    if state.get("step_count", 0) >= 3:
        return END
    return "biologist"

# Build the Graph
def build_mutation_graph():
    workflow = StateGraph(MutationState)
    
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("biologist", biologist_node)
    workflow.add_node("toxicology", toxicology_node)
    workflow.add_node("validator", validator_node)
    
    workflow.set_entry_point("researcher")
    
    workflow.add_edge("researcher", "biologist")
    workflow.add_edge("biologist", "toxicology")
    workflow.add_edge("toxicology", "validator")
    
    workflow.add_conditional_edges("validator", router)
    
    return workflow.compile()
