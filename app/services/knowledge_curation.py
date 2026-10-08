"""Local evidence curation lifecycle for the synthetic knowledge base."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl


class KnowledgeCandidateCreate(BaseModel):
    title: str = Field(min_length=5, max_length=240)
    content: str = Field(min_length=20, max_length=4000)
    source_url: HttpUrl
    keywords: list[str] = Field(default_factory=list)
    review_scope: str = Field(min_length=10, max_length=500)
    expires_at: str | None = None


class KnowledgeReviewDecision(BaseModel):
    decision: str = Field(pattern="^(approve|retire|reject)$")
    reviewer_id: str = Field(min_length=1)
    reviewer_role: str = Field(pattern="^(clinician|pharmacist)$")
    review_reason: str = Field(min_length=5, max_length=1000)
    replacement_evidence_id: str | None = None


class KnowledgeCurationRepository:
    """JSON-backed local repository so approved items are visible to RAG.

    It is deliberately intended for one local teaching deployment. Production
    content governance needs authenticated identity, version control and a
    managed content store.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path(__file__).parents[1] / "data" / "knowledge_base" / "curated_guidance.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def list(self, status: str | None = None) -> list[dict]:
        items = self._read()
        return [item for item in items if status is None or item["approval_status"] == status]

    def submit(self, candidate: KnowledgeCandidateCreate) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        item = {
            "evidence_id": f"candidate-{uuid4().hex[:12]}", "title": candidate.title,
            "content": candidate.content, "source": "curation_candidate", "source_url": str(candidate.source_url),
            "keywords": [keyword.strip().lower() for keyword in candidate.keywords if keyword.strip()],
            "review_scope": candidate.review_scope, "expires_at": candidate.expires_at,
            "approval_status": "candidate", "version": "0.1", "submitted_at": now,
            "reviewed_at": None, "reviewer_id": None, "reviewer_role": None,
            "review_reason": None, "replacement_evidence_id": None,
        }
        items = self._read(); items.append(item); self._write(items)
        return item

    def review(self, evidence_id: str, decision: KnowledgeReviewDecision) -> dict | None:
        items = self._read()
        for item in items:
            if item["evidence_id"] != evidence_id:
                continue
            if item["approval_status"] not in {"candidate", "approved"}:
                raise ValueError("Only candidate or approved evidence can be reviewed")
            item["approval_status"] = {"approve": "approved", "retire": "retired", "reject": "retired"}[decision.decision]
            item["version"] = "1.0" if decision.decision == "approve" else item["version"]
            item["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            item["reviewer_id"] = decision.reviewer_id
            item["reviewer_role"] = decision.reviewer_role
            item["review_reason"] = decision.review_reason
            item["replacement_evidence_id"] = decision.replacement_evidence_id
            self._write(items)
            return item
        return None

    def _read(self) -> list[dict]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, items: list[dict]) -> None:
        self.path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
