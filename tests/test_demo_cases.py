import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DISCHARGE_LLM_ENABLED", "false")
    monkeypatch.setenv("EXTERNAL_EVIDENCE_ENABLED", "false")
    return TestClient(create_app(tmp_path / "cases.db", tmp_path / "curated.json"))


def test_catalogue_has_seven_original_inputs_without_creating_cases(client):
    response = client.get("/demo-cases")
    assert response.status_code == 200
    catalogue = response.json()
    assert len(catalogue) == 7
    assert len({item["id"] for item in catalogue}) == 7
    directory = Path(__file__).resolve().parents[1] / "app/data/demo_cases"
    for item in catalogue:
        assert item["name"] and item["description"]
        assert item["case"] == json.loads((directory / f"{item['id']}.json").read_text(encoding="utf-8"))
    assert client.get("/cases").json() == []


@pytest.mark.parametrize("index,status,risk,finding", [
    (0, "awaiting_review", "low", None),
    (1, "awaiting_review", "low", None),
    (2, "awaiting_review", "low", None),
    (3, "escalated", "high", "duplicate_medication_conflict"),
    (4, "escalated", "high", "medication_reconciliation_incomplete"),
    (5, "awaiting_review", "medium", "follow_up_missing"),
    (6, "escalated", "high", "allergy_medication_conflict"),
])
def test_demo_inputs_follow_normal_safety_and_approval_gates(client, index, status, risk, finding):
    case = client.get("/demo-cases").json()[index]["case"]
    response = client.post("/cases", json={"case": case})
    assert response.status_code == 200
    body = response.json()
    assert body["workflow_status"] == status
    assert body["state"]["risk_level"] == risk
    assert body["state"]["discharge_instructions"]["generator"] == "deterministic"
    if finding:
        assert finding in {item["code"] for item in body["state"]["safety_findings"]}
    case_id = body["case_id"]
    assert client.get(f"/cases/{case_id}/export/final-plan.json").status_code == 409
    reviewed = client.post(f"/cases/{case_id}/review", json={"decision": "approve", "reviewer_id": "synthetic-demo-test"})
    if status == "escalated":
        assert reviewed.status_code == 409
    else:
        assert reviewed.status_code == 200
        assert reviewed.json()["workflow_status"] == "finalized"


def test_catalogue_uses_fresh_inputs_and_fixed_file_list(client):
    catalogue = client.get("/demo-cases").json()
    original_id = catalogue[0]["case"]["patient_id"]
    catalogue[0]["case"]["patient_id"] = "CHANGED-IN-BROWSER"
    assert client.get("/demo-cases").json()[0]["case"]["patient_id"] == original_id
    assert client.get("/demo-cases/not-a-file").status_code == 404
