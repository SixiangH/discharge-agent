"""Minimal reviewer API and local UI for simulated teaching cases only."""

from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import BaseModel

from app.graph.workflow import build_graph
from app.persistence.case_repository import CaseRepository
from app.schemas.patient_schema import PatientCaseInput, ReviewDecision
from app.tools.external.pubmed_tool import PubMedEvidenceTool
from app.api.reviewer_ui import render_reviewer_ui
from app.interoperability.fhir_mapper import build_synthetic_bundle
from app.services.knowledge_curation import (
    KnowledgeCandidateCreate, KnowledgeCurationRepository, KnowledgeReviewDecision,
)


class CaseSubmission(BaseModel):
    case: PatientCaseInput


class EvidenceSearchRequest(BaseModel):
    """A generic topic only; never submit a patient narrative to PubMed."""

    topic: str
    limit: int = 5


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if key != "__interrupt__"}


def create_app(database_path: str | Path | None = None, curation_path: str | Path | None = None) -> FastAPI:
    app = FastAPI(title="Simulated Discharge Planning Agent", version="0.1.0")
    resolved_database_path = Path(database_path or Path("app/data/discharge_agent.db"))
    repository = CaseRepository(resolved_database_path)
    curation_repository = KnowledgeCurationRepository(curation_path)
    # check_same_thread=False is required because FastAPI can handle requests on
    # different worker threads. This remains a single-process teaching prototype.
    checkpoint_connection = sqlite3.connect(resolved_database_path, check_same_thread=False)
    checkpointer = SqliteSaver(checkpoint_connection)
    checkpointer.setup()
    graph = build_graph(checkpointer=checkpointer)

    @app.get("/", response_class=HTMLResponse)
    def reviewer_ui() -> str:
        return render_reviewer_ui()

    @app.post("/cases")
    def submit_case(submission: CaseSubmission) -> dict[str, Any]:
        case_id = str(uuid4())
        thread_id = f"case-{case_id}"
        state = graph.invoke({"input_payload": submission.case.model_dump(mode="json")}, config={"configurable": {"thread_id": thread_id}})
        repository.save_state(case_id, thread_id, state)
        return {
            "case_id": case_id,
            "workflow_status": state.get("workflow_status"),
            "review_required": "__interrupt__" in state,
            "state": _public_state(state),
        }

    @app.get("/cases")
    def list_cases() -> list[dict[str, Any]]:
        return repository.list_cases()

    @app.get("/cases/{case_id}")
    def get_case(case_id: str) -> dict[str, Any]:
        case = repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return case

    @app.get("/cases/{case_id}/fhir-r4-bundle")
    def get_synthetic_fhir_bundle(case_id: str) -> dict[str, Any]:
        case = repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found")
        return build_synthetic_bundle(case["state"]["validated_case"], case["state"])

    def finalized_case_or_error(case_id: str) -> dict[str, Any]:
        case = repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found")
        if case["workflow_status"] != "finalized":
            raise HTTPException(
                status_code=409,
                detail="Only a clinician-approved finalized plan can be exported",
            )
        return case

    @app.get("/cases/{case_id}/export/final-plan.json")
    def export_final_plan_json(case_id: str) -> dict[str, Any]:
        """Export only the approved final plan, not a pending draft."""
        case = finalized_case_or_error(case_id)
        return case["state"]["final_discharge_plan"]

    @app.get("/cases/{case_id}/export/fhir-r4-bundle.json")
    def export_final_plan_fhir_bundle(case_id: str) -> dict[str, Any]:
        """Export a synthetic FHIR R4-shaped bundle after approval only."""
        case = finalized_case_or_error(case_id)
        return build_synthetic_bundle(case["state"]["validated_case"], case["state"])

    @app.post("/cases/{case_id}/review")
    def review_case(case_id: str, decision: ReviewDecision) -> dict[str, Any]:
        case = repository.get_case(case_id)
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found")
        if case["workflow_status"] != "awaiting_review":
            raise HTTPException(status_code=409, detail="Case is not awaiting review")
        state = graph.invoke(Command(resume=decision.model_dump(mode="json")), config={"configurable": {"thread_id": case["thread_id"]}})
        repository.save_state(case_id, case["thread_id"], state)
        return {"case_id": case_id, "workflow_status": state.get("workflow_status"), "state": _public_state(state)}

    @app.post("/evidence/literature-search")
    def literature_search(request: EvidenceSearchRequest) -> dict[str, Any]:
        """Retrieve unapproved bibliography candidates for offline curation.

        Results are intentionally not inserted into the runtime RAG knowledge
        base and cannot change a discharge plan until separately reviewed.
        """
        return PubMedEvidenceTool().search_for_curation(request.topic, request.limit)

    @app.get("/knowledge/candidates")
    def list_knowledge_candidates(status: str | None = None) -> list[dict[str, Any]]:
        return curation_repository.list(status)

    @app.post("/knowledge/candidates")
    def submit_knowledge_candidate(candidate: KnowledgeCandidateCreate) -> dict[str, Any]:
        return curation_repository.submit(candidate)

    @app.post("/knowledge/{evidence_id}/review")
    def review_knowledge_candidate(evidence_id: str, decision: KnowledgeReviewDecision) -> dict[str, Any]:
        try:
            reviewed = curation_repository.review(evidence_id, decision)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if reviewed is None:
            raise HTTPException(status_code=404, detail="Evidence item not found")
        return reviewed

    return app


app = create_app()
