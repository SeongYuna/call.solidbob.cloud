# Requirement: 7.3절 전사 이벤트, QUA-1
"""HTTP 표면: 기본값 채움 · 멱등 응답 · 검증 실패 422."""

from fastapi.testclient import TestClient

from hub.app.dtos.call_start_dto import CallStarted
from hub.app.ports.output.call_start_record_port import CallStartRecordPort
from hub.dependencies.call_record_provider import get_call_record_port
from main import app


class _SpyRecord(CallStartRecordPort):
    def __init__(self, created: bool = True):
        self.calls: list[CallStarted] = []
        self._created = created

    async def record(self, call: CallStarted) -> bool:
        self.calls.append(call)
        return self._created


def _post(body: dict, record: CallStartRecordPort):
    app.dependency_overrides[get_call_record_port] = lambda: record
    try:
        with TestClient(app) as client:
            return client.post("/hub/calls", json=body)
    finally:
        app.dependency_overrides.clear()


def test_call_id만_보내도_다산_기본값으로_만든다():
    record = _SpyRecord()
    r = _post({"call_id": "test-c001"}, record)
    assert r.status_code == 200
    body = r.json()
    assert body["call_id"] == "test-c001" and body["domain"] == "dasan"
    assert body["stt_engine"] == "google-stt" and body["channel_count"] == "1"
    assert body["status"] == "in_progress" and body["created"] == "true"
    assert body["started_at"]  # 서버가 채운다
    assert record.calls[0].call_id == "test-c001"


def test_같은_통화를_다시_알리면_created가_False다():
    r = _post({"call_id": "test-c001", "stt_engine": "mock"}, _SpyRecord(created=False))
    assert r.status_code == 200 and r.json()["created"] == "false"


def test_DDL에_없는_domain은_422다():
    r = _post({"call_id": "test-c001", "domain": "telecom"}, _SpyRecord())
    assert r.status_code == 422


def test_DB가_없으면_로그_어댑터로_떨어져도_200이다(monkeypatch):
    """전사 기록과 같은 조건이다 — 둘 다 로그로 가야 짝이 맞는다."""
    for k in ("DATABASE_URL", "POSTGRES_HOST", "POSTGRES_DB_NAME", "POSTGRES_USER", "POSTGRES_PASSWORD"):
        monkeypatch.delenv(k, raising=False)
    with TestClient(app) as client:
        r = client.post("/hub/calls", json={"call_id": "test-c002"})
    assert r.status_code == 200 and r.json()["created"] == "true"


def test_발신_번호는_식별자로만_남고_응답에_번호도_식별자도_없다(monkeypatch):
    monkeypatch.setenv("CUSTOMER_REF_HMAC_KEY", "test-key")
    record = _SpyRecord()
    r = _post({"call_id": "test-c7", "caller_phone": "010-1234-5678"}, record)
    assert r.status_code == 200
    assert r.json()["customer_linked"] == "true"
    assert "1234" not in r.text and record.calls[0].customer_id not in r.text
    assert len(record.calls[0].customer_id) == 64


def test_HMAC_키가_없으면_통화는_열리고_고객만_잇지_않는다():
    record = _SpyRecord()
    r = _post({"call_id": "test-c8", "caller_phone": "01012345678"}, record)
    assert r.status_code == 200 and r.json()["customer_linked"] == "false"
    assert record.calls[0].customer_id is None


def test_번호_형식이_아니면_422이고_입력을_되돌려_주지_않는다(monkeypatch):
    monkeypatch.setenv("CUSTOMER_REF_HMAC_KEY", "test-key")
    r = _post({"call_id": "test-c9", "caller_phone": "12-34"}, _SpyRecord())
    assert r.status_code == 422 and "12-34" not in r.text
