from langgraph.types import Command

from app.graph.workflow import build_graph
from app.tools.output_grounding_tool import OutputGroundingTool
from tests.test_end_to_end import complete_case


def test_free_text_dose_and_unapproved_follow_up_are_blocked():
    findings = OutputGroundingTool().check({
        "discharge_instructions": {"care_instructions": ["Take 5 mg every day."], "warning_notes": []},
        "follow_up_needs": ["Documented review"],
        "follow_up_tasks": ["Clinician-provided follow-up: Invented appointment"],
    })
    assert {item["code"] for item in findings} == {"unsupported_dose_or_frequency_claim", "unsupported_followup_task"}


def test_medication_action_requires_a_known_medication_name():
    findings = OutputGroundingTool().check({
        "medications": [{"name": "Amlodipine"}],
        "discharge_instructions": {"care_instructions": ["Start walking as tolerated.", "Start Amlodipine."], "warning_notes": []},
        "follow_up_needs": [], "follow_up_tasks": [],
    })
    assert [item["code"] for item in findings] == ["unsupported_medication_action_claim"]


def test_reviewer_edit_with_dose_is_rechecked_and_escalated():
    graph = build_graph()
    config = {"configurable": {"thread_id": "grounding-edit"}}
    paused = graph.invoke({"input_payload": complete_case()}, config=config)
    assert paused["workflow_status"] == "awaiting_review"
    result = graph.invoke(Command(resume={
        "decision": "edit", "reviewer_id": "reviewer-1", "reviewer_role": "pharmacist",
        "edits": {"care_instructions": ["Take 5 mg once daily."]},
    }), config=config)
    assert result["workflow_status"] == "escalated"
    assert any(item["code"] == "unsupported_dose_or_frequency_claim" for item in result["safety_findings"])
