"""Typed contracts for the simulated discharge-planning prototype."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Medication(BaseModel):
    """A medication as it appears in a reconciled discharge source.

    These fields deliberately describe an existing order; they are not a
    prescription interface and must never be completed by the agent.
    """

    name: str = Field(min_length=1)
    dosage: str | None = None
    frequency: str | None = None
    route: str | None = None
    discharge_action: Literal["start", "continue", "stop", "change"] = "continue"
    start_date: str | None = None
    stop_date: str | None = None
    is_prn: bool = False
    prn_indication: str | None = None
    max_frequency: str | None = None
    rxnorm_cui: str | None = Field(
        default=None,
        description="Optional RxNorm identifier returned by a terminology lookup.",
    )
    source_reference: str | None = Field(
        default=None,
        description="Optional identifier of the reconciled discharge order/source.",
    )
    notes: str | None = None

    @field_validator(
        "name", "dosage", "frequency", "route", "start_date", "stop_date",
        "prn_indication", "max_frequency", "rxnorm_cui", "source_reference", "notes",
        mode="before",
    )
    @classmethod
    def strip_medication_strings(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class PatientCaseInput(BaseModel):
    patient_id: str = Field(min_length=1, description="Synthetic case identifier")
    age: int | None = Field(default=None, ge=0, le=130)
    gender: str | None = None
    diagnosis: str = Field(min_length=1)
    discharge_summary: str = Field(min_length=1)
    medication_list: list[Medication] = Field(default_factory=list)
    medication_reconciliation_status: Literal[
        "complete", "no_discharge_medications", "incomplete", "unknown"
    ] = "unknown"
    allergies: list[str] = Field(default_factory=list)
    follow_up_needs: list[str] = Field(default_factory=list)
    relevant_notes: list[str] = Field(default_factory=list)

    @field_validator("allergies", "follow_up_needs", "relevant_notes")
    @classmethod
    def remove_blank_values(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value and value.strip()]


class EvidenceItem(BaseModel):
    evidence_id: str
    source: str
    title: str
    content: str
    score: float
    version: str = "1.0"
    source_url: str | None = None
    approval_status: Literal["approved", "candidate", "retired"] = "approved"
    reviewed_at: str | None = None
    review_scope: str | None = None


class DischargeInstruction(BaseModel):
    summary: str
    care_instructions: list[str] = Field(default_factory=list)
    warning_notes: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class MedicationScheduleItem(BaseModel):
    """A deterministic reminder derived only from a reconciled medication."""

    medication_name: str
    discharge_action: Literal["start", "continue", "stop", "change"]
    reminder: str
    source_fields: list[str] = Field(default_factory=list)
    source_reference: str | None = None
    rxnorm_cui: str | None = None
    requires_clinician_review: bool = False


class SafetyFinding(BaseModel):
    code: str
    severity: Literal["info", "warning", "high"]
    message: str
    affected_field: str | None = None
    required_action: Literal["review", "edit", "escalate"]
    evidence: list[str] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    """Claim-level provenance for a generated discharge education statement."""

    claim_type: Literal["care_instruction", "warning_note"]
    claim_index: int = Field(ge=0)
    text: str
    evidence_ids: list[str] = Field(default_factory=list)
    mapping_status: Literal["generated", "reviewer_edit_requires_confirmation"] = "generated"


class ReviewDecision(BaseModel):
    decision: Literal["approve", "edit", "reject", "escalate"]
    reviewer_id: str = Field(min_length=1)
    reviewer_role: Literal["clinician", "pharmacist"] = "clinician"
    notes: str = ""
    edits: dict[str, list[str]] = Field(default_factory=dict)


class FinalDischargePlan(BaseModel):
    patient_id: str
    status: Literal["finalized", "rejected", "escalated"]
    discharge_instructions: list[str] = Field(default_factory=list)
    medication_reminders: list[str] = Field(default_factory=list)
    medication_schedule: list[MedicationScheduleItem] = Field(default_factory=list)
    follow_up_tasks: list[str] = Field(default_factory=list)
    safety_findings: list[SafetyFinding] = Field(default_factory=list)
    reviewer_id: str | None = None
    reviewer_notes: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    claim_evidence: list[ClaimEvidence] = Field(default_factory=list)
