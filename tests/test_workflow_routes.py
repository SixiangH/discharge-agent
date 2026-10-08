from app.graph.workflow import route_after_review, route_after_safety_check, route_after_validation


def test_invalid_case_is_escalated():
    assert route_after_validation({"validation_status": "invalid"}) == "escalate"


def test_high_risk_case_cannot_reach_review_or_finalization():
    assert route_after_safety_check({"risk_level": "high"}) == "escalate"


def test_review_routes_require_an_explicit_decision():
    assert route_after_review({}) == "escalate"
    assert route_after_review({"reviewer_decision": "approve"}) == "finalize"
