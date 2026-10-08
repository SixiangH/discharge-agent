"""The bounded LangGraph workflow for the simulated prototype."""

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.graph.nodes import (
    apply_reviewer_edits, construct_patient_state, enrich_medications_with_external_evidence, escalate_to_clinician,
    finalize_discharge_plan, generate_discharge_instructions,
    generate_medication_and_followup, human_review, receive_case,
    reject_discharge_plan, request_human_review, retrieve_knowledge, safety_check, validate_case,
)
from app.graph.state import DischargeAgentState


def route_after_validation(state: dict[str, Any]) -> str:
    return "continue" if state.get("validation_status") == "valid" else "escalate"


def route_after_safety_check(state: dict[str, Any]) -> str:
    return "escalate" if state.get("risk_level") == "high" else "review"


def route_after_review(state: dict[str, Any]) -> str:
    return {"approve": "finalize", "edit": "apply_edits", "reject": "reject", "escalate": "escalate"}.get(
        state.get("reviewer_decision", ""), "escalate"
    )


def build_graph(checkpointer: Any | None = None):
    workflow = StateGraph(DischargeAgentState)
    workflow.add_node("receive_case", receive_case)
    workflow.add_node("validate_case", validate_case)
    workflow.add_node("construct_patient_state", construct_patient_state)
    workflow.add_node("enrich_medications_with_external_evidence", enrich_medications_with_external_evidence)
    workflow.add_node("retrieve_knowledge", retrieve_knowledge)
    workflow.add_node("generate_discharge_instructions", generate_discharge_instructions)
    workflow.add_node("generate_medication_and_followup", generate_medication_and_followup)
    workflow.add_node("safety_check", safety_check)
    workflow.add_node("request_human_review", request_human_review)
    workflow.add_node("human_review", human_review)
    workflow.add_node("apply_reviewer_edits", apply_reviewer_edits)
    workflow.add_node("finalize_discharge_plan", finalize_discharge_plan)
    workflow.add_node("reject_discharge_plan", reject_discharge_plan)
    workflow.add_node("escalate_to_clinician", escalate_to_clinician)
    workflow.set_entry_point("receive_case")
    workflow.add_edge("receive_case", "validate_case")
    workflow.add_conditional_edges("validate_case", route_after_validation, {"continue": "construct_patient_state", "escalate": "escalate_to_clinician"})
    workflow.add_edge("construct_patient_state", "enrich_medications_with_external_evidence")
    workflow.add_edge("enrich_medications_with_external_evidence", "retrieve_knowledge")
    workflow.add_edge("retrieve_knowledge", "generate_discharge_instructions")
    workflow.add_edge("generate_discharge_instructions", "generate_medication_and_followup")
    workflow.add_edge("generate_medication_and_followup", "safety_check")
    workflow.add_conditional_edges("safety_check", route_after_safety_check, {"review": "request_human_review", "escalate": "escalate_to_clinician"})
    workflow.add_edge("request_human_review", "human_review")
    workflow.add_conditional_edges("human_review", route_after_review, {"finalize": "finalize_discharge_plan", "apply_edits": "apply_reviewer_edits", "reject": "reject_discharge_plan", "escalate": "escalate_to_clinician"})
    workflow.add_edge("apply_reviewer_edits", "safety_check")
    workflow.add_edge("finalize_discharge_plan", END)
    workflow.add_edge("reject_discharge_plan", END)
    workflow.add_edge("escalate_to_clinician", END)
    return workflow.compile(checkpointer=checkpointer or MemorySaver())
