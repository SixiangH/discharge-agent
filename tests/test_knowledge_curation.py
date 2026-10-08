from pathlib import Path

from app.services.knowledge_curation import (
    KnowledgeCandidateCreate, KnowledgeCurationRepository, KnowledgeReviewDecision,
)
from app.tools.retrieval_tool import RetrievalTool


def test_only_approved_curated_evidence_is_retrievable(tmp_path: Path):
    path = tmp_path / "curated.json"
    repository = KnowledgeCurationRepository(path)
    candidate = repository.submit(KnowledgeCandidateCreate(
        title="Synthetic transition evidence", content="Synthetic reviewed evidence supports a clinician-confirmed transition plan.",
        source_url="https://example.org/synthetic-guideline", keywords=["synthetic-transition"],
        review_scope="Synthetic teaching evidence; no patient-specific prescribing.",
    ))
    assert all(item["evidence_id"] != candidate["evidence_id"] for item in RetrievalTool(path).retrieve("synthetic-transition"))

    approved = repository.review(candidate["evidence_id"], KnowledgeReviewDecision(
        decision="approve", reviewer_id="reviewer-1", reviewer_role="clinician", review_reason="Source and scope reviewed for synthetic teaching use.",
    ))
    assert approved["approval_status"] == "approved"
    evidence = RetrievalTool(path).retrieve("synthetic-transition")
    assert evidence[0]["evidence_id"] == candidate["evidence_id"]
    assert evidence[0]["reviewed_at"]

    retired = repository.review(candidate["evidence_id"], KnowledgeReviewDecision(
        decision="retire", reviewer_id="reviewer-2", reviewer_role="pharmacist", review_reason="Superseded for this synthetic knowledge base.", replacement_evidence_id="replacement-v1",
    ))
    assert retired["approval_status"] == "retired"
    assert all(item["evidence_id"] != candidate["evidence_id"] for item in RetrievalTool(path).retrieve("synthetic-transition"))
