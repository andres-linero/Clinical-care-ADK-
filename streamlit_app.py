"""
Streamlit demo for the rule-governed clinical care agent workflow.

Run:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from rule_pipeline import (
    FLAG_LABELS,
    explain_triage_decision,
    run_rule_pipeline,
    run_sandbox_triage_agent,
)


DATA_PATH = Path(__file__).with_name("sample_patients.json")


CSS = """
<style>
    :root {
        --panel: rgba(255, 255, 255, 0.045);
        --panel-strong: rgba(255, 255, 255, 0.075);
        --line: rgba(255, 255, 255, 0.14);
        --text-soft: rgba(255, 255, 255, 0.72);
        --accent: #38bdf8;
        --ok: #22c55e;
        --warn: #f59e0b;
        --danger: #ef4444;
    }

    .block-container {
        padding-top: 2rem;
        max-width: 1280px;
    }

    .hero {
        border: 1px solid var(--line);
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.14), rgba(34, 197, 94, 0.08));
        border-radius: 8px;
        padding: 1.25rem 1.35rem;
        margin-bottom: 1.25rem;
    }

    .hero h1 {
        font-size: 2rem;
        line-height: 1.1;
        margin: 0 0 0.45rem 0;
        letter-spacing: 0;
    }

    .hero p {
        color: var(--text-soft);
        font-size: 1rem;
        margin: 0;
    }

    .metric-card,
    .profile-card,
    .timeline-step,
    .summary-card {
        border: 1px solid var(--line);
        background: var(--panel);
        border-radius: 8px;
        padding: 1rem;
        height: 100%;
    }

    .metric-label,
    .card-label {
        color: var(--text-soft);
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.35rem;
    }

    .metric-value {
        font-size: 1.45rem;
        font-weight: 700;
        line-height: 1.2;
        overflow-wrap: anywhere;
    }

    .card-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.55rem;
    }

    .soft {
        color: var(--text-soft);
    }

    .kv {
        display: grid;
        grid-template-columns: minmax(110px, 0.42fr) 1fr;
        gap: 0.45rem 0.9rem;
        align-items: start;
        font-size: 0.95rem;
    }

    .kv .key {
        color: var(--text-soft);
    }

    .pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.45rem;
    }

    .pill {
        display: inline-flex;
        align-items: center;
        border: 1px solid var(--line);
        background: var(--panel-strong);
        border-radius: 999px;
        padding: 0.3rem 0.62rem;
        font-size: 0.86rem;
        line-height: 1.1;
    }

    .pill.ok { border-color: rgba(34, 197, 94, 0.55); color: #86efac; }
    .pill.warn { border-color: rgba(245, 158, 11, 0.65); color: #fcd34d; }
    .pill.danger { border-color: rgba(239, 68, 68, 0.65); color: #fca5a5; }
    .pill.info { border-color: rgba(56, 189, 248, 0.55); color: #7dd3fc; }

    .timeline-step {
        margin-bottom: 0.75rem;
    }

    .timeline-top {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
        margin-bottom: 0.35rem;
    }

    .timeline-title {
        font-weight: 700;
        font-size: 1rem;
    }

    .mini-list {
        margin: 0.35rem 0 0 0;
        padding-left: 1.1rem;
    }

    .mini-list li {
        margin: 0.2rem 0;
    }

    div[data-testid="stMetricValue"] {
        font-size: 1.35rem;
    }
</style>
"""


def load_examples() -> list[dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_patient_dataframe() -> pd.DataFrame:
    records = load_examples()
    rows = []
    for record in records:
        vitals = record.get("vitals", {})
        rows.append(
            {
                "patient_id": record["patient_id"],
                "scenario": record["label"],
                "name": record["name"],
                "age": record["age"],
                "gender": record["gender"],
                "visit_type": record.get("visit_type", ""),
                "symptoms": record["symptoms"],
                "duration_days": record["duration_days"],
                "pain_score": record["pain_score"],
                "medical_history": ", ".join(record.get("medical_history", [])),
                "medications": ", ".join(record.get("medications", [])),
                "allergies": ", ".join(record.get("allergies", [])),
                "red_flags": ", ".join(FLAG_LABELS.get(flag, flag) for flag in record.get("selected_red_flags", [])),
                "temperature_f": vitals.get("temperature_f"),
                "heart_rate": vitals.get("heart_rate"),
                "blood_pressure": vitals.get("blood_pressure"),
                "oxygen_saturation": vitals.get("oxygen_saturation"),
                "primary_care_provider": record.get("primary_care_provider", ""),
                "preferred_language": record.get("preferred_language", ""),
            }
        )
    return pd.DataFrame(rows)


def without_label(case: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in case.items() if key != "label"}


def split_lines(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def esc(value: Any) -> str:
    return html.escape(str(value))


def pill(label: str, tone: str = "info") -> str:
    return f'<span class="pill {tone}">{esc(label)}</span>'


def pills(items: list[str], tone: str = "info", empty: str = "None") -> str:
    values = items or [empty]
    return '<div class="pill-row">' + "".join(pill(item, tone) for item in values) + "</div>"


def metric_card(label: str, value: str, tone: str = "info") -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{esc(label)}</div>
        <div class="metric-value">{esc(value)}</div>
        <div class="pill-row">{pill(tone.title(), tone if tone in {"ok", "warn", "danger", "info"} else "info")}</div>
    </div>
    """


def profile_card(title: str, rows: list[tuple[str, Any]]) -> str:
    body = "".join(
        f'<div class="key">{esc(key)}</div><div>{esc(value)}</div>'
        for key, value in rows
    )
    return f"""
    <div class="profile-card">
        <div class="card-title">{esc(title)}</div>
        <div class="kv">{body}</div>
    </div>
    """


def summary_card(title: str, text: str, tags: list[str] | None = None, tone: str = "info") -> str:
    tag_html = pills(tags or [], tone) if tags else ""
    return f"""
    <div class="summary-card">
        <div class="card-title">{esc(title)}</div>
        <div class="soft">{esc(text)}</div>
        {tag_html}
    </div>
    """


def timeline_step(number: int, title: str, status: str, summary: str, tone: str = "info") -> str:
    return f"""
    <div class="timeline-step">
        <div class="timeline-top">
            <div class="timeline-title">{number}. {esc(title)}</div>
            {pill(status.replace("_", " ").title(), tone)}
        </div>
        <div class="soft">{esc(summary)}</div>
    </div>
    """


def tone_for_status(status: str) -> str:
    if "escalation" in status or "safety" in status:
        return "danger"
    if "urgent" in status or "review" in status or "pending" in status:
        return "warn"
    return "ok"


def main() -> None:
    st.set_page_config(
        page_title="Clinical Care ADK Demo",
        page_icon="",
        layout="wide",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    examples = load_examples()
    patient_df = load_patient_dataframe()
    patient_ids = [case["patient_id"] for case in examples]

    with st.sidebar:
        st.header("Patient Queue")
        selected_patient_id = st.radio(
            "Active patient ID",
            patient_ids,
            label_visibility="collapsed",
        )
        st.caption("Select the patient record to run through the workflow.")

    selected_record = next(case for case in examples if case["patient_id"] == selected_patient_id)
    selected_label = selected_record["label"]
    selected_case = without_label(selected_record)
    key = selected_case["patient_id"]

    st.markdown(
        """
        <div class="hero">
            <h1>Clinical Care ADK Workflow</h1>
            <p>Rule-governed multi-agent coordination: triage, diagnosis draft, treatment safety, documentation, scheduling, and follow-up.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        st.markdown("### Patient Record Loaded From Sample Data")
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="card-label">Selected Patient ID</div>
                <div class="metric-value">{esc(key)}</div>
                <div class="soft" style="margin-top:0.35rem;">{esc(selected_label)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        source_cols = st.columns([1, 1, 1, 1])
        with source_cols[0]:
            st.metric("Source", "sample_patients")
        with source_cols[1]:
            st.metric("Rows", len(patient_df))
        with source_cols[2]:
            st.metric("Active Record", key)
        with source_cols[3]:
            st.metric("Decision Mode", "Rules")

        st.caption(
            "Demo data is generated locally as a dataframe. In production this layer "
            "would be replaced by a warehouse table such as BigQuery."
        )

    patient_id = selected_case["patient_id"]
    name = selected_case["name"]
    age = int(selected_case["age"])
    gender = selected_case["gender"]
    symptoms = selected_case["symptoms"]
    duration_days = int(selected_case["duration_days"])
    pain_score = int(selected_case["pain_score"])
    medical_history = selected_case["medical_history"]
    medications = selected_case["medications"]
    allergies = selected_case["allergies"]
    selected_flags = selected_case["selected_red_flags"]
    primary_care_provider = selected_case.get("primary_care_provider", "Unassigned")
    preferred_language = selected_case.get("preferred_language", "English")
    visit_type = selected_case.get("visit_type", "New concern")
    vitals_seed = selected_case.get("vitals", {})
    temperature_f = float(vitals_seed.get("temperature_f", 98.6))
    heart_rate = int(vitals_seed.get("heart_rate", 76))
    blood_pressure = vitals_seed.get("blood_pressure", "120/80")
    oxygen_saturation = int(vitals_seed.get("oxygen_saturation", 99))

    patient = {
        "patient_id": patient_id,
        "name": name,
        "age": int(age),
        "gender": gender,
        "symptoms": symptoms,
        "duration_days": int(duration_days),
        "pain_score": int(pain_score),
        "medical_history": medical_history,
        "medications": medications,
        "allergies": allergies,
        "selected_red_flags": selected_flags,
        "primary_care_provider": primary_care_provider,
        "preferred_language": preferred_language,
        "visit_type": visit_type,
        "vitals": {
            "temperature_f": round(float(temperature_f), 1),
            "heart_rate": int(heart_rate),
            "blood_pressure": blood_pressure,
            "oxygen_saturation": int(oxygen_saturation),
        },
    }

    result = run_rule_pipeline(patient)
    steps = result["steps"]
    triage = steps["triage"]
    diagnosis = steps["diagnosis"]
    treatment = steps["treatment"]
    documentation = steps["documentation"]
    scheduling = steps["scheduling"]
    followup = steps["followup"]

    status_tone = tone_for_status(result["status"])
    safety_tone = "ok" if treatment["safety_checks"]["passed"] else "danger"
    escalation_tone = "danger" if triage["escalation_required"] else "ok"

    metric_cols = st.columns(4)
    cards = [
        metric_card("Workflow", result["status"].replace("_", " ").title(), status_tone),
        metric_card("Urgency", f"Level {triage['urgency_level']}", "danger" if triage["urgency_level"] <= 2 else "warn" if triage["urgency_level"] == 3 else "ok"),
        metric_card("Escalation", "Required" if triage["escalation_required"] else "Not Required", escalation_tone),
        metric_card("Safety", "Passed" if treatment["safety_checks"]["passed"] else "Hold", safety_tone),
    ]
    for col, card in zip(metric_cols, cards):
        with col:
            st.markdown(card, unsafe_allow_html=True)

    tab_profile, tab_triage, tab_sandbox, tab_workflow, tab_care, tab_note, tab_data = st.tabs(
        [
            "Patient Profile",
            "Triage Rules",
            "Logic Tester",
            "Agent Workflow",
            "Care Plan",
            "Documentation",
            "Data",
        ]
    )

    with tab_profile:
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(
                profile_card(
                    "Demographics",
                    [
                        ("Scenario", selected_label),
                        ("Patient", f"{patient['name']} ({patient['patient_id']})"),
                        ("Age / Gender", f"{patient['age']} / {patient['gender']}"),
                        ("Language", patient["preferred_language"]),
                        ("Provider", patient["primary_care_provider"]),
                        ("Visit type", patient["visit_type"]),
                    ],
                ),
                unsafe_allow_html=True,
            )
        with p2:
            vitals = patient["vitals"]
            st.markdown(
                profile_card(
                    "Vitals",
                    [
                        ("Temperature", f"{vitals['temperature_f']} F"),
                        ("Heart rate", f"{vitals['heart_rate']} bpm"),
                        ("Blood pressure", vitals["blood_pressure"]),
                        ("SpO2", f"{vitals['oxygen_saturation']}%"),
                    ],
                ),
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                summary_card(
                    "Presenting Concern",
                    f"{patient['symptoms']} Duration: {patient['duration_days']} day(s). Pain score: {patient['pain_score']}/10.",
                    [f"Pain {patient['pain_score']}/10", f"{patient['duration_days']} day(s)"],
                    "info",
                ),
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Clinical Background</div>
                    <div class="card-label">Medical History</div>
                    {pills(patient["medical_history"], "info", "None listed")}
                    <div class="card-label" style="margin-top:0.8rem;">Current Medications</div>
                    {pills(patient["medications"], "warn", "None listed")}
                    <div class="card-label" style="margin-top:0.8rem;">Allergies</div>
                    {pills(patient["allergies"], "danger", "No known allergies")}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_triage:
        t1, t2 = st.columns([0.95, 1.05])
        with t1:
            st.markdown(
                summary_card(
                    triage["urgency_label"],
                    triage["plain_summary"],
                    [f"Level {triage['urgency_level']}", triage["next_step"]],
                    "danger" if triage["urgency_level"] <= 2 else "warn" if triage["urgency_level"] == 3 else "ok",
                ),
                unsafe_allow_html=True,
            )
        with t2:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Deterministic Rule Evidence</div>
                    <div class="card-label">Rule Hits</div>
                    {pills(triage["rule_hits"], "warn")}
                    <div class="card-label" style="margin-top:0.8rem;">Red Flags</div>
                    {pills(triage["red_flags"], "danger", "None detected")}
                    <div class="card-label" style="margin-top:0.8rem;">LLM Decision Authority</div>
                    {pills(["None for triage urgency or escalation"], "ok")}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_sandbox:
        active_explanation = explain_triage_decision(patient)
        st.markdown(
            summary_card(
                "Selected Patient Logic",
                active_explanation["why"],
                [f"Level {active_explanation['urgency_level']}", active_explanation["urgency_label"]],
                "danger" if active_explanation["urgency_level"] <= 2 else "warn" if active_explanation["urgency_level"] == 3 else "ok",
            ),
            unsafe_allow_html=True,
        )

        reason_cols = st.columns([1, 1])
        with reason_cols[0]:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Parameters Used For Triage</div>
                    <div class="kv">
                        <div class="key">Patient ID</div><div>{esc(patient["patient_id"])}</div>
                        <div class="key">Age</div><div>{esc(patient["age"])}</div>
                        <div class="key">Symptoms</div><div>{esc(patient["symptoms"])}</div>
                        <div class="key">Duration</div><div>{esc(patient["duration_days"])} day(s)</div>
                        <div class="key">Pain score</div><div>{esc(patient["pain_score"])}/10</div>
                    </div>
                    <div class="card-label" style="margin-top:0.8rem;">Detected Red Flags</div>
                    {pills(triage["red_flags"], "danger", "None detected")}
                </div>
                """,
                unsafe_allow_html=True,
            )
        with reason_cols[1]:
            blockers = treatment["safety_checks"]["blockers"]
            warnings = treatment["safety_checks"]["warnings"]
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Parameters Used For Medication Safety</div>
                    <div class="card-label">Current Medications</div>
                    {pills(patient["medications"], "warn", "None listed")}
                    <div class="card-label" style="margin-top:0.8rem;">Allergies</div>
                    {pills(patient["allergies"], "danger", "No known allergies")}
                    <div class="card-label" style="margin-top:0.8rem;">Medication Draft</div>
                    {pills(treatment["proposed_medications"], "warn", "No medication draft")}
                    <div class="card-label" style="margin-top:0.8rem;">Why blocked or allowed</div>
                    {pills([b.get("action", str(b)) for b in blockers], "danger", "No blockers")}
                    {pills([w.get("warning", str(w)) for w in warnings], "warn", "No warnings")}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("#### Printed Rule Logic")
        st.caption("Every safety-critical triage rule is evaluated explicitly. This table is the reason behind Level 2, Level 3, or Level 4.")
        st.dataframe(pd.DataFrame(active_explanation["full_trace"]), width="stretch", hide_index=True)

        if active_explanation["rules_not_met_for_level_2"]:
            st.markdown("#### Why this did not become Level 2")
            st.write(
                "The following Level 2 rules did not match the structured data: "
                + ", ".join(active_explanation["rules_not_met_for_level_2"])
            )

        st.divider()
        st.markdown("### Add A New Case And Ask For Reasoning")
        st.caption(
            "Use this to test a new patient ID and symptoms. The answer explains what the model-style reasoning would say, while the rule output remains the source of truth."
        )

        sandbox_cols = st.columns([0.7, 0.7, 0.8, 1.8])
        with sandbox_cols[0]:
            sandbox_patient_id = st.text_input("New patient ID", "NEW-001")
        with sandbox_cols[1]:
            sandbox_age = st.number_input("Age", min_value=0, max_value=120, value=42)
        with sandbox_cols[2]:
            sandbox_pain = st.slider("Pain score", 0, 10, 4)
        with sandbox_cols[3]:
            sandbox_prompt = st.text_input(
                "Prompt to test",
                "Explain the triage level and any medication safety concerns.",
            )

        sandbox_symptoms = st.text_area(
            "Symptoms",
            "Mild cough and runny nose for two days. Patient is stable and speaking comfortably.",
            height=85,
        )
        sandbox_flags = st.multiselect(
            "Structured red flags",
            options=list(FLAG_LABELS.keys()),
            default=[],
            format_func=lambda flag: FLAG_LABELS[flag],
        )

        sandbox_patient = {
            "patient_id": sandbox_patient_id,
            "name": "Sandbox Patient",
            "age": int(sandbox_age),
            "gender": "Not specified",
            "symptoms": sandbox_symptoms,
            "duration_days": 2,
            "pain_score": int(sandbox_pain),
            "medical_history": [],
            "medications": [],
            "allergies": [],
            "selected_red_flags": sandbox_flags,
            "primary_care_provider": "Sandbox",
            "preferred_language": "English",
            "visit_type": "Sandbox triage test",
            "vitals": {},
        }
        sandbox_result = run_sandbox_triage_agent(sandbox_patient, sandbox_prompt)

        s1, s2 = st.columns([1, 1])
        with s1:
            st.markdown(
                summary_card(
                    "Production Rule Result",
                    sandbox_result["production_result"]["why"],
                    [
                        f"Level {sandbox_result['production_result']['urgency_level']}",
                        sandbox_result["production_result"]["urgency_label"],
                    ],
                    "danger"
                    if sandbox_result["production_result"]["urgency_level"] <= 2
                    else "warn"
                    if sandbox_result["production_result"]["urgency_level"] == 3
                    else "ok",
                ),
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                summary_card(
                    "Model-Style Answer",
                    sandbox_result["sandbox_agent_response"],
                    ["Reasoning answer", "Rules stay source of truth"],
                    "info",
                ),
                unsafe_allow_html=True,
            )

        st.markdown("#### New Case Rule Logic")
        st.dataframe(pd.DataFrame(sandbox_result["rule_trace"]), width="stretch", hide_index=True)

    with tab_workflow:
        st.markdown(
            timeline_step(1, "Triage Agent", "completed", triage["plain_summary"], "ok"),
            unsafe_allow_html=True,
        )
        st.markdown(
            timeline_step(2, "Diagnosis Agent", diagnosis["status"], diagnosis["plain_summary"], "warn"),
            unsafe_allow_html=True,
        )
        st.markdown(
            timeline_step(3, "Treatment Agent", treatment["status"], treatment["plain_summary"], safety_tone),
            unsafe_allow_html=True,
        )
        st.markdown(
            timeline_step(4, "Documentation Agent", documentation["status"], "Creates a SOAP draft from structured workflow data.", "warn"),
            unsafe_allow_html=True,
        )
        st.markdown(
            timeline_step(5, "Scheduling Agent", scheduling["status"], f"{scheduling['appointment_type']} through {scheduling['escalation_channel']}.", "info"),
            unsafe_allow_html=True,
        )
        st.markdown(
            timeline_step(6, "Follow-up Agent", followup["status"], f"Monitoring interval: {followup['monitoring_interval']}.", "info"),
            unsafe_allow_html=True,
        )

    with tab_care:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Diagnosis Draft</div>
                    <div class="soft">{esc(diagnosis["plain_summary"])}</div>
                    <div class="card-label" style="margin-top:0.8rem;">Differential Focus</div>
                    {pills(diagnosis["differential_focus"], "info")}
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            blockers = treatment["safety_checks"]["blockers"]
            warnings = treatment["safety_checks"]["warnings"]
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Treatment Safety</div>
                    <div class="soft">{esc(treatment["plain_summary"])}</div>
                    <div class="card-label" style="margin-top:0.8rem;">Medication Draft</div>
                    {pills(treatment["proposed_medications"], "warn", "No medication draft")}
                    <div class="card-label" style="margin-top:0.8rem;">Safety Result</div>
                    {pills(["Passed"] if treatment["safety_checks"]["passed"] else ["Safety hold"], safety_tone)}
                    <div class="card-label" style="margin-top:0.8rem;">Blockers</div>
                    {pills([b.get("action", str(b)) for b in blockers], "danger", "None")}
                    <div class="card-label" style="margin-top:0.8rem;">Warnings</div>
                    {pills([w.get("warning", str(w)) for w in warnings], "warn", "None")}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(
                profile_card(
                    "Scheduling",
                    [
                        ("Timeframe", scheduling["recommended_timeframe"]),
                        ("Appointment", scheduling["appointment_type"]),
                        ("Scheduled for", scheduling["scheduled_for"]),
                        ("Channel", scheduling["escalation_channel"]),
                    ],
                ),
                unsafe_allow_html=True,
            )
        with s2:
            st.markdown(
                f"""
                <div class="profile-card">
                    <div class="card-title">Follow-up Monitoring</div>
                    <div class="kv">
                        <div class="key">Interval</div><div>{esc(followup["monitoring_interval"])}</div>
                        <div class="key">Next check-in</div><div>{esc(followup["next_check_in"])}</div>
                    </div>
                    <div class="card-label" style="margin-top:0.8rem;">Triggers</div>
                    {pills(followup["triggers"], "info")}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_note:
        st.code(documentation["soap_note"], language="text")

    with tab_data:
        st.markdown("### Sample Source Table")
        st.caption("Generated local dataframe. This is the layer that could be swapped for BigQuery.")
        st.dataframe(patient_df, width="stretch", hide_index=True)

        st.markdown("### Active Patient Row")
        active_row = patient_df[patient_df["patient_id"] == key]
        st.dataframe(active_row, width="stretch", hide_index=True)

        st.markdown("### Pipeline Payload")
        st.json(result)


if __name__ == "__main__":
    main()
