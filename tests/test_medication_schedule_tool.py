from app.tools.medication_schedule_tool import MedicationScheduleTool
from app.tools.safety_tool import SafetyTool


def test_schedule_is_traceable_to_reconciled_source_fields():
    result = MedicationScheduleTool().build([
        {
            "name": "Amlodipine", "dosage": "5 mg", "frequency": "once daily",
            "route": "oral", "discharge_action": "continue", "rxnorm_cui": "17767",
            "source_reference": "synthetic-order-1",
        }
    ])

    item = result["medication_schedule"][0]
    assert item["reminder"] == "Continue Amlodipine — 5 mg — once daily — via oral."
    assert item["source_fields"] == ["name", "discharge_action", "dosage", "frequency", "route"]
    assert item["rxnorm_cui"] == "17767"
    assert item["requires_clinician_review"] is False
    assert result["medication_schedule_findings"] == []


def test_prn_without_indication_or_limit_cannot_be_finalized():
    result = MedicationScheduleTool().build([
        {"name": "Synthetic PRN medicine", "dosage": "1 tablet", "frequency": "as needed", "is_prn": True}
    ])

    codes = {finding["code"] for finding in result["medication_schedule_findings"]}
    assert codes == {"medication_schedule_details_missing", "medication_route_missing"}
    safety = SafetyTool().check({
        "validated_case": {"medication_reconciliation_status": "complete", "relevant_notes": []},
        "medications": [{"name": "Synthetic PRN medicine", "dosage": "1 tablet", "frequency": "as needed", "is_prn": True}],
        "medication_schedule_findings": result["medication_schedule_findings"],
        "allergies": [], "follow_up_needs": ["Synthetic follow-up"],
        "retrieved_evidence": [{"evidence_id": "test"}],
    })
    assert safety["risk_level"] == "high"


def test_manual_medication_reminder_edit_requires_escalation():
    result = SafetyTool().check({
        "validated_case": {"medication_reconciliation_status": "no_discharge_medications", "relevant_notes": []},
        "medications": [], "medication_schedule_findings": [], "allergies": [],
        "follow_up_needs": ["Synthetic follow-up"], "retrieved_evidence": [{"evidence_id": "test"}],
        "reviewer_edits": {"medication_reminders": ["Take an unverified medicine"]},
    })
    assert result["risk_level"] == "high"
    assert any(item["code"] == "medication_reminder_edit_not_permitted" for item in result["safety_findings"])
