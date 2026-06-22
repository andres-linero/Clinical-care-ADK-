"""
Rule-governed clinical care coordination pipeline.

This module is intentionally deterministic for safety-critical decisions.
LLMs can be added later for summarization, but triage urgency, escalation,
medication safety, and follow-up triggers are owned by explicit rules.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any


URGENCY_LABELS = {
    1: "Immediate escalation",
    2: "Emergency clinical review",
    3: "Urgent care team review",
    4: "Standard clinical visit",
    5: "Routine follow-up",
}

RED_FLAG_KEYWORDS = {
    "chest_pain": ["chest pain", "chest pressure", "tight chest"],
    "shortness_of_breath": ["shortness of breath", "difficulty breathing", "trouble breathing"],
    "severe_bleeding": ["severe bleeding", "bleeding heavily", "bleeding won't stop"],
    "loss_of_consciousness": ["unconscious", "loss of consciousness", "passed out", "fainted"],
    "confusion": ["confusion", "confused", "altered mental status", "disoriented"],
    "stroke_signs": ["face drooping", "arm weakness", "slurred speech", "speech difficulty", "stroke"],
    "severe_allergic_reaction": ["anaphylaxis", "swelling throat", "severe allergic", "allergic reaction"],
    "suicidal_ideation": ["suicidal", "self-harm", "hurt myself", "kill myself"],
    "severe_trauma": ["severe trauma", "major injury", "head injury", "car accident"],
    "fever": ["fever", "high temperature", "temperature"],
    "neck_stiffness": ["neck stiffness", "stiff neck"],
    "severe_headache": ["severe headache", "worst headache", "thunderclap headache"],
    "persistent_vomiting": ["persistent vomiting", "can't keep fluids", "vomiting repeatedly"],
}

FLAG_LABELS = {
    "chest_pain": "Chest pain or pressure",
    "shortness_of_breath": "Shortness of breath",
    "severe_bleeding": "Severe bleeding",
    "loss_of_consciousness": "Loss of consciousness",
    "confusion": "Confusion or altered mental status",
    "stroke_signs": "Possible stroke signs",
    "severe_allergic_reaction": "Severe allergic reaction",
    "suicidal_ideation": "Suicidal ideation or self-harm risk",
    "severe_trauma": "Severe trauma",
    "fever": "Fever",
    "neck_stiffness": "Neck stiffness",
    "severe_headache": "Severe headache",
    "persistent_vomiting": "Persistent vomiting",
}

KNOWN_INTERACTIONS = {
    ("warfarin", "aspirin"): "Increased bleeding risk",
    ("metformin", "contrast dye"): "Risk of lactic acidosis",
    ("lisinopril", "potassium"): "Risk of hyperkalemia",
}


@dataclass
class PatientIntake:
    patient_id: str
    name: str
    age: int
    gender: str
    symptoms: str
    duration_days: int
    pain_score: int
    medical_history: list[str] = field(default_factory=list)
    medications: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    selected_red_flags: list[str] = field(default_factory=list)


@dataclass
class TriageResult:
    urgency_level: int
    urgency_label: str
    escalation_required: bool
    red_flags: list[str]
    rule_hits: list[str]
    next_step: str
    plain_summary: str


@dataclass
class DiagnosisResult:
    status: str
    differential_focus: list[str]
    clinician_review_required: bool
    plain_summary: str


@dataclass
class TreatmentResult:
    status: str
    proposed_medications: list[str]
    safety_checks: dict[str, Any]
    non_pharmacological_plan: list[str]
    clinician_review_required: bool
    plain_summary: str


@dataclass
class DocumentationResult:
    status: str
    note_type: str
    soap_note: str


@dataclass
class SchedulingResult:
    status: str
    recommended_timeframe: str
    appointment_type: str
    scheduled_for: str
    escalation_channel: str


@dataclass
class FollowupResult:
    status: str
    monitoring_interval: str
    triggers: list[str]
    next_check_in: str


def detect_red_flags(patient: PatientIntake) -> list[str]:
    symptoms_lower = patient.symptoms.lower()
    detected = set(patient.selected_red_flags)

    for flag, keywords in RED_FLAG_KEYWORDS.items():
        if any(keyword in symptoms_lower for keyword in keywords):
            detected.add(flag)

    if patient.pain_score >= 8:
        detected.add("severe_headache" if "headache" in symptoms_lower else "severe_pain")

    return sorted(detected)


def run_triage(patient: PatientIntake) -> TriageResult:
    flags = detect_red_flags(patient)
    flag_set = set(flags)
    rule_hits: list[str] = []
    urgency = 4

    immediate_flags = {
        "severe_bleeding",
        "loss_of_consciousness",
        "stroke_signs",
        "severe_allergic_reaction",
        "suicidal_ideation",
        "severe_trauma",
    }
    if flag_set.intersection(immediate_flags):
        urgency = 1
        rule_hits.append("Immediate escalation red flag present")

    if {"chest_pain", "shortness_of_breath"}.issubset(flag_set):
        urgency = min(urgency, 1)
        rule_hits.append("Chest pain with shortness of breath")
    elif "chest_pain" in flag_set or "shortness_of_breath" in flag_set:
        urgency = min(urgency, 2)
        rule_hits.append("Single cardiopulmonary red flag")

    if {"fever", "neck_stiffness"}.issubset(flag_set):
        urgency = min(urgency, 2)
        rule_hits.append("Fever with neck stiffness")

    if "severe_headache" in flag_set and ("fever" in flag_set or "confusion" in flag_set):
        urgency = min(urgency, 2)
        rule_hits.append("Severe headache with systemic or neurologic concern")

    if "persistent_vomiting" in flag_set:
        urgency = min(urgency, 3)
        rule_hits.append("Persistent vomiting")

    if patient.age >= 65 and urgency > 3 and flags:
        urgency = 3
        rule_hits.append("Older adult with red-flag symptom")

    if patient.duration_days >= 7 and urgency > 4:
        urgency = 4
        rule_hits.append("Symptoms persistent for at least one week")

    if not rule_hits:
        rule_hits.append("No escalation rule matched")

    escalation_required = urgency <= 2
    red_flag_labels = [FLAG_LABELS.get(flag, flag.replace("_", " ").title()) for flag in flags]
    next_step = (
        "Escalate to immediate clinical review"
        if urgency == 1
        else "Route to emergency clinical review"
        if urgency == 2
        else "Route to urgent care team review"
        if urgency == 3
        else "Proceed through standard coordinated workflow"
    )

    return TriageResult(
        urgency_level=urgency,
        urgency_label=URGENCY_LABELS[urgency],
        escalation_required=escalation_required,
        red_flags=red_flag_labels,
        rule_hits=rule_hits,
        next_step=next_step,
        plain_summary=(
            f"Triage rules assigned level {urgency}: {URGENCY_LABELS[urgency]}. "
            f"The decision is based on explicit rules, not an LLM."
        ),
    )


def run_diagnosis(patient: PatientIntake, triage: TriageResult) -> DiagnosisResult:
    symptoms_lower = patient.symptoms.lower()
    focus = []

    if "headache" in symptoms_lower:
        focus.extend(["Migraine or tension headache", "Secondary headache causes"])
    if "fever" in symptoms_lower or "Fever" in triage.red_flags:
        focus.append("Infectious process")
    if "Neck stiffness" in triage.red_flags:
        focus.append("Meningeal irritation risk")
    if "chest" in symptoms_lower:
        focus.extend(["Cardiac causes", "Pulmonary causes"])
    if not focus:
        focus.append("General clinical assessment")

    return DiagnosisResult(
        status="draft_for_review",
        differential_focus=focus,
        clinician_review_required=True,
        plain_summary=(
            "Diagnosis agent prepares a structured differential focus for clinician "
            "review. It does not make a final diagnosis."
        ),
    )


def propose_medications(patient: PatientIntake, diagnosis: DiagnosisResult) -> list[str]:
    symptoms_lower = patient.symptoms.lower()
    meds = []

    if "headache" in symptoms_lower or patient.pain_score > 0:
        meds.append("Acetaminophen")
    if "allergy" in symptoms_lower and "severe allergic reaction" not in " ".join(diagnosis.differential_focus).lower():
        meds.append("Cetirizine")

    return meds


def run_medication_safety(
    proposed_medications: list[str],
    current_medications: list[str],
    allergies: list[str],
) -> dict[str, Any]:
    warnings = []
    blockers = []
    normalized_current = " ".join(current_medications).lower()
    normalized_proposed = [med.lower() for med in proposed_medications]

    for med in proposed_medications:
        for allergy in allergies:
            if allergy.lower() in med.lower():
                blockers.append(
                    {
                        "type": "allergy_conflict",
                        "medication": med,
                        "allergen": allergy,
                        "action": "Do not recommend medication",
                    }
                )

    combined = " ".join(normalized_proposed + [normalized_current])
    for drug_pair, warning in KNOWN_INTERACTIONS.items():
        if all(drug in combined for drug in drug_pair):
            warnings.append(
                {
                    "type": "drug_interaction",
                    "drugs": list(drug_pair),
                    "warning": warning,
                    "severity": "moderate",
                }
            )

    return {
        "passed": not blockers,
        "checks_performed": ["allergy_check", "drug_interaction_check"],
        "warnings": warnings,
        "blockers": blockers,
    }


def run_treatment(patient: PatientIntake, triage: TriageResult, diagnosis: DiagnosisResult) -> TreatmentResult:
    proposed_meds = [] if triage.escalation_required else propose_medications(patient, diagnosis)
    safety = run_medication_safety(proposed_meds, patient.medications, patient.allergies)
    status = "safety_hold" if not safety["passed"] else "pending_clinician_review"

    non_pharm = [
        "Review vital signs and objective findings",
        "Provide return precautions based on triage level",
        "Confirm plan with licensed clinician before patient instructions",
    ]
    if triage.escalation_required:
        non_pharm.insert(0, "Do not delay escalation for routine treatment planning")

    return TreatmentResult(
        status=status,
        proposed_medications=proposed_meds,
        safety_checks=safety,
        non_pharmacological_plan=non_pharm,
        clinician_review_required=True,
        plain_summary=(
            "Treatment agent proposes only low-risk draft actions and runs explicit "
            "allergy and interaction checks. Escalated cases bypass medication drafting."
        ),
    )


def run_documentation(
    patient: PatientIntake,
    triage: TriageResult,
    diagnosis: DiagnosisResult,
    treatment: TreatmentResult,
) -> DocumentationResult:
    soap_note = f"""SUBJECTIVE
Patient: {patient.name} ({patient.patient_id})
Symptoms: {patient.symptoms}
Duration: {patient.duration_days} day(s)
Pain score: {patient.pain_score}/10

OBJECTIVE
Rule-based urgency: Level {triage.urgency_level} - {triage.urgency_label}
Red flags: {", ".join(triage.red_flags) if triage.red_flags else "None detected"}

ASSESSMENT
Differential focus: {", ".join(diagnosis.differential_focus)}
Final diagnosis: Requires clinician review

PLAN
Next step: {triage.next_step}
Medication draft: {", ".join(treatment.proposed_medications) if treatment.proposed_medications else "None"}
Safety status: {treatment.status}
Clinician review required: Yes
"""

    return DocumentationResult(
        status="draft_requires_signature",
        note_type="SOAP",
        soap_note=soap_note,
    )


def run_scheduling(patient: PatientIntake, triage: TriageResult) -> SchedulingResult:
    now = datetime.now()
    if triage.urgency_level == 1:
        timeframe = "Immediate"
        scheduled_for = now.isoformat(timespec="minutes")
        appointment_type = "Emergency escalation"
        channel = "Emergency care team"
    elif triage.urgency_level == 2:
        timeframe = "Same day"
        scheduled_for = (now + timedelta(hours=2)).isoformat(timespec="minutes")
        appointment_type = "Emergency clinical review"
        channel = "On-call clinician"
    elif triage.urgency_level == 3:
        timeframe = "Within 24 hours"
        scheduled_for = (now + timedelta(days=1)).isoformat(timespec="minutes")
        appointment_type = "Urgent visit"
        channel = "Care coordinator"
    else:
        timeframe = "Within 7 days"
        scheduled_for = (now + timedelta(days=7)).isoformat(timespec="minutes")
        appointment_type = "Standard follow-up"
        channel = "Scheduling desk"

    return SchedulingResult(
        status="scheduled_draft",
        recommended_timeframe=timeframe,
        appointment_type=appointment_type,
        scheduled_for=scheduled_for,
        escalation_channel=channel,
    )


def run_followup(triage: TriageResult, scheduling: SchedulingResult) -> FollowupResult:
    if triage.urgency_level <= 2:
        interval = "Daily until clinician clears escalation"
        next_check = datetime.now() + timedelta(days=1)
    elif triage.urgency_level == 3:
        interval = "48-hour check-in"
        next_check = datetime.now() + timedelta(days=2)
    else:
        interval = "One-week check-in"
        next_check = datetime.now() + timedelta(days=7)

    return FollowupResult(
        status="monitoring_plan_created",
        monitoring_interval=interval,
        triggers=[
            "Symptoms worsen",
            "New red flags appear",
            "Appointment is missed",
            "Medication safety concern is reported",
        ],
        next_check_in=next_check.isoformat(timespec="minutes"),
    )


def run_rule_pipeline(patient_data: dict[str, Any]) -> dict[str, Any]:
    patient = PatientIntake(**patient_data)
    triage = run_triage(patient)
    diagnosis = run_diagnosis(patient, triage)
    treatment = run_treatment(patient, triage, diagnosis)
    documentation = run_documentation(patient, triage, diagnosis, treatment)
    scheduling = run_scheduling(patient, triage)
    followup = run_followup(triage, scheduling)
    status = (
        "escalation_required"
        if triage.escalation_required
        else "safety_review_required"
        if treatment.status == "safety_hold"
        else "workflow_completed"
    )

    return {
        "patient": asdict(patient),
        "steps": {
            "triage": asdict(triage),
            "diagnosis": asdict(diagnosis),
            "treatment": asdict(treatment),
            "documentation": asdict(documentation),
            "scheduling": asdict(scheduling),
            "followup": asdict(followup),
        },
        "status": status,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }
