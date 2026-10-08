"""Small, transparent retriever for approved simulated guidance."""

import json
import re
from pathlib import Path
from typing import Any


class RetrievalTool:
    def __init__(self, curated_path: str | Path | None = None) -> None:
        knowledge_dir = Path(__file__).parents[1] / "data" / "knowledge_base"
        self.documents = []
        for knowledge_file in (knowledge_dir / "guidance.json", Path(curated_path) if curated_path else knowledge_dir / "curated_guidance.json"):
            self.documents.extend(json.loads(knowledge_file.read_text(encoding="utf-8")))
        self.documents = [document for document in self.documents if document.get("approval_status", "approved") == "approved"]
        if not self.documents:
            raise ValueError("Knowledge base contains no approved documents")

    def retrieve(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        query_terms = self._tokens(query)
        ranked: list[tuple[float, dict[str, Any]]] = []
        for document in self.documents:
            keywords = self._tokens(" ".join(document["keywords"]))
            searchable = keywords | self._tokens(document["title"]) | self._tokens(document["content"])
            overlap = query_terms.intersection(searchable)
            score = sum(2 if term in keywords else 1 for term in overlap)
            if score:
                ranked.append((score, document))
        if not ranked:
            ranked = [(1, self.documents[0])]
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "evidence_id": document["evidence_id"],
                "source": document["source"],
                "title": document["title"],
                "content": document["content"],
                "score": round(score / max(1, len(query_terms) * 2), 3),
                "version": document.get("version", "1.0"),
                "source_url": document.get("source_url"),
                "approval_status": document.get("approval_status", "approved"),
                "reviewed_at": document.get("reviewed_at"),
                "review_scope": document.get("review_scope"),
            }
            for score, document in ranked[:limit]
        ]

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 1}
