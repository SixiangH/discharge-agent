from app.tools.retrieval_tool import RetrievalTool


def test_retrieval_returns_ranked_evidence_metadata():
    evidence = RetrievalTool().retrieve("hypertension amlodipine cardiology")
    assert evidence[0]["evidence_id"] == "hypertension-followup-v1"
    assert evidence[0]["score"] > 0
    assert evidence[0]["version"] == "1.1"
    assert evidence[0]["approval_status"] == "approved"
    assert evidence[0]["source_url"].startswith("https://")
