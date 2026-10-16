"""Read-only catalogue of the seven supplied synthetic presentation inputs."""

import json
from pathlib import Path
from typing import Any


_CASE_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "demo_cases"
# Fixed filenames: no client-supplied filesystem paths are accepted.
_CATALOGUE = (
    ("01_low_risk_diabetes_hypertension", "01 - Diabetes and hypertension", "A complete medicine list and documented follow-up tasks."),
    ("02_medication_action_mix", "02 - Medication action mix", "Source orders include different discharge actions."),
    ("03_prn_complete", "03 - As-needed medicine", "An as-needed medicine includes its reason and maximum frequency."),
    ("04_duplicate_medication_conflict", "04 - Conflicting medicine entries", "The same medicine appears with different strengths."),
    ("05_reconciliation_unknown", "05 - Unconfirmed medicine list", "The source medicine list has not been confirmed."),
    ("06_followup_missing_warning", "06 - Missing follow-up", "The discharge record does not supply follow-up tasks."),
    ("07_allergy_conflict", "07 - Allergy conflict", "A medicine is also recorded in the allergy list."),
)


def list_demo_cases() -> list[dict[str, Any]]:
    """Return fresh input objects without creating cases or calling the model."""
    return [
        {
            "id": case_id,
            "name": name,
            "description": description,
            "case": json.loads((_CASE_DIRECTORY / f"{case_id}.json").read_text(encoding="utf-8")),
        }
        for case_id, name, description in _CATALOGUE
    ]
