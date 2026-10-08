"""Deterministic checks for claims introduced after draft generation.

This is intentionally conservative.  Medication changes belong in the
reconciled medication list and follow-up tasks belong in the source case, not
in free-text instructions or reviewer edits.
"""

import re
from typing import Any


class OutputGroundingTool:
    dose_or_frequency_pattern = re.compile(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|units?)\b|\b(?:once|twice|three times|daily|weekly|every\s+\d+\s*(?:hours?|days?))\b",
        re.IGNORECASE,
    )
    medication_action_pattern = re.compile(r"\b(?:take|start|stop|continue|increase|decrease)\b", re.IGNORECASE)

    def check(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        instructions = state.get("discharge_instructions", {})
        free_text = list(instructions.get("care_instructions", [])) + list(instructions.get("warning_notes", []))
        medication_names = [
            item.get("name", "").lower() for item in state.get("medications", []) if item.get("name")
        ]
        for index, text in enumerate(free_text):
            if self.dose_or_frequency_pattern.search(text):
                findings.append(self._finding("unsupported_dose_or_frequency_claim", f"Instruction {index + 1} contains a dose or frequency. Medication details must come only from the reconciled schedule.", "discharge_instructions"))
            if self.medication_action_pattern.search(text) and any(name in text.lower() for name in medication_names):
                findings.append(self._finding("unsupported_medication_action_claim", f"Instruction {index + 1} contains a medication action. Use the structured medication schedule instead.", "discharge_instructions"))

        expected_followups = {
            f"Clinician-provided follow-up: {item}" for item in state.get("follow_up_needs", [])
        }
        for task in state.get("follow_up_tasks", []):
            if task not in expected_followups:
                findings.append(self._finding("unsupported_followup_task", "A follow-up task was not present in the clinician-provided source list.", "follow_up_tasks"))
        return findings

    @staticmethod
    def _finding(code: str, message: str, field: str) -> dict[str, Any]:
        return {
            "code": code, "severity": "high", "message": message,
            "affected_field": field, "required_action": "escalate", "evidence": [],
        }
