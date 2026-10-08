"""Deterministic medication reconciliation and reminder drafting.

The tool intentionally does not calculate doses, administration times, drug
interactions, or patient-specific recommendations.  It converts only supplied,
reconciled discharge medication fields into a reviewer-facing reminder draft.
"""

from typing import Any


class MedicationScheduleTool:
    """Build traceable medication reminders from structured source fields."""

    def build(self, medications: list[dict[str, Any]]) -> dict[str, Any]:
        schedule: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []

        for index, medication in enumerate(medications):
            item, item_findings = self._build_item(medication, index)
            schedule.append(item)
            findings.extend(item_findings)

        return {
            "medication_schedule": schedule,
            "medication_reminders": [item["reminder"] for item in schedule],
            "medication_schedule_findings": findings,
        }

    def _build_item(self, medication: dict[str, Any], index: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        name = self._text(medication.get("name")) or "Unknown medication"
        action = medication.get("discharge_action", "continue")
        dosage = self._text(medication.get("dosage"))
        frequency = self._text(medication.get("frequency"))
        route = self._text(medication.get("route"))
        is_prn = bool(medication.get("is_prn"))
        prn_indication = self._text(medication.get("prn_indication"))
        max_frequency = self._text(medication.get("max_frequency"))
        source_fields = ["name", "discharge_action"]
        findings: list[dict[str, Any]] = []

        if action == "stop":
            reminder = f"Stop {name} as listed in the reconciled discharge medication list."
        else:
            parts = [f"{action.title()} {name}"]
            if dosage:
                parts.append(dosage)
                source_fields.append("dosage")
            if frequency:
                parts.append(frequency)
                source_fields.append("frequency")
            if route:
                parts.append(f"via {route}")
                source_fields.append("route")
            reminder = " — ".join(parts) + "."

        if is_prn:
            source_fields.append("is_prn")
            if prn_indication:
                reminder = reminder[:-1] + f" when needed for {prn_indication}."
                source_fields.append("prn_indication")
            if max_frequency:
                reminder = reminder[:-1] + f" Do not exceed {max_frequency}."
                source_fields.append("max_frequency")

        required = [] if action == "stop" else [
            field for field, value in (("dosage", dosage), ("frequency", frequency)) if not value
        ]
        if is_prn:
            required.extend(field for field, value in (("prn_indication", prn_indication), ("max_frequency", max_frequency)) if not value)
        if required:
            findings.append(self._finding(
                "medication_schedule_details_missing", "high",
                f"Medication '{name}' cannot be used for a final reminder until these source fields are confirmed: {', '.join(required)}.",
                index,
            ))
        if action != "stop" and not route:
            findings.append(self._finding(
                "medication_route_missing", "warning",
                f"Medication '{name}' has no route in the reconciled source; reviewer confirmation is required.",
                index,
            ))

        item = {
            "medication_name": name,
            "discharge_action": action,
            "reminder": reminder,
            "source_fields": source_fields,
            "source_reference": self._text(medication.get("source_reference")),
            "rxnorm_cui": self._text(medication.get("rxnorm_cui")),
            "requires_clinician_review": bool(findings),
        }
        return item, findings

    @staticmethod
    def _text(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _finding(code: str, severity: str, message: str, index: int) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "affected_field": f"medication_list[{index}]",
            "required_action": "escalate" if severity == "high" else "review",
            "evidence": [],
        }
