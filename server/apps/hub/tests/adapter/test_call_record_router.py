# Requirement: B-5, D-1, F-2, QUA-1
"""HTTP 표면: DB 없으면 501 · 없는 통화 404 · 값은 전부 문자열(null 은 그대로)."""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from hub.app.dtos.call_record_dto import (
    CallRecord,
    SavedCard,
    SavedClosure,
    SavedClosureItem,
    SavedFollowUp,
    SavedRecommendation,
)
from hub.app.ports.output.call_record_port import CallRecordPort
from hub.dependencies.call_record_query_provider import get_call_record_query_port
from main import app

T = datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc)
RECORD = CallRecord(
    call_id="c1", status="in_progress", started_at=T, ended_at=None,
    summary_text="고객 문의: 초본 서류 / 발화 고객 1건 · 상담원 1건 (규칙 발췌 초안)", inquiry_type=None, summary_confirmed_at=None,
    follow_up_actions=(SavedFollowUp(action_text="문자로 보내 드리겠습니다", status="draft"),),
    recommendations=(
        SavedRecommendation(recommendation_id=5, trigger_at_ms=3150, internal_latency_ms=12, created_at=T, cards=(
            SavedCard(card_id=9, rank=1, title="주민등록초본", summary="신분증", source_doc_id=None, similarity_score=7.8),)),
        SavedRecommendation(recommendation_id=6, trigger_at_ms=5000, internal_latency_ms=None, created_at=T),
    ),
    closures=(SavedClosure(closure_id=3, procedure="DASAN-TERM-4.3", verdict="incomplete", detected=True, reason=None,
                           source_doc_id="DASAN-TERM-4.3", decided_at=T,
                           items=(SavedClosureItem(rank=1, document_name="신분증", informed=False),)),),
)


class _Port(CallRecordPort):
    def __init__(self, record):
        self.record = record

    async def get(self, call_id):
        return self.record


def _get(record):
    app.dependency_overrides[get_call_record_query_port] = lambda: _Port(record)
    try:
        with TestClient(app) as client:
            return client.get("/hub/calls/c1/record")
    finally:
        app.dependency_overrides.clear()


def _leaves(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from _leaves(v)
    elif isinstance(value, list):
        for v in value:
            yield from _leaves(v)
    else:
        yield value


def test_PostgreSQL_미설정이면_501이다():
    with TestClient(app) as client:
        assert client.get("/hub/calls/c1/record").status_code == 501


def test_없는_통화는_404다():
    assert _get(None).status_code == 404


def test_요약_추천_판정을_문자열로_돌려준다():
    r = _get(RECORD)
    assert r.status_code == 200
    b = r.json()
    assert b["summary_confirmed"] == "false" and b["inquiry_type"] is None
    assert b["follow_up_actions"] == [{"action_text": "문자로 보내 드리겠습니다", "status": "draft"}]
    first, empty = b["recommendations"]
    assert first["cards"][0] == {"card_id": "9", "rank": "1", "title": "주민등록초본", "summary": "신분증",
                                 "source_doc_id": None, "similarity_score": "7.8"}
    assert empty["cards"] == [] and empty["internal_latency_ms"] is None  # 관련 문서 없음(B-6)
    closure = b["closures"][0]
    assert closure["verdict"] == "incomplete" and closure["detected"] == "true"
    assert closure["items"] == [{"rank": "1", "document_name": "신분증", "informed": "false"}]
    assert all(v is None or isinstance(v, str) for v in _leaves(b)), b
