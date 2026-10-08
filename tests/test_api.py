from fastapi.testclient import TestClient

from app.api.main import create_app
from tests.test_end_to_end import complete_case


def test_api_persists_case_and_allows_review(tmp_path):
    database_path = tmp_path / "cases.db"
    client = TestClient(create_app(database_path, tmp_path / "curated.json"))
    submitted = client.post("/cases", json={"case": complete_case()})
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["review_required"] is True

    stored = client.get(f"/cases/{body['case_id']}")
    assert stored.status_code == 200
    assert stored.json()["workflow_status"] == "awaiting_review"

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert "Discharge Planning Reviewer" in dashboard.text
    assert "Upload JSON file" in dashboard.text
    assert "selectJsonFile" in dashboard.text
    assert "Use only one input method" in dashboard.text
    assert "Create draft from text" not in dashboard.text
    assert "Agent workflow trace" in dashboard.text
    assert "Evidence-to-claim mapping" in dashboard.text
    assert dashboard.text.index("New synthetic case") < dashboard.text.index("<h2>Cases</h2>")
    listed = client.get("/cases")
    assert listed.status_code == 200
    assert listed.json()[0]["case_id"] == body["case_id"]
    fhir_bundle = client.get(f"/cases/{body['case_id']}/fhir-r4-bundle")
    assert fhir_bundle.status_code == 200
    assert fhir_bundle.json()["resourceType"] == "Bundle"
    assert any(entry["resource"]["resourceType"] == "MedicationRequest" for entry in fhir_bundle.json()["entry"])
    assert client.get(f"/cases/{body['case_id']}/export/final-plan.json").status_code == 409

    # A new application instance simulates an API restart. The SQLite graph
    # checkpoint must still allow the pending interrupt to resume.
    restarted_client = TestClient(create_app(database_path, tmp_path / "curated.json"))
    reviewed = restarted_client.post(f"/cases/{body['case_id']}/review", json={"decision": "approve", "reviewer_id": "api-reviewer"})
    assert reviewed.status_code == 200
    assert reviewed.json()["workflow_status"] == "finalized"
    final_export = restarted_client.get(f"/cases/{body['case_id']}/export/final-plan.json")
    assert final_export.status_code == 200
    assert final_export.json()["status"] == "finalized"
    fhir_export = restarted_client.get(f"/cases/{body['case_id']}/export/fhir-r4-bundle.json")
    assert fhir_export.status_code == 200
    assert fhir_export.json()["resourceType"] == "Bundle"
