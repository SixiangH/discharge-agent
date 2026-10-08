"""RxNorm public terminology lookup.  It never guesses an ambiguous match."""

from datetime import datetime, timezone
from typing import Any

from app.tools.external.cache import ExternalEvidenceCache
from app.tools.external.http_client import JsonFetcher, fetch_json


class RxNormTool:
    endpoint = "https://rxnav.nlm.nih.gov/REST/rxcui.json"

    def __init__(self, cache: ExternalEvidenceCache | None = None, fetcher: JsonFetcher = fetch_json) -> None:
        self.cache = cache
        self.fetcher = fetcher

    def lookup(self, medication_name: str) -> dict[str, Any]:
        query = {"name": medication_name, "search": "2"}
        cached = self.cache.get("rxnorm", query) if self.cache else None
        if cached is not None:
            return {**cached, "cache_status": "hit"}
        try:
            response = self.fetcher(self.endpoint, query)
            candidates = response.get("idGroup", {}).get("rxnormId", [])
            status = "matched" if len(candidates) == 1 else ("ambiguous" if len(candidates) > 1 else "not_found")
            result = {
                "tool": "rxnorm", "status": status, "query": medication_name,
                "rxcui": candidates[0] if status == "matched" else None,
                "candidates": candidates[:10], "source_url": self.endpoint,
                "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "miss",
            }
        except Exception as error:  # Network issues must degrade to reviewer confirmation.
            result = self._unavailable(medication_name, error)
        if self.cache and result["status"] != "unavailable":
            self.cache.set("rxnorm", query, result)
        return result

    @staticmethod
    def _unavailable(medication_name: str, error: Exception) -> dict[str, Any]:
        return {
            "tool": "rxnorm", "status": "unavailable", "query": medication_name,
            "rxcui": None, "candidates": [], "source_url": RxNormTool.endpoint,
            "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "none",
            "error_code": type(error).__name__,
        }
