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

import streamlit as st

from rule_pipeline import FLAG_LABELS, run_rule_pipeline


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
        st.markdown("### Patient Scenario & Intake")
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

        row1 = st.columns([1, 1.2, 0.8, 0.8])
        with row1[0]:
            patient_id = st.text_input(
                "Patient ID",
                selected_case["patient_id"],
                disabled=True,
                key=f"patient_id_{key}",
            )
        with row1[1]:
            name = st.text_input("Name", selected_case["name"], key=f"name_{key}")
        with row1[2]:
            age = st.number_input("Age", min_value=0, max_value=120, value=int(selected_case["age"]), key=f"age_{key}")
        with row1[3]:
            gender_options = ["F", "M", "Other", "Not specified"]
            gender = st.selectbox(
                "Gender",
                gender_options,
                index=gender_options.index(selected_case["gender"]) if selected_case["gender"] in gender_options else 3,
                key=f"gender_{key}",
            )

        symptoms = st.text_area("Presenting symptoms", selected_case["symptoms"], height=90, key=f"symptoms_{key}")

        row2 = st.columns([0.8, 1.2, 1.2, 1.2])
        with row2[0]:
            duration_days = st.number_input(
                "Duration in days",
                min_value=0,
                max_value=365,
                value=int(selected_case["duration_days"]),
                key=f"duration_{key}",
            )
        with row2[1]:
            pain_score = st.slider(
                "Pain score",
                min_value=0,
                max_value=10,
                value=int(selected_case["pain_score"]),
                key=f"pain_{key}",
            )
        with row2[2]:
            primary_care_provider = st.text_input(
                "Primary care provider",
                selected_case.get("primary_care_provider", "Unassigned"),
                key=f"provider_{key}",
            )
        with row2[3]:
            visit_type = st.text_input(
                "Visit type",
                selected_case.get("visit_type", "New concern"),
                key=f"visit_type_{key}",
            )

        row3 = st.columns([1, 1, 1])
        with row3[0]:
            preferred_language = st.text_input(
                "Preferred language",
                selected_case.get("preferred_language", "English"),
                key=f"language_{key}",
            )
        with row3[1]:
            medical_history = split_lines(
                st.text_area(
                    "Medical history",
                    ", ".join(selected_case["medical_history"]),
                    height=80,
                    key=f"history_{key}",
                )
            )
        with row3[2]:
            medications = split_lines(
                st.text_area(
                    "Current medications",
                    ", ".join(selected_case["medications"]),
                    height=80,
                    key=f"meds_{key}",
                )
            )

        row4 = st.columns([1, 2])
        with row4[0]:
            allergies = split_lines(
                st.text_area(
                    "Allergies",
                    ", ".join(selected_case["allergies"]),
                    height=80,
                    key=f"allergies_{key}",
                )
            )
        with row4[1]:
            selected_flags = st.multiselect(
                "Structured red flags",
                options=list(FLAG_LABELS.keys()),
                default=selected_case["selected_red_flags"],
                format_func=lambda flag: FLAG_LABELS[flag],
                key=f"flags_{key}",
            )

        vitals_seed = selected_case.get("vitals", {})
        row5 = st.columns(4)
        with row5[0]:
            temperature_f = st.number_input(
                "Temperature F",
                min_value=90.0,
                max_value=110.0,
                value=float(vitals_seed.get("temperature_f", 98.6)),
                step=0.1,
                key=f"temp_{key}",
            )
        with row5[1]:
            heart_rate = st.number_input(
                "Heart rate",
                min_value=30,
                max_value=220,
                value=int(vitals_seed.get("heart_rate", 76)),
                key=f"hr_{key}",
            )
        with row5[2]:
            blood_pressure = st.text_input(
                "Blood pressure",
                vitals_seed.get("blood_pressure", "120/80"),
                key=f"bp_{key}",
            )
        with row5[3]:
            oxygen_saturation = st.number_input(
                "Oxygen saturation",
                min_value=50,
                max_value=100,
                value=int(vitals_seed.get("oxygen_saturation", 99)),
                key=f"spo2_{key}",
            )

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

    tab_profile, tab_triage, tab_workflow, tab_care, tab_note, tab_data = st.tabs(
        ["Patient Profile", "Triage Rules", "Agent Workflow", "Care Plan", "Documentation", "Data"]
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
        st.json(result)


if __name__ == "__main__":
    main()
