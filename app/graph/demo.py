"""Run a complete simulated case, including an explicit reviewer resume."""

import json
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from langgraph.types import Command

from app.graph.workflow import build_graph


sample_case = {
    "patient_id": "SIM-1001",
    "age": 68,
    "gender": "female",
    "diagnosis": "Type 2 diabetes and hypertension",
    "discharge_summary": "Simulated patient discharged after blood pressure stabilization and diabetes education.",
    "medication_reconciliation_status": "complete",
    "medication_list": [
        {"name": "Metformin", "dosage": "500 mg", "frequency": "twice daily", "route": "oral"},
        {"name": "Amlodipine", "dosage": "5 mg", "frequency": "once daily", "route": "oral"},
    ],
    "allergies": ["Penicillin"],
    "follow_up_needs": ["Cardiology follow-up in 2 weeks", "Home blood pressure monitoring"],
    "relevant_notes": ["Synthetic teaching case only."],
}


if __name__ == "__main__":
    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-case-1001"}}
    paused = graph.invoke({"input_payload": sample_case}, config=config)
    if "__interrupt__" not in paused:
        raise RuntimeError(f"Expected a human-review interrupt, got {paused.get('workflow_status')}")

    final = graph.invoke(Command(resume={
        "decision": "approve",
        "reviewer_id": "demo-clinician",
        "notes": "Reviewed simulated draft and evidence.",
    }), config=config)
    print(json.dumps(final["final_discharge_plan"], indent=2))
