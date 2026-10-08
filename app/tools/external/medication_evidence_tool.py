"""Orchestrates public drug terminology and label lookups for reviewers."""

import os
from pathlib import Path
from typing import Any

from app.tools.external.cache import ExternalEvidenceCache
from app.tools.external.dailymed_tool import DailyMedLabelTool
from app.tools.external.openfda_tool import OpenFdaDrugLabelTool
from app.tools.external.rxnorm_tool import RxNormTool


class PublicMedicationEvidenceTool:
    """Public, read-only lookups using only medication names/RxCUIs.

    Enable only for synthetic or suitably governed data.  This tool deliberately
    does not send patient identifiers, notes, diagnoses, allergies, or doses to
    an external service.
    """

    def __init__(self, cache_path: str | Path | None = None, *, rxnorm: RxNormTool | None = None, dailymed: DailyMedLabelTool | None = None, openfda: OpenFdaDrugLabelTool | None = None) -> None:
        cache = ExternalEvidenceCache(cache_path or os.getenv("EXTERNAL_EVIDENCE_CACHE_PATH", "app/data/external_evidence_cache.db"))
        self.rxnorm = rxnorm or RxNormTool(cache)
        self.dailymed = dailymed or DailyMedLabelTool(cache)
        self.openfda = openfda or OpenFdaDrugLabelTool(cache)

    def enrich(self, medications: list[dict[str, Any]]) -> dict[str, Any]:
        enriched = [dict(medication) for medication in medications]
        evidence: list[dict[str, Any]] = []
        findings: list[dict[str, Any]] = []
        for index, medication in enumerate(enriched):
            name = medication.get("name", "")
            rxnorm_result = self.rxnorm.lookup(name)
            entry: dict[str, Any] = {"medication_name": name, "rxnorm": rxnorm_result}
            if rxnorm_result["status"] == "matched":
                medication["rxnorm_cui"] = rxnorm_result["rxcui"]
                entry["dailymed"] = self.dailymed.lookup_by_rxcui(rxnorm_result["rxcui"])
                entry["openfda"] = self.openfda.lookup(name)
            else:
                findings.append(self._finding(index, name, rxnorm_result["status"]))
            evidence.append(entry)
        return {
            "medications": enriched,
            "external_drug_evidence": evidence,
            "external_evidence_findings": findings,
        }

    @staticmethod
    def _finding(index: int, name: str, status: str) -> dict[str, Any]:
        message = {
            "ambiguous": "Multiple public RxNorm candidates were returned; a reviewer must select a terminology match.",
            "not_found": "No public RxNorm match was returned; confirm the reconciled medication name before relying on external label evidence.",
            "unavailable": "The public terminology service was unavailable; confirm the medication identity manually.",
        }.get(status, "The public terminology query was not valid; confirm the medication identity manually.")
        return {
            "code": "external_terminology_confirmation_required", "severity": "warning", "message": f"Medication '{name}': {message}",
            "affected_field": f"medication_list[{index}].name", "required_action": "review", "evidence": [],
        }
