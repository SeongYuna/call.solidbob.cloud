# Requirement: 7.3절 전사 이벤트, C-5, SEC-1, QUA-1
"""HTTP 표면: 마스킹 스포크가 없으면 501 (원문 통과 없음), 있으면 계약 형태로 응답."""

from fastapi.testclient import TestClient

from hub.app.dtos import MaskedSpan
from hub.app.ports.output import MaskingPort
from hub.dependencies.masking_provider import get_masking_port
from main import app

BODY = {"call_id": "c_001", "segment_id": 1, "speaker": "customer",
        "text": "제 번호는 01012345678이고 문자로 남겨주세요", "is_final": True, "utterance_end_ms": 2600}


class _StubMasking(MaskingPort):
    def mask(self, text: str):
        idx = text.find("01012345678")
        return text[:idx] + "*" * 11 + text[idx + 11:], (MaskedSpan(type="P4", span=(idx, idx + 11)),)


def test_기본_마스킹_구현이_원문을_흘려보내지_않는다():
    """2026-08-27 masking 스포크(P1~P5)가 붙어 더는 501 이 아니다.
    501 이었던 이유는 임시 통과 경로를 만들지 않기 위해서였고, 그 목적은 그대로 지켜진다 —
    실제 구현이 원문을 가린다."""
    with TestClient(app) as client:
        r = client.post("/hub/transcripts", json=BODY)
    assert r.status_code == 200
    assert "01012345678" not in r.text  # SEC-1 — 원문이 응답에 없다
    assert r.json()["masked"][0]["type"] == "P4"


def test_returns_masked_contract_when_masking_registered():
    app.dependency_overrides[get_masking_port] = lambda: _StubMasking()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/transcripts", json=BODY)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert "01012345678" not in body["text"]
    assert body["masked"] == [{"type": "P4", "span": ["6", "17"]}]
    assert body["segment_id"] == "1" and body["utterance_end_ms"] == "2600"  # 응답은 전부 문자열 (2026-09-10)


def test_통화_시작_전_전사는_409로_순서를_알려준다():
    """decisions/301 — 전에는 외래키 위반이 500 으로 나가 "서버 코드가 틀렸다"로 읽혔다(2026-09-11).
    호출 순서 문제이므로 409 + 무엇을 먼저 보내야 하는지를 준다. 원문은 오류 본문에도 없어야 한다(SEC-1)."""
    from hub.app.ports.output import CallNotStartedError, TranscriptIngestRecordPort
    from hub.dependencies.transcript_record_provider import get_transcript_record_port

    class _NoCall(TranscriptIngestRecordPort):
        async def record(self, event):
            raise CallNotStartedError(event.call_id)

    app.dependency_overrides[get_transcript_record_port] = lambda: _NoCall()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/transcripts", json=BODY)
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 409
    assert "POST /hub/calls" in r.json()["detail"]
    assert "01012345678" not in r.text


def test_myself_is_served():
    with TestClient(app) as client:
        body = client.get("/hub/myself").json()
    assert body["name"] == "허브 (hub)" and body["does_not"]
