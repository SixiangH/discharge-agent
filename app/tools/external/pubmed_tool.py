"""Public PubMed metadata search for offline evidence curation only."""

from datetime import datetime, timezone
from typing import Any

from app.tools.external.cache import ExternalEvidenceCache
from app.tools.external.http_client import JsonFetcher, fetch_json


class PubMedEvidenceTool:
    search_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    summary_endpoint = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, cache: ExternalEvidenceCache | None = None, fetcher: JsonFetcher = fetch_json) -> None:
        self.cache = cache
        self.fetcher = fetcher

    def search_for_curation(self, topic: str, limit: int = 5) -> dict[str, Any]:
        """Return bibliography candidates only; never adds them to approved RAG."""
        query = {"db": "pubmed", "term": topic, "retmax": str(min(max(limit, 1), 10)), "retmode": "json", "sort": "relevance"}
        cached = self.cache.get("pubmed_search", query) if self.cache else None
        if cached is not None:
            return {**cached, "cache_status": "hit"}
        try:
            ids = self.fetcher(self.search_endpoint, query).get("esearchresult", {}).get("idlist", [])
            summaries = self.fetcher(self.summary_endpoint, {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}).get("result", {}) if ids else {}
            articles = [
                {"pmid": pmid, "title": summaries.get(pmid, {}).get("title"), "source": summaries.get(pmid, {}).get("source"), "pubdate": summaries.get(pmid, {}).get("pubdate"), "authors": [author.get("name") for author in summaries.get(pmid, {}).get("authors", [])[:3] if author.get("name")]}
                for pmid in ids
            ]
            result = {"tool": "pubmed", "status": "matched" if articles else "not_found", "topic": topic, "articles": articles, "source_url": self.search_endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "miss", "curation_required": True}
        except Exception as error:
            result = {"tool": "pubmed", "status": "unavailable", "topic": topic, "articles": [], "source_url": self.search_endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "none", "curation_required": True, "error_code": type(error).__name__}
        if self.cache and result["status"] != "unavailable":
            self.cache.set("pubmed_search", query, result)
        return result
