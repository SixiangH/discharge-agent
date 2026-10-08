"""LangGraph state for a simulated, auditable discharge-planning workflow."""

import operator
from typing import Annotated, Any, Literal, TypedDict


class DischargeAgentState(TypedDict, total=False):
    input_payload: dict[str, Any]
    validated_case: dict[str, Any]
    patient_id: str
    validation_status: Literal["valid", "invalid"]
    missing_fields: list[str]
    validation_errors: list[str]
    patient_profile: dict[str, Any]
    diagnosis_summary: str
    medications: list[dict[str, Any]]
    external_drug_evidence: list[dict[str, Any]]
    external_evidence_findings: list[dict[str, Any]]
    allergies: list[str]
    follow_up_needs: list[str]
    discharge_context: dict[str, Any]
    retrieved_evidence: list[dict[str, Any]]
    discharge_instructions: dict[str, Any]
    medication_reminders: list[str]
    medication_schedule: list[dict[str, Any]]
    medication_schedule_findings: list[dict[str, Any]]
    follow_up_tasks: list[str]
    safety_findings: list[dict[str, Any]]
    risk_level: Literal["low", "medium", "high"]
    human_review_status: Literal["pending", "approved", "edited", "rejected", "escalated"]
    reviewer_decision: str
    reviewer_id: str
    reviewer_role: Literal["clinician", "pharmacist"]
    reviewer_notes: str
    reviewer_edits: dict[str, list[str]]
    final_discharge_plan: dict[str, Any]
    workflow_status: str
    audit_log: Annotated[list[dict[str, Any]], operator.add]
