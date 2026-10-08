"""Pure-ish graph nodes.  Each node returns only the state it owns."""

from datetime import datetime, timezone
import os
from typing import Any

from pydantic import ValidationError

from app.schemas.patient_schema import FinalDischargePlan, PatientCaseInput, ReviewDecision
from app.services.draft_generator import get_draft_generator
from app.tools.retrieval_tool import RetrievalTool
from app.tools.safety_tool import SafetyTool
from app.tools.medication_schedule_tool import MedicationScheduleTool
from app.tools.external.medication_evidence_tool import PublicMedicationEvidenceTool


def _event(node: str, status: str, **details: Any) -> dict[str, Any]:
    return {
        "node": node,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **details,
    }


def receive_case(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "workflow_status": "received",
        "audit_log": [_event("receive_case", "received")],
    }


def validate_case(state: dict[str, Any]) -> dict[str, Any]:
    try:
        case = PatientCaseInput.model_validate(state.get("input_payload", {}))
    except ValidationError as error:
        errors = [item["msg"] for item in error.errors()]
        fields = sorted({str(item["loc"][0]) for item in error.errors()})
        return {
            "validation_status": "invalid",
            "missing_fields": fields,
            "validation_errors": errors,
            "workflow_status": "validation_failed",
            "audit_log": [_event("validate_case", "invalid", fields=fields)],
        }

    case_data = case.model_dump(mode="json")
    return {
        "patient_id": case.patient_id,
        "validated_case": case_data,
        "validation_status": "valid",
        "missing_fields": [],
        "validation_errors": [],
        "workflow_status": "validated",
        "audit_log": [_event("validate_case", "valid", patient_id=case.patient_id)],
    }


def construct_patient_state(state: dict[str, Any]) -> dict[str, Any]:
    case = state["validated_case"]
    return {
        "patient_profile": {"age": case.get("age"), "gender": case.get("gender"), "diagnosis": case["diagnosis"]},
        "diagnosis_summary": case["diagnosis"],
        "medications": case["medication_list"],
        "allergies": case["allergies"],
        "follow_up_needs": case["follow_up_needs"],
        "discharge_context": {"summary": case["discharge_summary"], "notes": case["relevant_notes"]},
        "workflow_status": "patient_state_ready",
        "audit_log": [_event("construct_patient_state", "ok", patient_id=case["patient_id"])],
    }


def enrich_medications_with_external_evidence(state: dict[str, Any]) -> dict[str, Any]:
    """Optionally query public terminology and label services with drug names only."""
    enabled = os.getenv("EXTERNAL_EVIDENCE_ENABLED", "false").lower() == "true"
    if not enabled:
        return {
            "external_drug_evidence": [], "external_evidence_findings": [],
            "workflow_status": "external_evidence_skipped",
            "audit_log": [_event("enrich_medications_with_external_evidence", "disabled")],
        }
    result = PublicMedicationEvidenceTool().enrich(state.get("medications", []))
    return {
        **result, "workflow_status": "external_evidence_retrieved",
        "audit_log": [_event("enrich_medications_with_external_evidence", "ok", medication_count=len(result["medications"]), evidence_count=len(result["external_drug_evidence"]))],
    }


def retrieve_knowledge(state: dict[str, Any]) -> dict[str, Any]:
    query = " ".join([
        state.get("diagnosis_summary", ""),
        " ".join(item.get("name", "") for item in state.get("medications", [])),
        " ".join(state.get("follow_up_needs", [])),
    ])
    evidence = RetrievalTool().retrieve(query)
    return {
        "retrieved_evidence": evidence,
        "workflow_status": "knowledge_retrieved",
        "audit_log": [_event("retrieve_knowledge", "ok", evidence_ids=[item["evidence_id"] for item in evidence])],
    }


def generate_discharge_instructions(state: dict[str, Any]) -> dict[str, Any]:
    """Draft only general instructions; medicines and follow-up remain deterministic."""
    generated = get_draft_generator().generate(state)
    summary = state.get("discharge_context", {}).get("summary", "")
    return {
        "discharge_instructions": {
            "summary": summary,
            "care_instructions": generated.care_instructions,
            "warning_notes": generated.warning_notes,
            "evidence_ids": generated.evidence_ids,
            "care_instruction_evidence": generated.care_instruction_evidence,
            "warning_note_evidence": generated.warning_note_evidence,
            "evidence_mapping_status": "generated",
            "generator": generated.generator,
        },
        "workflow_status": "draft_generated",
        "audit_log": [_event("generate_discharge_instructions", "draft_created", evidence_ids=generated.evidence_ids, generator=generated.generator)],
    }


def generate_medication_and_followup(state: dict[str, Any]) -> dict[str, Any]:
    schedule_result = MedicationScheduleTool().build(state.get("medications", []))
    tasks = [f"Clinician-provided follow-up: {need}" for need in state.get("follow_up_needs", [])]
    return {
        **schedule_result,
        "follow_up_tasks": tasks,
        "workflow_status": "followup_generated",
        "audit_log": [_event("generate_medication_and_followup", "draft_created", medication_count=len(schedule_result["medication_schedule"]), follow_up_count=len(tasks))],
    }


def safety_check(state: dict[str, Any]) -> dict[str, Any]:
    result = SafetyTool().check(state)
    return {
        **result,
        "workflow_status": "safety_checked",
        "audit_log": [_event("safety_check", "ok", risk_level=result["risk_level"], finding_codes=[item["code"] for item in result["safety_findings"]])],
    }


def request_human_review(state: dict[str, Any]) -> dict[str, Any]:
    """Persist the pending status before the interrupt pauses graph execution."""
    return {
        "human_review_status": "pending",
        "workflow_status": "awaiting_review",
        "audit_log": [_event("request_human_review", "pending", risk_level=state.get("risk_level", "low"))],
    }


def human_review(state: dict[str, Any]) -> dict[str, Any]:
    """Pause execution until an authenticated reviewer supplies a decision."""
    from langgraph.types import interrupt

    review_input = interrupt({
        "patient_id": state["patient_id"],
        "draft": {
            "instructions": state.get("discharge_instructions", {}),
            "medication_reminders": state.get("medication_reminders", []),
            "medication_schedule": state.get("medication_schedule", []),
            "follow_up_tasks": state.get("follow_up_tasks", []),
        },
        "evidence": state.get("retrieved_evidence", []),
        "external_drug_evidence": state.get("external_drug_evidence", []),
        "safety_findings": state.get("safety_findings", []),
        "allowed_decisions": ["approve", "edit", "reject", "escalate"],
    })
    decision = ReviewDecision.model_validate(review_input)
    return {
        "human_review_status": {
            "approve": "approved",
            "edit": "edited",
            "reject": "rejected",
            "escalate": "escalated",
        }[decision.decision],
        "reviewer_decision": decision.decision,
        "reviewer_id": decision.reviewer_id,
        "reviewer_role": decision.reviewer_role,
        "reviewer_notes": decision.notes,
        "reviewer_edits": decision.edits,
        "workflow_status": "review_decided",
        "audit_log": [_event("human_review", decision.decision, reviewer_id=decision.reviewer_id, reviewer_role=decision.reviewer_role)],
    }


def apply_reviewer_edits(state: dict[str, Any]) -> dict[str, Any]:
    edits = state.get("reviewer_edits", {})
    # Medication reminders are generated only from validated, reconciled source
    # fields.  A reviewer may request escalation instead of free-text editing.
    allowed = {"care_instructions", "warning_notes", "follow_up_tasks"}
    ignored = sorted(set(edits).difference(allowed))
    instructions = dict(state.get("discharge_instructions", {}))
    mapping_requires_confirmation = False
    for field in ("care_instructions", "warning_notes"):
        if field in edits:
            mapping_field = "care_instruction_evidence" if field == "care_instructions" else "warning_note_evidence"
            previous_claims = instructions.get(field, [])
            previous_mappings = instructions.get(mapping_field, [])
            # Preserve a citation only for text that is byte-for-byte unchanged.
            # A reviewer-created claim is intentionally shown as unmapped, so it
            # cannot inherit provenance from unrelated generated wording.
            available_mappings: dict[str, list[list[str]]] = {}
            for claim, mapping in zip(previous_claims, previous_mappings):
                available_mappings.setdefault(claim, []).append(mapping)
            revised_mappings: list[list[str]] = []
            for claim in edits[field]:
                matches = available_mappings.get(claim, [])
                if matches:
                    revised_mappings.append(matches.pop(0))
                else:
                    revised_mappings.append([])
                    mapping_requires_confirmation = True
            instructions[field] = edits[field]
            instructions[mapping_field] = revised_mappings
    if mapping_requires_confirmation:
        instructions["evidence_mapping_status"] = "reviewer_edit_requires_confirmation"
    update: dict[str, Any] = {"discharge_instructions": instructions, "workflow_status": "review_edits_applied"}
    for field in ("follow_up_tasks",):
        if field in edits:
            update[field] = edits[field]
    update["audit_log"] = [_event(
        "apply_reviewer_edits", "ok", ignored_fields=ignored,
        evidence_mapping_status=instructions.get("evidence_mapping_status", "generated"),
    )]
    return update


def finalize_discharge_plan(state: dict[str, Any]) -> dict[str, Any]:
    instructions = state.get("discharge_instructions", {})
    mapping_status = instructions.get("evidence_mapping_status", "generated")
    claim_evidence = []
    for claim_type, claims_key, mapping_key in (
        ("care_instruction", "care_instructions", "care_instruction_evidence"),
        ("warning_note", "warning_notes", "warning_note_evidence"),
    ):
        for index, claim in enumerate(instructions.get(claims_key, [])):
            mappings = instructions.get(mapping_key, [])
            claim_evidence.append({
                "claim_type": claim_type,
                "claim_index": index,
                "text": claim,
                "evidence_ids": mappings[index] if index < len(mappings) else [],
                "mapping_status": mapping_status if index < len(mappings) and mappings[index] else "reviewer_edit_requires_confirmation",
            })
    plan = FinalDischargePlan(
        patient_id=state["patient_id"], status="finalized",
        discharge_instructions=instructions.get("care_instructions", []),
        medication_reminders=state.get("medication_reminders", []),
        medication_schedule=state.get("medication_schedule", []),
        follow_up_tasks=state.get("follow_up_tasks", []),
        safety_findings=state.get("safety_findings", []), reviewer_id=state.get("reviewer_id"),
        reviewer_notes=state.get("reviewer_notes", ""),
        evidence_ids=instructions.get("evidence_ids", []),
        claim_evidence=claim_evidence,
    )
    return {"final_discharge_plan": plan.model_dump(mode="json"), "workflow_status": "finalized", "audit_log": [_event("finalize_discharge_plan", "finalized", reviewer_id=state.get("reviewer_id"))]}


def reject_discharge_plan(state: dict[str, Any]) -> dict[str, Any]:
    return {"workflow_status": "rejected", "audit_log": [_event("reject_discharge_plan", "rejected", reviewer_id=state.get("reviewer_id"))]}


def escalate_to_clinician(state: dict[str, Any]) -> dict[str, Any]:
    return {"human_review_status": "escalated", "workflow_status": "escalated", "audit_log": [_event("escalate_to_clinician", "escalated", finding_codes=[item["code"] for item in state.get("safety_findings", [])])]}
