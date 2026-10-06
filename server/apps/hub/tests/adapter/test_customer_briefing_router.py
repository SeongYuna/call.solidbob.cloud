# Requirement: F-3, QUA-1
"""HTTP 표면: 404 · 값은 전부 문자열 · 고객 식별 정보가 응답 어디에도 없다."""

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from hub.app.dtos.customer_briefing_dto import BriefingFacts, PriorCall
from hub.app.ports.output.briefing_facts_port import BriefingFactsPort
from hub.dependencies.customer_briefing_provider import get_briefing_facts_port, reset_briefing_cache
from main import app

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)
PRIOR = PriorCall(call_id="p1", started_at=T, inquiry_type="일반행정", summary_text="위임 등본 문의", summary_confirmed=True,
                  incomplete_procedures=("DASAN-TERM-4.1",))


class _Facts(BriefingFactsPort):
    def __init__(self, facts):
        self.facts = facts

    async def collect(self, call_id):
        return self.facts


def _get(facts, call_id="now"):
    reset_briefing_cache()
    app.dependency_overrides[get_briefing_facts_port] = lambda: _Facts(facts)
    try:
        return TestClient(app).get(f"/hub/calls/{call_id}/briefing")
    finally:
        app.dependency_overrides.pop(get_briefing_facts_port, None)


def test_unknown_call_404():
    assert _get(None).status_code == 404


def test_ready_shape_is_all_strings():
    r = _get(BriefingFacts("now", True, (PRIOR,), blacklisted=False))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready" and body["prior_call_count"] == "1"
    assert body["purpose"]["category"] == "서류 보완" and body["purpose"]["source"] == "rule"
    assert body["signals"]["blacklisted"] == "false" and body["signals"]["open_follow_ups"] == "0"
    assert body["evidence"][0]["summary_confirmed"] == "true"
    assert body["evidence"][0]["incomplete_procedures"] == ["DASAN-TERM-4.1"]
    assert 1 <= len(body["briefing_lines"]) <= 3


def test_first_contact_has_null_purpose():
    body = _get(BriefingFacts("now", True)).json()
    assert body["status"] == "first_contact" and body["purpose"] is None and body["briefing_lines"] == []


def test_response_has_no_customer_identity():
    text = json.dumps(_get(BriefingFacts("now", True, (PRIOR,))).json(), ensure_ascii=False)
    for key in ("customer_id", "customer_ref", "display_hint", "caller_phone", "hmac"):
        assert key not in text
