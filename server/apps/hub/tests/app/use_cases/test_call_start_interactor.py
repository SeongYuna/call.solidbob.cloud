# Requirement: 7.3절 전사 이벤트, QUA-1
"""스텁 기록 포트로 인터랙터만 검증 — 시각 채움·멱등 결과 전달."""

import asyncio
from datetime import datetime, timezone

from hub.app.dtos.call_start_dto import CallStartCommand, CallStarted
from hub.app.ports.output.call_start_record_port import CallStartRecordPort
from hub.app.use_cases.call_start_interactor import CallStartInteractor


class _SpyRecord(CallStartRecordPort):
    def __init__(self, created: bool = True):
        self.calls: list[CallStarted] = []
        self._created = created

    async def record(self, call: CallStarted) -> bool:
        self.calls.append(call)
        return self._created


def _cmd(**over) -> CallStartCommand:
    base = dict(call_id="test-c001", domain="dasan", stt_engine="mock", channel_count=1)
    return CallStartCommand(**{**base, **over})


def test_시작_시각이_없으면_지금_시각을_넣는다():
    record = _SpyRecord()
    before = datetime.now(timezone.utc)
    call = asyncio.run(CallStartInteractor(record).start(_cmd()))
    assert before <= call.started_at <= datetime.now(timezone.utc)
    assert call.started_at.tzinfo is not None
    assert call.status == "in_progress" and call.created is True
    assert record.calls == [call]


def test_시작_시각을_주면_그대로_쓴다():
    given = datetime(2026, 9, 10, 3, 0, tzinfo=timezone.utc)
    call = asyncio.run(CallStartInteractor(_SpyRecord()).start(_cmd(started_at=given)))
    assert call.started_at == given


def test_이미_있던_통화면_created가_False다():
    call = asyncio.run(CallStartInteractor(_SpyRecord(created=False)).start(_cmd()))
    assert call.created is False and call.call_id == "test-c001"


class _Ref:
    def __init__(self, value="r" * 64):
        self.value = value
        self.phones = []

    def ref(self, phone):
        self.phones.append(phone)
        return self.value


def test_발신_번호를_식별자로_바꿔_싣고_번호는_싣지_않는다():
    record, ref = _SpyRecord(), _Ref()
    call = asyncio.run(CallStartInteractor(record, customer_ref=ref).start(_cmd(caller_phone="010-1234-5678")))
    assert ref.phones == ["010-1234-5678"]
    assert call.customer_id == "r" * 64
    assert "010" not in repr(record.calls[0])


def test_번호가_없거나_키가_없으면_고객을_잇지_않는다():
    assert asyncio.run(CallStartInteractor(_SpyRecord(), customer_ref=_Ref()).start(_cmd())).customer_id is None
    no_key = _Ref(value=None)
    assert asyncio.run(CallStartInteractor(_SpyRecord(), customer_ref=no_key).start(
        _cmd(caller_phone="01012345678"))).customer_id is None
