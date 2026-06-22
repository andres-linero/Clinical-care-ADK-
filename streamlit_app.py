"""
Streamlit demo for the rule-governed clinical care agent workflow.

Run:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from rule_pipeline import FLAG_LABELS, run_rule_pipeline


DATA_PATH = Path(__file__).with_name("sample_patients.json")


def load_examples() -> list[dict[str, Any]]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def without_label(case: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in case.items() if key != "label"}


def split_lines(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def section_header(title: str, caption: str) -> None:
    st.subheader(title)
    st.caption(caption)


def render_status_badge(label: str, value: str) -> None:
    st.metric(label, value)


def render_agent_step(title: str, status: str, summary: str) -> None:
    st.markdown(f"### {title}")
    st.write(summary)
    st.caption(f"Status: {status}")


def main() -> None:
    st.set_page_config(
        page_title="Clinical Care ADK Demo",
        page_icon="",
        layout="wide",
    )

    examples = load_examples()
    example_labels = [case["label"] for case in examples]

    st.title("Clinical Care Agent Workflow")
    st.write(
        "A multi-agent care coordination demo where safety-critical decisions "
        "are handled by deterministic rules, not free-form LLM judgment."
    )

    st.info(
        "Demo scope: this is not medical advice. The workflow shows software "
        "architecture, rule-based triage, safety checks, and agent handoffs."
    )

    with st.sidebar:
        st.header("Patient Intake")
        selected_label = st.selectbox("Load demo case", example_labels)
        selected_case = without_label(
            next(case for case in examples if case["label"] == selected_label)
        )

        patient_id = st.text_input("Patient ID", selected_case["patient_id"])
        name = st.text_input("Name", selected_case["name"])
        age = st.number_input("Age", min_value=0, max_value=120, value=selected_case["age"])
        gender = st.selectbox(
            "Gender",
            ["F", "M", "Other", "Not specified"],
            index=["F", "M", "Other", "Not specified"].index(selected_case["gender"])
            if selected_case["gender"] in ["F", "M", "Other", "Not specified"]
            else 3,
        )
        symptoms = st.text_area("Symptoms", selected_case["symptoms"], height=110)
        duration_days = st.number_input(
            "Duration in days",
            min_value=0,
            max_value=365,
            value=selected_case["duration_days"],
        )
        pain_score = st.slider("Pain score", min_value=0, max_value=10, value=selected_case["pain_score"])

        st.divider()
        st.caption("Structured clinical context")
        medical_history = split_lines(
            st.text_area(
                "Medical history, comma separated",
                ", ".join(selected_case["medical_history"]),
                height=70,
            )
        )
        medications = split_lines(
            st.text_area(
                "Current medications, comma separated",
                ", ".join(selected_case["medications"]),
                height=70,
            )
        )
        allergies = split_lines(
            st.text_area(
                "Allergies, comma separated",
                ", ".join(selected_case["allergies"]),
                height=70,
            )
        )

        selected_flags = st.multiselect(
            "Clinician-selected red flags",
            options=list(FLAG_LABELS.keys()),
            default=selected_case["selected_red_flags"],
            format_func=lambda flag: FLAG_LABELS[flag],
        )

        run_clicked = st.button("Run Workflow", type="primary", use_container_width=True)

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
    }

    if not run_clicked and "last_result" not in st.session_state:
        st.session_state.last_result = run_rule_pipeline(patient)

    if run_clicked:
        st.session_state.last_result = run_rule_pipeline(patient)

    result = st.session_state.last_result
    steps = result["steps"]
    triage = steps["triage"]
    diagnosis = steps["diagnosis"]
    treatment = steps["treatment"]
    documentation = steps["documentation"]
    scheduling = steps["scheduling"]
    followup = steps["followup"]

    metric_cols = st.columns(4)
    with metric_cols[0]:
        render_status_badge("Workflow status", result["status"].replace("_", " ").title())
    with metric_cols[1]:
        render_status_badge("Urgency level", str(triage["urgency_level"]))
    with metric_cols[2]:
        render_status_badge("Escalation", "Required" if triage["escalation_required"] else "No")
    with metric_cols[3]:
        render_status_badge("Safety", "Passed" if treatment["safety_checks"]["passed"] else "Hold")

    tab_overview, tab_steps, tab_note, tab_raw = st.tabs(
        ["Overview", "Agent Steps", "Clinical Note", "Structured Data"]
    )

    with tab_overview:
        left, right = st.columns([1, 1])
        with left:
            section_header("Patient", "Structured intake used by the pipeline")
            st.write(f"**{patient['name']}** ({patient['patient_id']})")
            st.write(f"Age/Gender: {patient['age']} / {patient['gender']}")
            st.write(f"Symptoms: {patient['symptoms']}")
            st.write(f"Duration: {patient['duration_days']} day(s)")
            st.write(f"Pain score: {patient['pain_score']}/10")
        with right:
            section_header("Rule Decision", "The triage result is deterministic")
            st.write(f"**{triage['urgency_label']}**")
            st.write(triage["plain_summary"])
            st.write("Rule hits:")
            for rule in triage["rule_hits"]:
                st.write(f"- {rule}")
            st.write("Red flags:")
            if triage["red_flags"]:
                for flag in triage["red_flags"]:
                    st.write(f"- {flag}")
            else:
                st.write("- None detected")

    with tab_steps:
        render_agent_step("1. Triage Agent", "completed", triage["plain_summary"])
        st.write(f"Next step: {triage['next_step']}")
        st.divider()

        render_agent_step("2. Diagnosis Agent", diagnosis["status"], diagnosis["plain_summary"])
        st.write("Differential focus:")
        for item in diagnosis["differential_focus"]:
            st.write(f"- {item}")
        st.divider()

        render_agent_step("3. Treatment Agent", treatment["status"], treatment["plain_summary"])
        st.write("Proposed medications:")
        if treatment["proposed_medications"]:
            for med in treatment["proposed_medications"]:
                st.write(f"- {med}")
        else:
            st.write("- None")
        st.write("Safety checks:")
        st.json(treatment["safety_checks"])
        st.divider()

        render_agent_step("4. Documentation Agent", documentation["status"], "Creates a SOAP draft from structured data.")
        render_agent_step("5. Scheduling Agent", scheduling["status"], f"{scheduling['appointment_type']} scheduled draft.")
        st.write(f"Recommended timeframe: {scheduling['recommended_timeframe']}")
        st.write(f"Scheduled for: {scheduling['scheduled_for']}")
        st.write(f"Channel: {scheduling['escalation_channel']}")
        st.divider()

        render_agent_step("6. Follow-up Agent", followup["status"], "Creates a monitoring plan using urgency-based rules.")
        st.write(f"Monitoring interval: {followup['monitoring_interval']}")
        st.write(f"Next check-in: {followup['next_check_in']}")
        st.write("Triggers:")
        for trigger in followup["triggers"]:
            st.write(f"- {trigger}")

    with tab_note:
        section_header("SOAP Draft", "Generated from deterministic pipeline outputs")
        st.code(documentation["soap_note"], language="text")

    with tab_raw:
        section_header("Full Payload", "Structured result passed between agents")
        st.json(result)


if __name__ == "__main__":
    main()
