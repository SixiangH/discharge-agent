from pathlib import Path

from app.tools.external.cache import ExternalEvidenceCache
from app.tools.external.dailymed_tool import DailyMedLabelTool
from app.tools.external.medication_evidence_tool import PublicMedicationEvidenceTool
from app.tools.external.openfda_tool import OpenFdaDrugLabelTool
from app.tools.external.pubmed_tool import PubMedEvidenceTool
from app.tools.external.rxnorm_tool import RxNormTool


def fake_drug_fetcher(url: str, params: dict[str, str]) -> dict:
    if "rxnav" in url:
        return {"idGroup": {"rxnormId": ["17767"]}}
    if "dailymed" in url:
        assert params["rxcui"] == "17767"
        return {"data": [{"setid": "set-1", "title": "AMLODIPINE TABLET", "spl_version": "4", "published_date": "2026-01-01"}]}
    if "fda.gov" in url:
        return {"results": [{"id": "fda-label-1", "effective_time": "20260101", "warnings": ["Synthetic label warning."]}]}
    raise AssertionError(f"Unexpected URL: {url}")


def test_public_medication_evidence_chain_uses_only_terminology_and_label_queries(tmp_path: Path):
    cache = ExternalEvidenceCache(tmp_path / "cache.db")
    tool = PublicMedicationEvidenceTool(
        cache_path=tmp_path / "unused.db",
        rxnorm=RxNormTool(cache, fake_drug_fetcher),
        dailymed=DailyMedLabelTool(cache, fake_drug_fetcher),
        openfda=OpenFdaDrugLabelTool(cache, fake_drug_fetcher),
    )
    result = tool.enrich([{"name": "Amlodipine", "dosage": "5 mg", "frequency": "once daily"}])
    assert result["medications"][0]["rxnorm_cui"] == "17767"
    evidence = result["external_drug_evidence"][0]
    assert evidence["rxnorm"]["status"] == "matched"
    assert evidence["dailymed"]["labels"][0]["setid"] == "set-1"
    assert evidence["openfda"]["evidence_excerpts"]["warnings"] == "Synthetic label warning."
    assert result["external_evidence_findings"] == []


def test_rxnorm_ambiguity_never_assigns_a_concept(tmp_path: Path):
    tool = RxNormTool(ExternalEvidenceCache(tmp_path / "cache.db"), lambda _url, _params: {"idGroup": {"rxnormId": ["1", "2"]}})
    result = tool.lookup("Ambiguous Synthetic Name")
    assert result["status"] == "ambiguous"
    assert result["rxcui"] is None


def test_pubmed_returns_curation_candidates_not_runtime_evidence(tmp_path: Path):
    def pubmed_fetcher(url: str, _params: dict[str, str]) -> dict:
        if "esearch" in url:
            return {"esearchresult": {"idlist": ["123"]}}
        return {"result": {"123": {"title": "Synthetic review", "source": "Synthetic Journal", "pubdate": "2026", "authors": [{"name": "Author One"}]}}}

    result = PubMedEvidenceTool(ExternalEvidenceCache(tmp_path / "cache.db"), pubmed_fetcher).search_for_curation("discharge planning")
    assert result["curation_required"] is True
    assert result["articles"][0]["pmid"] == "123"
