# Clinical Care ADK Workflow

A rule-governed multi-agent clinical care coordination prototype.

This project demonstrates how specialized agents can coordinate a patient case
from intake through triage, diagnosis drafting, treatment safety checks,
documentation, scheduling, and follow-up. The system returns different workflow
outputs depending on the patient's status, risk level, medications, allergies,
and detected red flags.

The demo is built to be understandable by both technical and non-technical
reviewers. It includes a Streamlit interface, generated sample patient records,
agent handoffs, and a logic tester that explains why each patient receives a
specific triage level.

Short version:

> This is a clinical care coordination agent workflow. The agents coordinate the
> work, but safety-critical decisions are handled by explicit rules so the system
> can explain why a patient was escalated, routed, held for safety review, or
> cleared for the next step.

## What It Does

The workflow starts from a patient record and produces a coordinated care plan.

```text
Patient Record
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

Each agent owns a specific part of the workflow and passes structured output to
the next step. The output changes based on patient state. For example:

- a patient with fever and neck stiffness is escalated for emergency clinical review
- a patient with chest pain and shortness of breath is escalated immediately
- a stable patient with no escalation rule match proceeds through a standard workflow
- a medication allergy conflict creates a safety review hold

## Why This Is Rule-Governed

Clinical workflows should not let an LLM freely decide safety-critical outcomes.
In this project, the model-style layer is used for explanation and workflow
presentation, while clinical risk decisions are controlled by deterministic
rules.

Rules own:

- red-flag detection
- triage level
- escalation requirement
- medication allergy checks
- drug interaction checks
- follow-up timing

The app also includes a `Logic Tester` tab. This lets a reviewer add a new test
case, ask a prompt, and see:

- which patient parameters were used
- which triage rules matched
- which escalation rules did not match
- why the patient is Level 2, 3, or 4
- why a medication was allowed or blocked
- a model-style explanation that does not override the deterministic result

## Agent Delegation

| Agent | Responsibility | Output Passed Forward |
|------|----------------|-----------------------|
| Triage Agent | Evaluates symptoms, red flags, urgency, and escalation rules | `urgency_level`, `red_flags`, `next_step`, `rule_hits` |
| Diagnosis Agent | Creates a draft differential focus from structured triage context | `differential_focus`, `clinician_review_required` |
| Treatment Agent | Drafts low-risk treatment actions and runs safety checks | `proposed_medications`, `safety_checks`, `status` |
| Documentation Agent | Converts structured workflow data into a SOAP-style clinical note | `soap_note`, `draft_requires_signature` |
| Scheduling Agent | Chooses timing and routing based on urgency | `appointment_type`, `recommended_timeframe`, `escalation_channel` |
| Follow-up Agent | Creates monitoring cadence and trigger conditions | `monitoring_interval`, `next_check_in`, `triggers` |

The agents are coordinated by the pipeline rather than operating independently.
That means each step receives the previous step's structured result and uses it
to decide what should happen next.

## Demo UI

Run the Streamlit demo:

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The Streamlit app includes:

- `Patient Queue`: select a patient ID from generated sample records
- `Patient Profile`: patient demographics, vitals, symptoms, medical history, medications, and allergies
- `Triage Rules`: the deterministic triage result and rule evidence
- `Logic Tester`: add new cases and inspect the reasoning behind triage/safety outcomes
- `Agent Workflow`: step-by-step agent handoff view
- `Care Plan`: diagnosis draft, treatment safety, scheduling, and follow-up
- `Documentation`: generated SOAP-style note
- `Data`: source dataframe, active patient row, and full pipeline payload

## Data Source

The current demo uses generated local patient records in `sample_patients.json`.
The Streamlit app loads those records into a dataframe and runs the workflow from
that structured source.

This is intentionally designed so the local data layer can be replaced later by
a production source such as BigQuery:

```text
sample_patients.json -> dataframe -> rule pipeline -> agent workflow

Production equivalent:
BigQuery table -> dataframe/API payload -> rule pipeline -> agent workflow
```

## Key Files

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Portfolio demo UI |
| `rule_pipeline.py` | Rule-governed workflow, triage logic, safety checks, and explainability helpers |
| `sample_patients.json` | Generated sample patient records |
| `triage_agent.py` | ADK triage agent role definition |
| `diagnosis_agent.py` | ADK diagnosis agent role definition |
| `treatment_agent.py` | ADK treatment planning agent role definition |
| `documentation_agent.py` | ADK documentation agent role definition |
| `scheduling_agent.py` | ADK scheduling agent role definition |
| `followup_agent.py` | ADK follow-up monitoring agent role definition |
| `clinical_tools.py` | Mock clinical tools for assessment, patient lookup, interactions, scheduling, alerts, and notes |
| `biogpt_wrapper.py` | BioGPT/mock BioGPT integration layer |
| `demo.py` | CLI demo entrypoint |

## Example Rule Logic

Triage starts at Level 4 unless a rule raises urgency.

Examples:

- chest pain + shortness of breath -> Level 1
- fever + neck stiffness -> Level 2
- single cardiopulmonary red flag -> Level 2
- persistent vomiting -> Level 3
- no urgent rule match -> Level 4

Medication safety checks compare proposed medications against:

- known allergies
- current medications
- known interaction pairs

If a blocker is found, the workflow returns `safety_review_required`.

## Current Scope

This is a portfolio prototype, not a clinical product. It uses generated data
and mock clinical tools. Diagnosis and treatment outputs are marked as drafts
requiring clinician review.

The purpose is to demonstrate:

- multi-agent workflow design
- structured handoffs between agents
- deterministic guardrails for safety-critical decisions
- explainable triage and medication safety logic
- a non-technical demo UI for reviewing the system behavior
