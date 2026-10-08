"""Deterministic guardrails for the prototype, not clinical decision support."""

from typing import Any

from app.tools.output_grounding_tool import OutputGroundingTool


class SafetyTool:
    def check(self, state: dict[str, Any]) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        payload = state.get("validated_case", {})
        medications = state.get("medications", [])
        schedule_findings = state.get("medication_schedule_findings", [])
        external_findings = state.get("external_evidence_findings", [])
        reconciliation = payload.get("medication_reconciliation_status")
        allergies = {item.lower() for item in state.get("allergies", [])}

        if reconciliation in {"incomplete", "unknown"}:
            findings.append(self._finding("medication_reconciliation_incomplete", "high", "Medication reconciliation is incomplete or unknown; do not finalize this plan.", "medication_reconciliation_status", "escalate"))
        if reconciliation == "complete" and not medications:
            findings.append(self._finding("medication_list_missing", "high", "Medication reconciliation is marked complete but no medication list was supplied.", "medication_list", "escalate"))
        if reconciliation == "no_discharge_medications" and medications:
            findings.append(self._finding("medication_reconciliation_conflict", "high", "The case says there are no discharge medications but a medication list is present.", "medication_list", "escalate"))

        seen: dict[str, tuple[str | None, str | None]] = {}
        for medication in medications:
            name = medication.get("name", "").strip()
            normalized = name.lower()
            if not name or (medication.get("discharge_action", "continue") != "stop" and (not medication.get("dosage") or not medication.get("frequency"))):
                findings.append(self._finding("medication_details_incomplete", "high", f"Medication '{name or 'unknown'}' lacks a name, dosage, or frequency.", "medication_list", "escalate"))
            if normalized in allergies:
                findings.append(self._finding("allergy_medication_conflict", "high", f"Medication '{name}' conflicts with a recorded allergy.", "allergies", "escalate"))
            signature = (medication.get("dosage"), medication.get("frequency"))
            if normalized in seen and seen[normalized] != signature:
                findings.append(self._finding("duplicate_medication_conflict", "high", f"Medication '{name}' has conflicting dosage or frequency entries.", "medication_list", "escalate"))
            seen[normalized] = signature

        if not state.get("follow_up_needs"):
            findings.append(self._finding("follow_up_missing", "warning", "No clinician-provided follow-up task is available for the reviewer to confirm.", "follow_up_needs", "review"))
        if not state.get("retrieved_evidence"):
            findings.append(self._finding("evidence_missing", "high", "No approved guidance was retrieved to support the draft.", "retrieved_evidence", "escalate"))

        # These findings come from the deterministic schedule builder and are
        # kept separate from free-text generation so their source is auditable.
        findings.extend(schedule_findings)
        findings.extend(external_findings)
        findings.extend(OutputGroundingTool().check(state))

        instructions = state.get("discharge_instructions", {})
        if instructions.get("evidence_mapping_status") == "reviewer_edit_requires_confirmation":
            findings.append(self._finding(
                "reviewer_edited_claim_requires_evidence_confirmation", "warning",
                "One or more reviewer-edited education claims no longer has the original generated evidence mapping; confirm its support before approval.",
                "discharge_instructions", "review",
            ))

        if "medication_reminders" in state.get("reviewer_edits", {}):
            findings.append(self._finding(
                "medication_reminder_edit_not_permitted", "high",
                "Medication reminders must be regenerated from reconciled source fields, not manually edited.",
                "reviewer_edits", "escalate",
            ))

        notes = " ".join(payload.get("relevant_notes", [])).lower()
        injection_terms = ("ignore previous", "ignore the rules", "auto approve", "bypass review")
        if any(term in notes for term in injection_terms):
            findings.append(self._finding("untrusted_instruction", "high", "Untrusted note requests a workflow bypass; it was not used as an instruction.", "relevant_notes", "escalate"))

        risk_level = "high" if any(item["severity"] == "high" for item in findings) else ("medium" if findings else "low")
        return {"risk_level": risk_level, "safety_findings": findings}

    @staticmethod
    def _finding(code: str, severity: str, message: str, field: str, action: str) -> dict[str, Any]:
        return {"code": code, "severity": severity, "message": message, "affected_field": field, "required_action": action, "evidence": []}
