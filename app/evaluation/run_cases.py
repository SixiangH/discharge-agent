"""Run each synthetic case and report the safe workflow outcome."""

import json
from pathlib import Path

from app.graph.workflow import build_graph


def run() -> list[dict[str, str]]:
    graph = build_graph()
    cases_dir = Path(__file__).parents[1] / "data" / "synthetic_cases"
    results: list[dict[str, str]] = []
    for case_file in sorted(cases_dir.glob("*.json")):
        case = json.loads(case_file.read_text(encoding="utf-8"))
        state = graph.invoke({"input_payload": case}, config={"configurable": {"thread_id": f"evaluation-{case['patient_id']}"}})
        expected = "awaiting_review" if case_file.name == "complete_case.json" else "escalated"
        results.append({
            "case": case_file.name,
            "workflow_status": state["workflow_status"],
            "risk_level": state.get("risk_level", "not_assessed"),
            "expected_safe_outcome": expected,
            "passed": state["workflow_status"] == expected,
        })
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
