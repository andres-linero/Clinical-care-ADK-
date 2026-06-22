# Clinical Care Coordination System

## Google ADK + BioGPT Multi-Agent Framework

## Portfolio Demo: Rule-Governed Agent Workflow

This repository includes a Streamlit demo designed for a non-technical
reviewer. It shows a clinical care coordination workflow with six agent
roles:

```text
Patient Intake
   |
   v
Triage Agent
   |
   v
Diagnosis Agent
   |
   v
Treatment Agent
   |
   +--> Documentation Agent
   |
   +--> Scheduling Agent
   |
   v
Follow-up Agent
```

Safety-critical decisions are not left to an LLM. The demo uses explicit
rules for:

- red-flag detection
- triage urgency
- escalation
- medication allergy checks
- drug interaction checks
- follow-up timing
- sandbox prompt testing for explainability

The agent layer coordinates the workflow and presents structured handoffs.
Any clinical diagnosis or treatment output is marked as requiring clinician
review.

### Run the Streamlit Demo

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Files used by the demo:

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Interactive demo UI |
| `rule_pipeline.py` | Deterministic workflow logic |
| `sample_patients.json` | Generated sample patient records loaded into a dataframe |
| `triage_agent.py` ... `followup_agent.py` | ADK agent role definitions |

The current demo uses generated local records for portability. In a production
version, that same source-data layer could be replaced by a warehouse table such
as BigQuery while keeping the rule-governed pipeline interface the same.

The `Logic Tester` tab lets reviewers test new symptom wording and patient IDs.
It prints the parameters, medication safety checks, model-style answer, and the
actual deterministic rule trace, making it clear why a patient is Level 2, 3,
or 4.

### Why This Design

Clinical workflows need guardrails. In this demo, LLM-style agents are not
trusted with safety-critical decisions. Instead, the pipeline uses structured
input and deterministic rules, then passes validated outputs between agent
steps.

---

## 📚 FILE STUDY ORDER

Study the files in this order to understand the system from foundation to complete workflow:

```
PHASE 1: FOUNDATION (Building Blocks)
├── 1. models/biogpt_wrapper.py    ← ML model integration
└── 2. tools/clinical_tools.py     ← Tools agents can use

PHASE 2: AGENTS (Learn Agent Patterns)
├── 3. agents/triage_agent.py      ← First agent, simplest example
├── 4. agents/diagnosis_agent.py   ← SEQUENTIAL pattern
├── 5. agents/treatment_agent.py   ← Tool-heavy agent
├── 6. agents/scheduling_agent.py  ← PARALLEL operations
├── 7. agents/documentation_agent.py ← Data aggregation
└── 8. agents/followup_agent.py    ← LOOP pattern

PHASE 3: COORDINATION (Everything Together)
├── 9. orchestrator.py             ← Master coordinator
└── 10. demo.py                    ← Running the system
```

---

## 📁 FILE EXPLANATIONS

### PHASE 1: FOUNDATION

#### 1️⃣ `models/biogpt_wrapper.py`
**Purpose:** Bridges your fine-tuned BioGPT with the agent system

**Why Important:**
- Encapsulates model complexity (loading, tokenization, generation)
- Provides consistent `generate()` interface for all agents
- Handles GPU/CPU device management
- Includes `MockBioGPT` for testing without loading a real model

**Key Classes:**
```python
BioGPTWrapper      # Real model wrapper
MockBioGPT         # For testing
create_biogpt_wrapper(use_mock=True)  # Factory function
```

---

#### 2️⃣ `tools/clinical_tools.py`
**Purpose:** Functions that agents can call to perform actions

**Why Important:**
- Tools extend agent capabilities beyond text generation
- ADK reads function docstrings to understand tools
- Each agent gets specific tools relevant to its role

**Available Tools:**
| Tool | Purpose |
|------|---------|
| `assess_symptoms()` | Analyze patient symptoms |
| `lookup_patient()` | Get patient records |
| `check_drug_interactions()` | Medication safety |
| `schedule_appointment()` | Book appointments |
| `send_alert()` | Notify care team |
| `generate_clinical_note()` | Create documentation |

---

### PHASE 2: AGENTS

#### 3️⃣ `agents/triage_agent.py`
**Purpose:** Entry point - assesses urgency and routes patients

**Pattern:** Basic ADK Agent

**Why Important:**
- Simplest agent to understand first
- Shows ADK Agent structure (instruction + tools)
- Demonstrates decision making (urgency levels)

**Key Concepts:**
```python
TRIAGE_INSTRUCTION = "..."  # System prompt
create_triage_agent()       # Factory function
check_red_flags()           # Quick safety check
format_triage_result()      # Structured output
```

---

#### 4️⃣ `agents/diagnosis_agent.py`
**Purpose:** Analyzes symptoms and generates differential diagnosis

**Pattern:** 🔄 SEQUENTIAL (receives Triage output)

**Why Important:**
- Shows how agents receive data from previous agents
- Demonstrates multi-step reasoning
- Integrates BioGPT for medical reasoning

**Key Concepts:**
```python
build_clinical_picture(triage_result, patient_data)
# ↑ Combines previous agent output with new data
```

---

#### 5️⃣ `agents/treatment_agent.py`
**Purpose:** Creates treatment plans with safety validation

**Pattern:** Tool-Heavy with Safety Gate

**Why Important:**
- Shows heavy tool usage (drug checks, patient lookup)
- Demonstrates validation pattern (pre/post checks)
- Safety can BLOCK workflow if issues found

**Key Concepts:**
```python
run_safety_checks()  # CRITICAL - must pass before treatment
# If fails → status: "safety_hold" → requires physician review
```

---

#### 6️⃣ `agents/scheduling_agent.py`
**Purpose:** Coordinates appointments and resources

**Pattern:** ⚡ PARALLEL (runs with Documentation)

**Why Important:**
- Runs at SAME TIME as Documentation agent
- Shows retry logic for unavailable slots
- Demonstrates external system integration

**Key Concepts:**
```python
# In orchestrator:
await asyncio.gather(
    run_documentation(...),
    run_scheduling(...)     # ← PARALLEL!
)
```

---

#### 7️⃣ `agents/documentation_agent.py`
**Purpose:** Generates clinical notes (SOAP, Progress, etc.)

**Pattern:** Data Aggregation

**Why Important:**
- Pulls data from ALL previous agents
- Shows template-based generation
- Multiple output formats

**Key Concepts:**
```python
aggregate_clinical_data(triage, diagnosis, treatment)
# ↑ Combines everything into one clinical picture
generate_soap_note(aggregated_data)
# ↑ Structured documentation output
```

---

#### 8️⃣ `agents/followup_agent.py`
**Purpose:** Continuous patient monitoring

**Pattern:** 🔁 LOOP (runs repeatedly)

**Why Important:**
- Maintains state across monitoring cycles
- Generates alerts when thresholds exceeded
- Re-engages patients who miss appointments

**Key Concepts:**
```python
class MonitoringState:
    # Tracks all patients being monitored
    
def run_monitoring_check(patient_id):
    # One iteration of the loop:
    # 1. Check status
    # 2. Generate alerts if needed
    # 3. Schedule next check
    # 4. REPEAT when due
```

---

### PHASE 3: COORDINATION

#### 9️⃣ `orchestrator.py`
**Purpose:** Master coordinator - ties everything together

**Pattern:** All patterns combined

**Why Important:**
- Creates and manages all agents
- Implements workflow execution
- Uses ADK Runner for agent execution
- Provides observability (status, history)

**Key Concepts:**
```python
class ClinicalCareOrchestrator:
    def __init__(self):
        self.agents = {...}   # All 6 agents
        self.runners = {...}  # ADK runners
        self.biogpt = ...     # Your model
        
    async def run_full_workflow(patient_data):
        # SEQUENTIAL
        triage → diagnosis → treatment
        
        # PARALLEL
        documentation + scheduling (together)
        
        # LOOP INIT
        followup monitoring setup
```

---

#### 🔟 `demo.py`
**Purpose:** Shows how to run the system

**Usage:**
```bash
python demo.py                    # Full demo with mock BioGPT
python demo.py --biogpt-path ...  # With your real model
python demo.py --triage-only      # Quick triage test
python demo.py --show-patterns    # Explain patterns
```

---

## 🔄 THE THREE PATTERNS

### 1. SEQUENTIAL Pattern
```
Agent A → Agent B → Agent C
   │          │         │
   └── Output flows forward
```
**Example:** Triage → Diagnosis → Treatment

### 2. PARALLEL Pattern
```
              ┌─→ Agent A ─┐
Input Data ──┤            ├──→ Combined Results
              └─→ Agent B ─┘
```
**Example:** Documentation + Scheduling run together

### 3. LOOP Pattern
```
       ┌──────────────────────┐
       │                      │
       ▼                      │
[Check Patients] → [Alerts?] → [Wait] ──┘
```
**Example:** Follow-up monitoring cycles

---

## 🚀 QUICK START

```python
from orchestrator import create_orchestrator

# Create system
orchestrator = create_orchestrator(use_mock_biogpt=True)

# Run workflow
patient = {
    "patient_id": "P001",
    "symptoms": "headache, fever",
    "age": 35
}
result = await orchestrator.run_full_workflow(patient)
```

---

## 📋 CAPSTONE REQUIREMENTS CHECKLIST

| Requirement | Where Demonstrated |
|-------------|-------------------|
| ✅ Multi-agent framework | All 6 agents |
| ✅ Sequential agents | Triage → Diagnosis → Treatment |
| ✅ Parallel agents | Documentation + Scheduling |
| ✅ Loop agents | Follow-up monitoring |
| ✅ Custom tools | `clinical_tools.py` |
| ✅ Google Search tool | Added to agents |
| ✅ Custom ML model | BioGPT integration |
| ✅ Sessions | ADK InMemoryRunner |
| ✅ Memory management | Monitoring state |
| ✅ Observability | Orchestrator status/history |

---

## 📖 LEARNING GUIDE

For detailed explanations with code examples, see:
**`LEARNING_GUIDE.ipynb`**
