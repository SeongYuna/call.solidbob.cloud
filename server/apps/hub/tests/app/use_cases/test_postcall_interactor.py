# Requirement: D-1, D-2, D-3, SEC-1, QUA-1
"""스텁 포트로 배선만 검증. 요약 품질·환각은 postcall 스포크가 골든셋으로 채점받는다. 저장은 기록 포트로 — 돌려준 초안과 같은 것이 남는다."""

import asyncio

import pytest

from hub.app.dtos import CallSummaryDraft, FollowUpAction, MaskedSpan
from hub.app.dtos.postcall_dto import PostcallCommand, PostcallSegment
from hub.app.ports.output import PostcallPort, PostcallRecordPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.use_cases.postcall_interactor import PostcallInteractor

SEGMENTS = (
    PostcallSegment(segment_id=1, speaker="customer", raw_text="카드를 잃어버렸어요", is_final=True),
    PostcallSegment(segment_id=2, speaker="agent", raw_text="분실 신고 도와드리겠습니다", is_final=True),
)


class _DigitMasking(MaskingPort):
    """숫자를 같은 길이의 `*` 로 — 배선만 본다(무엇을 가릴지는 masking 스포크가 채점받는다)."""

    def mask(self, text):
        spans = tuple(MaskedSpan(type="P4", span=(i, i + 1)) for i, ch in enumerate(text) if ch.isdigit())
        return "".join("*" if ch.isdigit() else ch for ch in text), spans


class _Spy(PostcallPort):
    def __init__(self, draft=None):
        self.calls = []
        self.draft = draft

    async def summarize(self, call_id, segments):
        self.calls.append((call_id, len(segments)))
        return self.draft or CallSummaryDraft(
            call_id=call_id, summary_text="카드 분실 신고 접수", inquiry_type="사고 및 보상 문의",
            follow_up_actions=(FollowUpAction(action_text="재발급 안내 문자 발송"),))


class _Record(PostcallRecordPort):
    def __init__(self):
        self.saved = []

    async def record(self, draft):
        self.saved.append(draft)


def _run(port, segments=SEGMENTS, record=None):
    return asyncio.run(PostcallInteractor(postcall=port, record=record or _Record(), masking=_DigitMasking()).close(
        PostcallCommand(call_id="c_001", segments=segments)))


def test_전사를_포트에_그대로_넘긴다():
    port = _Spy()
    _run(port)
    assert port.calls == [("c_001", 2)]


def test_요약과_유형과_후속조치를_그대로_싣는다():
    draft = _run(_Spy())
    assert draft.summary_text == "카드 분실 신고 접수"
    assert draft.inquiry_type == "사고 및 보상 문의"
    assert draft.follow_up_actions[0].action_text == "재발급 안내 문자 발송"


def test_요약을_다시_다듬지_않는다():
    """손대면 모델 출력과 화면 표시가 달라져 환각 추적이 끊긴다."""
    odd = CallSummaryDraft(call_id="c_001", summary_text="  두 줄\n요약  ", inquiry_type=None)
    assert _run(_Spy(odd)).summary_text == "  두 줄\n요약  "


def test_모델이_confirmed_True를_보내도_무시한다():
    """확정은 상담원이 화면에서 하는 일이다 — 서버가 확정하는 경로를 만들지 않는다 (부록 A-1)."""
    forged = CallSummaryDraft(call_id="c_001", summary_text="요약", inquiry_type="반품", confirmed=True)
    assert _run(_Spy(forged)).confirmed is False


def test_유형은_없어도_된다():
    """D-2 는 제안이라 못 정할 수 있다. 억지로 채우지 않는다."""
    none_type = CallSummaryDraft(call_id="c_001", summary_text="요약", inquiry_type=None)
    assert _run(_Spy(none_type)).inquiry_type is None


def test_call_id를_요청_기준으로_고정한다():
    """스포크가 다른 call_id 를 실어도 요청한 통화에 붙는다."""
    wrong = CallSummaryDraft(call_id="OTHER", summary_text="요약")
    assert _run(_Spy(wrong)).call_id == "c_001"


def test_전사가_비면_거부한다():
    port = _Spy()
    record = _Record()
    with pytest.raises(ValueError):
        _run(port, (), record)
    assert port.calls == [] and record.saved == []


def test_돌려주는_초안과_같은_초안을_저장한다():
    """confirmed 를 덮고 call_id 를 고정한 **뒤의** 초안이 저장된다 — 모델이 보낸 원래 값이 아니다."""
    record = _Record()
    forged = CallSummaryDraft(call_id="OTHER", summary_text="요약", confirmed=True)
    draft = _run(_Spy(forged), record=record)
    assert record.saved == [draft]
    assert record.saved[0].call_id == "c_001" and record.saved[0].confirmed is False


def test_위반_발화_번호를_요약_포트에_같이_넘긴다():
    """2026-10-01 — 컴플라이언스가 잡은 상담원 발화가 「안내」로 요약에 실리지 않게. 조회가 죽어도 초안은 나온다."""
    from hub.app.ports.output.postcall_port import PostcallPort as _P  # noqa: PLC0415

    class _FlagSpy(_P):
        def __init__(self):
            self.got = None

        async def summarize(self, call_id, segments):
            raise AssertionError("summarize_with_flags 로 와야 한다")

        async def summarize_with_flags(self, call_id, segments, flagged_segment_ids):
            self.got = flagged_segment_ids
            return CallSummaryDraft(call_id=call_id, summary_text="요약", inquiry_type=None, follow_up_actions=())

    class _Flags:
        async def flagged_segment_ids(self, call_id):
            return frozenset({2})

    class _Broken:
        async def flagged_segment_ids(self, call_id):
            raise RuntimeError("DB 없음")

    port = _FlagSpy()
    asyncio.run(PostcallInteractor(postcall=port, record=_Record(), masking=_DigitMasking(), flags=_Flags()).close(
        PostcallCommand(call_id="c_001", segments=SEGMENTS)))
    assert port.got == frozenset({2})

    port = _FlagSpy()
    asyncio.run(PostcallInteractor(postcall=port, record=_Record(), masking=_DigitMasking(), flags=_Broken()).close(
        PostcallCommand(call_id="c_001", segments=SEGMENTS)))
    assert port.got == frozenset()


def test_화면이_보낸_원문_자막은_요약_전에_가린다():
    """2026-10-06(`decisions/326`) — 상담원 화면은 원문을 보여 주고, `/close` 는 그 화면의 자막을 받는다.
    요약 포트(모델 포함)에도, 저장되는 초안에도 원문 번호가 닿으면 안 된다."""

    class _Echo(PostcallPort):
        def __init__(self):
            self.seen = []

        async def summarize(self, call_id, segments):
            self.seen = [(s.text, s.masked) for s in segments]
            return CallSummaryDraft(call_id=call_id, summary_text=" / ".join(s.text for s in segments))

    raw = (PostcallSegment(segment_id=7, speaker="customer", raw_text="제 번호는 01012345678 입니다", is_final=True),)
    port, record = _Echo(), _Record()
    draft = _run(port, raw, record)
    assert port.seen[0][0] == "제 번호는 *********** 입니다"
    assert len(port.seen[0][1]) == 11  # 구간도 같이 넘어간다
    assert "01012345678" not in draft.summary_text
    assert "01012345678" not in record.saved[0].summary_text
