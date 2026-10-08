"""Read-only openFDA label evidence lookup; no clinical interpretation."""

import re
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError

from app.tools.external.cache import ExternalEvidenceCache
from app.tools.external.http_client import JsonFetcher, fetch_json


class OpenFdaDrugLabelTool:
    endpoint = "https://api.fda.gov/drug/label.json"
    allowed_name = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 -]{0,99}$")
    evidence_fields = ("boxed_warning", "warnings", "contraindications", "drug_interactions", "patient_medication_information")

    def __init__(self, cache: ExternalEvidenceCache | None = None, fetcher: JsonFetcher = fetch_json) -> None:
        self.cache = cache
        self.fetcher = fetcher

    def lookup(self, normalized_medication_name: str) -> dict[str, Any]:
        if not self.allowed_name.fullmatch(normalized_medication_name):
            return {"tool": "openfda", "status": "invalid_query", "query": normalized_medication_name, "labels": [], "source_url": self.endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "none"}
        # The label API indexes generic names such as "AMLODIPINE BESYLATE";
        # a non-exact field query correctly discovers these product labels.
        query = {"search": f"openfda.generic_name:{normalized_medication_name.upper()}", "limit": "1"}
        cached = self.cache.get("openfda", query) if self.cache else None
        if cached is not None:
            return {**cached, "cache_status": "hit"}
        try:
            response = self.fetcher(self.endpoint, query)
            record = (response.get("results") or [{}])[0]
            excerpts = {field: record[field][0][:1000] for field in self.evidence_fields if record.get(field)}
            result = {
                "tool": "openfda", "status": "matched" if record else "not_found", "query": normalized_medication_name,
                "label_id": record.get("id"), "effective_time": record.get("effective_time"), "evidence_excerpts": excerpts,
                "source_url": self.endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "miss",
            }
        except HTTPError as error:
            if error.code == 404:
                result = {"tool": "openfda", "status": "not_found", "query": normalized_medication_name, "label_id": None, "effective_time": None, "evidence_excerpts": {}, "source_url": self.endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "miss"}
            else:
                result = {"tool": "openfda", "status": "unavailable", "query": normalized_medication_name, "labels": [], "source_url": self.endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "none", "error_code": f"HTTP_{error.code}"}
        except Exception as error:
            result = {"tool": "openfda", "status": "unavailable", "query": normalized_medication_name, "labels": [], "source_url": self.endpoint, "retrieved_at": datetime.now(timezone.utc).isoformat(), "cache_status": "none", "error_code": type(error).__name__}
        if self.cache and result["status"] != "unavailable":
            self.cache.set("openfda", query, result)
        return result
