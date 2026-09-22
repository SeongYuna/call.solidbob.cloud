# Requirement: C-1, C-2, C-3, C-4, QUA-1
"""HTTP 표면: 스포크가 없으면 501 (빈 목록으로 '깨끗함' 만들지 않음)."""

from fastapi.testclient import TestClient

from hub.app.dtos import ComplianceFinding, Source
from hub.app.ports.output import CompliancePort
from hub.dependencies.compliance_provider import get_compliance_port
from hub.tests.adapter._ingest_auth import HEADERS as INGEST_HEADERS
from main import app

BODY = {"call_id": "c_001", "segment_id": 7, "agent_utterance": "무조건 보장됩니다"}


class _Stub(CompliancePort):
    async def detect(self, agent_utterance):
        return [ComplianceFinding(rule_code="C-1", phrase="무조건 보장됩니다",
                                  alternative_source=Source(doc_id="FIN-MANUAL-1.4", title="응대 매뉴얼 1.4"))]


class _Clean(CompliancePort):
    async def detect(self, agent_utterance):
        return []


def test_스포크가_없으면_501이다(monkeypatch):
    """빈 목록으로 200 을 주면 '탐지가 죽은 것'이 '위반 없음'으로 읽힌다.

    2026-09-15 부터 합성 루트가 `ai/` 규칙 스포크를 꽂는다(`_wire_compliance`) — 콜 가드 테스트와 같이
    배선을 꺼서 「스포크가 없는 배포」를 재현한다.
    """
    import main

    monkeypatch.setattr(main, "_wire_compliance", lambda app: None)
    app.dependency_overrides.pop(get_compliance_port, None)
    with TestClient(app, headers=INGEST_HEADERS) as client:
        r = client.post("/hub/compliance-checks", json=BODY)
    assert r.status_code == 501


def test_위반을_계약_형태로_돌려준다():
    app.dependency_overrides[get_compliance_port] = lambda: _Stub()
    try:
        with TestClient(app, headers=INGEST_HEADERS) as client:
            r = client.post("/hub/compliance-checks", json=BODY)
        b = r.json()
        assert r.status_code == 200
        assert b["findings"][0]["rule_code"] == "C-1"
        assert b["findings"][0]["alternative_source"]["doc_id"] == "FIN-MANUAL-1.4"
    finally:
        app.dependency_overrides.clear()


def test_응답에_등급이나_안전_필드가_없다():
    """부록 A-1 — '안전합니다'·'위험도 N%' 를 만들 수 있는 필드를 아예 두지 않는다."""
    app.dependency_overrides[get_compliance_port] = lambda: _Clean()
    try:
        with TestClient(app, headers=INGEST_HEADERS) as client:
            r = client.post("/hub/compliance-checks", json=BODY)
        b = r.json()
        assert b["findings"] == []
        assert set(b) == {"call_id", "segment_id", "findings"}
    finally:
        app.dependency_overrides.clear()


def test_빈_발화는_422다():
    app.dependency_overrides[get_compliance_port] = lambda: _Stub()
    try:
        with TestClient(app, headers=INGEST_HEADERS) as client:
            r = client.post("/hub/compliance-checks", json={**BODY, "agent_utterance": ""})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_없는_전사_구간을_가리키면_404_다():
    """2026-09-20 운영 왕복: 콜 가드는 **500**(FK 위반이 그대로), 컴플라이언스는 **200 + 조용한 저장 실패**였다.

    같은 호출자 실수가 스포크마다 다르게 보였다 — 둘 다 「전사를 먼저 넣어라」는 404 로 맞춘다.
    """
    from hub.dependencies.compliance_provider import get_compliance_check_use_case
    from hub.app.ports.output.transcript_ingest_record_port import SegmentNotFoundError

    class _Missing:
        async def check(self, command):
            raise SegmentNotFoundError(command.call_id, command.segment_id)

    app.dependency_overrides[get_compliance_check_use_case] = lambda: _Missing()
    try:
        with TestClient(app, headers=INGEST_HEADERS) as client:
            r = client.post("/hub/compliance-checks", json=BODY)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 404
    assert "POST /hub/transcripts" in r.json()["detail"]      # 무엇을 먼저 해야 하는지 알려 준다
    assert "c_001#7" in r.json()["detail"]
