# Requirement: D-1, D-2, D-3, QUA-1
"""HTTP 표면: 기본은 규칙 발췌 초안(decisions/306), 스포크를 바꿔 꽂아도 초안 형태로 응답."""

from fastapi.testclient import TestClient

from hub.app.dtos import CallSummaryDraft, FollowUpAction
from hub.app.ports.output import PostcallPort
from hub.dependencies.postcall_provider import get_postcall_port
from main import app

BODY = {"call_id": "c_001", "segments": [
    {"segment_id": 1, "speaker": "customer", "text": "카드를 잃어버렸어요", "is_final": True},
    {"segment_id": 2, "speaker": "agent", "text": "분실 신고 도와드리겠습니다", "is_final": True}]}


class _Stub(PostcallPort):
    async def summarize(self, call_id, segments):
        return CallSummaryDraft(call_id=call_id, summary_text="카드 분실 신고 접수",
                                inquiry_type="사고 및 보상 문의",
                                follow_up_actions=(FollowUpAction(action_text="재발급 안내 문자 발송"),),
                                confirmed=True)  # 모델이 확정을 주장해도 서버가 무시한다


def test_기본은_규칙_발췌_초안이다():
    """501 이 아니다 — 자막에서 고른 문장과 발화 건수가 나가고, 유형은 만들지 않는다(decisions/306)."""
    with TestClient(app) as client:
        r = client.post("/hub/calls/c_001/close", json=BODY)
    b = r.json()
    assert r.status_code == 200
    assert b["summary_text"].startswith("고객 문의: 카드를 잃어버렸어요 / 상담원 안내: 분실 신고 도와드리겠습니다")
    assert b["inquiry_type"] is None
    assert b["follow_up_actions"] == []  # 통화 안에서 끝나는 약속은 후속조치가 아니다
    assert b["confirmed"] == "false"


def test_초안을_계약_형태로_돌려준다():
    app.dependency_overrides[get_postcall_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/calls/c_001/close", json=BODY)
        b = r.json()
        assert r.status_code == 200
        assert b["summary_text"] == "카드 분실 신고 접수"
        assert b["inquiry_type"] == "사고 및 보상 문의"
        assert b["follow_up_actions"][0]["action_text"] == "재발급 안내 문자 발송"
    finally:
        app.dependency_overrides.clear()


def test_confirmed는_항상_false로_나간다():
    """서버가 확정하는 경로가 없다 — 확정은 상담원 몫이다 (부록 A-1)."""
    app.dependency_overrides[get_postcall_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/calls/c_001/close", json=BODY)
        assert r.json()["confirmed"] == "false"
    finally:
        app.dependency_overrides.clear()


def test_경로와_본문의_call_id가_다르면_422다():
    app.dependency_overrides[get_postcall_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/calls/c_999/close", json=BODY)
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_전사가_비면_422다():
    app.dependency_overrides[get_postcall_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/calls/c_001/close", json={"call_id": "c_001", "segments": []})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()
