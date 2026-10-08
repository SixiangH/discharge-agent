from langgraph.types import Command

from app.graph.workflow import build_graph


def complete_case() -> dict:
    return {
        "patient_id": "SIM-E2E-1",
        "diagnosis": "Hypertension",
        "discharge_summary": "Synthetic discharge summary.",
        "medication_reconciliation_status": "complete",
        "medication_list": [{"name": "Amlodipine", "dosage": "5 mg", "frequency": "once daily"}],
        "allergies": [],
        "follow_up_needs": ["Synthetic blood pressure review"],
        "relevant_notes": ["Synthetic teaching case."],
    }


def test_complete_case_requires_explicit_approval_before_finalization():
    graph = build_graph()
    config = {"configurable": {"thread_id": "e2e-approved"}}
    paused = graph.invoke({"input_payload": complete_case()}, config=config)
    assert paused["workflow_status"] == "awaiting_review"
    assert "__interrupt__" in paused

    final = graph.invoke(Command(resume={"decision": "approve", "reviewer_id": "reviewer-1"}), config=config)
    assert final["workflow_status"] == "finalized"
    assert final["final_discharge_plan"]["reviewer_id"] == "reviewer-1"


def test_high_risk_case_is_escalated_without_reviewer_approval_path():
    graph = build_graph()
    case = complete_case()
    case["allergies"] = ["Amlodipine"]
    result = graph.invoke({"input_payload": case}, config={"configurable": {"thread_id": "e2e-escalated"}})
    assert result["workflow_status"] == "escalated"
    assert "__interrupt__" not in result
    assert any(item["code"] == "allergy_medication_conflict" for item in result["safety_findings"])
