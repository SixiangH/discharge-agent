"""DailyMed SPL lookup using a previously confirmed RxCUI."""

from datetime import datetime, timezone
from typing import Any

from app.tools.external.cache import ExternalEvidenceCache
from app.tools.external.http_client import JsonFetcher, fetch_json


class DailyMedLabelTool:
    endpoint = "https://dailymed.nlm.nih.gov/dailymed/services/v2/spls.json"
    label_page = "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid="

    def __init__(self, cache: ExternalEvidenceCache | None = None, fetcher: JsonFetcher = fetch_json) -> None:
        self.cache = cache
        self.fetcher = fetcher

    def lookup_by_rxcui(self, rxcui: str) -> dict[str, Any]:
        query = {"rxcui": rxcui, "pagesize": "3", "page": "1"}
        cached = self.cache.get("dailymed", query) if self.cache else None
        if cached is not None:
            return {**cached, "cache_status": "hit"}
        try:
            response = self.fetcher(self.endpoint, query)
            labels = [
                {
                    "setid": item.get("setid"), "title": item.get("title"),
                    "spl_version": item.get("spl_version"), "published_date": item.get("published_date"),
                    "label_url": f"{self.label_page}{item['setid']}" if item.get("setid") else None,
                }
                for item in response.get("data", [])[:3]
            ]
            result = {
                "tool": "dailymed", "status": "matched" if labels else "not_found", "rxcui": rxcui,
                "labels": labels, "source_url": self.endpoint,
                "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "miss",
            }
        except Exception as error:
            result = {"tool": "dailymed", "status": "unavailable", "rxcui": rxcui, "labels": [], "source_url": self.endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "none", "error_code": type(error).__name__}
        if self.cache and result["status"] != "unavailable":
            self.cache.set("dailymed", query, result)
        return result
