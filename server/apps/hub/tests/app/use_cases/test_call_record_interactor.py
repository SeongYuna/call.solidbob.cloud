# Requirement: B-5, D-1, F-2, QUA-1
"""스텁 포트로: 없는 통화는 CallRecordNotFound · 빈 call_id 는 거부 · 기록은 그대로 돌려준다."""

import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.call_record_dto import CallRecord, CallRecordNotFound
from hub.app.ports.output.call_record_port import CallRecordPort
from hub.app.use_cases.call_record_interactor import CallRecordInteractor

RECORD = CallRecord(call_id="c1", status="in_progress", started_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
                    ended_at=None, summary_text=None, inquiry_type=None, summary_confirmed_at=None)


class _Port(CallRecordPort):
    def __init__(self, record):
        self.record, self.calls = record, []

    async def get(self, call_id):
        self.calls.append(call_id)
        return self.record


def test_기록을_그대로_돌려준다():
    assert asyncio.run(CallRecordInteractor(_Port(RECORD)).get("c1")) is RECORD


def test_없는_통화는_CallRecordNotFound():
    with pytest.raises(CallRecordNotFound):
        asyncio.run(CallRecordInteractor(_Port(None)).get("nope"))


def test_빈_call_id는_조회하지_않고_거부한다():
    port = _Port(RECORD)
    with pytest.raises(ValueError):
        asyncio.run(CallRecordInteractor(port).get("  "))
    assert port.calls == []
