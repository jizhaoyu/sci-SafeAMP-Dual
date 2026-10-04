# Multi-Agent Mutation Engine Implementation Plan

> **For agentic workers:** Implement the plan with the available Codex tools and repository conventions. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a LangGraph-based multi-agent pipeline replacing the static `ai_optimize` endpoint.

**Architecture:** A 4-node state graph (Researcher, Biologist, Toxicology, Validator) with loopback routing.

**Tech Stack:** `langgraph`, `langchain-openai`, `biopython`

## Global Constraints
- All LLM outputs must use `temperature=0.0` (SEP-2026).
- Use `TypedDict` for State.

---

### Task 1: Environment & Setup

**Files:**
- Modify: `D:\桌面文件\sci\requirements.txt` (or pip install commands)
- Create: `D:\桌面文件\sci\02_code\agent_state.py`

- [ ] **Step 1: Install dependencies**
```bash
pip install langgraph langchain-openai biopython
```

- [ ] **Step 2: Define State Schema**
Create `D:\桌面文件\sci\02_code\agent_state.py`:
```python
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
```

### Task 2: Implement Tool & Action Nodes

**Files:**
- Create: `D:\桌面文件\sci\02_code\agent_tools.py`

- [ ] **Step 1: Implement PubMed Tool**
```python
# In agent_tools.py
from Bio import Entrez
Entrez.email = "admin@safeamp.org"

def search_pubmed(query: str) -> str:
    handle = Entrez.esearch(db="pubmed", term=query, retmax=3)
    record = Entrez.read(handle)
    handle.close()
    id_list = record["IdList"]
    if not id_list:
        return "No literature found."
    
    handle = Entrez.efetch(db="pubmed", id=id_list, rettype="medline", retmode="text")
    records = handle.read()
    handle.close()
    return records[:2000] # truncate to avoid token overload
```

- [ ] **Step 2: Implement Toxicology Node**
```python
# In agent_tools.py
from .ai_optimizer import SafeAMPDualNet, ESMFeatureExtractor
from .helical_wheel import compute_helical_wheel_data

# ... write the async toxicology_node function that takes state, runs the local models, and sets state['metrics']
```

### Task 3: Implement LLM Nodes & Graph

**Files:**
- Create: `D:\桌面文件\sci\02_code\mutation_graph.py`

- [ ] **Step 1: Implement Researcher, Biologist, Validator Nodes**
Write the LLM prompts and extraction logic using `langchain_openai.ChatOpenAI(model="deepseek-chat", temperature=0.0, ...)`.

- [ ] **Step 2: Build and Compile Graph**
Link nodes: `researcher -> biologist -> toxicology -> validator -> conditional_edge(biologist, END)`.

### Task 4: Integrate with FastAPI

**Files:**
- Modify: `D:\桌面文件\sci\05_web_server\app.py`

- [ ] **Step 1: Update API endpoint**
Modify `@app.post("/api/ai_optimize")` to `await graph.ainvoke(initial_state)`.
