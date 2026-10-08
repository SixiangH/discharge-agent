"""FHIR R4-shaped export for synthetic cases only.

The mapper is an exchange-contract draft, not a certified FHIR server and not
an authorization to connect to a production EHR.
"""

from typing import Any


def build_synthetic_bundle(case: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    patient_ref = f"Patient/{case['patient_id']}"
    entries: list[dict[str, Any]] = []
    for index, medication in enumerate(case.get("medication_list", [])):
        coding = [{"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": medication["rxnorm_cui"]}] if medication.get("rxnorm_cui") else []
        dosage = " ".join(filter(None, [medication.get("dosage"), medication.get("frequency"), medication.get("route")]))
        entries.append({"resource": {
            "resourceType": "MedicationRequest", "id": f"synthetic-medication-{index + 1}",
            "status": "stopped" if medication.get("discharge_action") == "stop" else "active",
            "intent": "order", "subject": {"reference": patient_ref},
            "medicationCodeableConcept": {"coding": coding, "text": medication["name"]},
            "dosageInstruction": [{"text": dosage}] if dosage else [],
            "note": [{"text": "Synthetic teaching export; clinician verification required."}],
        }})
    for index, allergy in enumerate(case.get("allergies", [])):
        entries.append({"resource": {
            "resourceType": "AllergyIntolerance", "id": f"synthetic-allergy-{index + 1}",
            "clinicalStatus": {"text": "active"}, "patient": {"reference": patient_ref},
            "code": {"text": allergy}, "note": [{"text": "Synthetic teaching export; unverified."}],
        }})
    plan = state.get("final_discharge_plan", {})
    entries.append({"resource": {
        "resourceType": "CarePlan", "id": "synthetic-discharge-plan", "status": "active" if plan.get("status") == "finalized" else "draft",
        "intent": "plan", "subject": {"reference": patient_ref},
        "description": "Synthetic discharge-plan support output; clinician approval required.",
        "activity": [{"detail": {"description": task}} for task in state.get("follow_up_tasks", [])],
    }})
    return {"resourceType": "Bundle", "type": "collection", "meta": {"tag": [{"system": "https://example.org/discharge-agent", "code": "synthetic-only"}]}, "entry": entries}
