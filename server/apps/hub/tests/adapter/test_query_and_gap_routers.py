# Requirement: A-1, D-4, SEC-1, QUA-1
"""HTTP 표면: PostgreSQL 미설정이면 501, 설정되면 계약 형태로 응답."""

from fastapi.testclient import TestClient

from hub.app.dtos import MaskedSpan, TranscriptEvent
from hub.app.ports.output import KnowledgeGapPort, TranscriptQueryPort
from hub.dependencies.knowledge_gap_provider import get_knowledge_gap_port
from hub.dependencies.transcript_query_provider import get_transcript_query_port
from main import app


class _Query(TranscriptQueryPort):
    async def list_segments(self, call_id, limit, offset):
        return [TranscriptEvent(call_id=call_id, segment_id=1, speaker="customer",
                                text="번호는 ***********", is_final=True,
                                masked=(MaskedSpan(type="P4", span=(4, 15)),))]

    async def count_segments(self, call_id):
        return 1


class _Gap(KnowledgeGapPort):
    async def save(self, report):
        return 77


def test_전사조회_PostgreSQL_미설정이면_501이다():
    """빈 목록을 주면 '발화가 없는 통화'로 읽혀 DB 미설정과 구분되지 않는다."""
    with TestClient(app) as client:
        r = client.get("/hub/calls/c_001/transcript")
    assert r.status_code == 501


def test_전사조회가_마스킹_구간까지_돌려준다():
    app.dependency_overrides[get_transcript_query_port] = lambda: _Query()
    try:
        with TestClient(app) as client:
            r = client.get("/hub/calls/c_001/transcript?limit=10&offset=0")
        b = r.json()
        assert r.status_code == 200
        assert b["total"] == "1" and b["limit"] == "10"
        assert b["segments"][0]["masked"][0]["type"] == "P4"
        assert b["segments"][0]["masked"][0]["span"] == ["4", "15"]
    finally:
        app.dependency_overrides.clear()


def test_전사조회_limit_범위를_벗어나면_422다():
    app.dependency_overrides[get_transcript_query_port] = lambda: _Query()
    try:
        with TestClient(app) as client:
            r = client.get("/hub/calls/c_001/transcript?limit=99999")
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_공백신고_PostgreSQL_미설정이면_501이다():
    """접수했다고 응답한 뒤 아무 데도 안 남으면 D-4 목적과 정반대다."""
    with TestClient(app) as client:
        r = client.post("/hub/knowledge-gaps", json={"module": "B", "description": "못 찾음"})
    assert r.status_code == 501


def test_공백신고가_접수되면_201과_id를_준다():
    app.dependency_overrides[get_knowledge_gap_port] = lambda: _Gap()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/knowledge-gaps",
                            json={"module": "B", "description": "반품 배송비를 못 찾음", "call_id": "c_001"})
        assert r.status_code == 201
        assert r.json() == {"gap_id": "77", "module": "B"}
    finally:
        app.dependency_overrides.clear()


def test_공백신고_모듈은_B_C_F만_받는다():
    app.dependency_overrides[get_knowledge_gap_port] = lambda: _Gap()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/knowledge-gaps", json={"module": "X", "description": "못 찾음"})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


# ── 카드 피드백 (E-1) ─────────────────────────────────────────────────────────

from hub.app.ports.output import CardFeedbackPort  # noqa: E402
from hub.dependencies.card_feedback_provider import get_card_feedback_port  # noqa: E402


class _Feedback(CardFeedbackPort):
    async def append(self, feedback):
        return 501234


def test_카드피드백_PostgreSQL_미설정이면_501이다():
    with TestClient(app) as client:
        r = client.post("/hub/cards/42/feedback", json={"action": "adopted"})
    assert r.status_code == 501


def test_카드피드백이_접수되면_201이다():
    app.dependency_overrides[get_card_feedback_port] = lambda: _Feedback()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/cards/42/feedback", json={"action": "adopted"})
        assert r.status_code == 201
        assert r.json() == {"feedback_id": 501234, "card_id": 42, "action": "adopted"}
    finally:
        app.dependency_overrides.clear()


def test_카드피드백_요청에_상담원_필드를_넣어도_무시된다():
    """부록 A-1 — 스키마에 agent_id 가 없어 상담원 단위 집계를 만들 수 없다."""
    app.dependency_overrides[get_card_feedback_port] = lambda: _Feedback()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/cards/42/feedback", json={"action": "adopted", "agent_id": "a_01"})
        assert r.status_code == 201
        assert "agent_id" not in r.json()
    finally:
        app.dependency_overrides.clear()


def test_카드피드백_action은_두_값만_받는다():
    app.dependency_overrides[get_card_feedback_port] = lambda: _Feedback()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/cards/42/feedback", json={"action": "maybe"})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()
