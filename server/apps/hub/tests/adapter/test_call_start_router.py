# Requirement: 7.3절 전사 이벤트, QUA-1
"""HTTP 표면: 기본값 채움 · 멱등 응답 · 검증 실패 422."""

from fastapi.testclient import TestClient

from hub.app.dtos.call_start_dto import CallStarted
from hub.app.ports.output.call_start_record_port import CallStartRecordPort
from hub.dependencies.call_record_provider import get_call_record_port
from hub.tests.adapter._ingest_auth import HEADERS as INGEST_HEADERS
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
        with TestClient(app, headers=INGEST_HEADERS) as client:
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
    with TestClient(app, headers=INGEST_HEADERS) as client:
        r = client.post("/hub/calls", json={"call_id": "test-c002"})
    assert r.status_code == 200 and r.json()["created"] == "true"


# 응답에 실리는 필드 전부. 여기 없는 이름이 생기면 「번호를 담을 자리」가 하나 늘어난 것이라
# 이 테스트가 먼저 깨진다 — 늘릴 때 SEC-1 을 한 번 더 보라는 뜻이다.
_RESPONSE_FIELDS = {
    "call_id", "domain", "stt_engine", "channel_count",
    "started_at", "status", "created", "customer_linked",
}


def test_발신_번호는_식별자로만_남고_응답에_번호도_식별자도_없다(monkeypatch):
    """SEC-1 · `decisions/304` — 평문 번호도, 그것으로 만든 식별자도 응답에 싣지 않는다.

    ⚠ **`started_at` 을 고정해서 부른다.** 서버가 시각을 채우게 두면 마이크로초가 매번 달라지고,
    번호 조각을 `r.text` 에서 찾는 검사가 **타임스탬프와 우연히 겹쳐** 깨진다 —
    2026-09-15 CI 에서 실제로 났다(`...01:16:44.412342Z` 의 `412342` 안에 `1234` 가 있다).
    """
    monkeypatch.setenv("CUSTOMER_REF_HMAC_KEY", "test-key")
    record = _SpyRecord()
    r = _post(
        {"call_id": "test-c7", "caller_phone": "010-1234-5678",
         "started_at": "2026-09-15T00:00:00Z"},
        record,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["customer_linked"] == "true"

    # ① 담을 자리가 늘지 않았는가
    assert set(body) == _RESPONSE_FIELDS

    # ② 번호가 **어떤 표기로도** 새지 않는가. 네 자리 조각(`1234`)이 아니라 번호 전체를 본다 —
    #    조각 검사는 «번호가 샜다» 말고 **타임스탬프 같은 무관한 숫자에도 걸린다.**
    #    탐지력이 약해서가 아니라 **거짓 양성** 때문에 바꿨다(조각 검사도 유출 자체는 잡았다).
    customer_id = record.calls[0].customer_id
    for leaked in ("010-1234-5678", "01012345678", "+821012345678", customer_id):
        assert leaked not in r.text

    # ③ 저장 쪽에는 식별자만 남는다
    assert len(customer_id) == 64 and customer_id != "010-1234-5678"


def test_HMAC_키가_없으면_통화는_열리고_고객만_잇지_않는다():
    record = _SpyRecord()
    r = _post({"call_id": "test-c8", "caller_phone": "01012345678"}, record)
    assert r.status_code == 200 and r.json()["customer_linked"] == "false"
    assert record.calls[0].customer_id is None


def test_번호_형식이_아니면_422이고_입력을_되돌려_주지_않는다(monkeypatch):
    monkeypatch.setenv("CUSTOMER_REF_HMAC_KEY", "test-key")
    r = _post({"call_id": "test-c9", "caller_phone": "12-34"}, _SpyRecord())
    assert r.status_code == 422 and "12-34" not in r.text
