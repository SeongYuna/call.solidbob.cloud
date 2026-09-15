# Requirement: D-1, D-2, D-3, SEC-1, QUA-1
"""어댑터: interim 을 버리고 segment_id 순으로 도메인에 넘기며, 늘 초안(confirmed=False)으로 돌려준다."""

import asyncio

from hub.app.dtos.transcript_dto import TranscriptEvent
from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter


def _seg(segment_id, speaker, text, is_final=True):
    return TranscriptEvent(call_id="c1", segment_id=segment_id, speaker=speaker, text=text, is_final=is_final)


def test_interim은_버리고_segment_id_순으로_발췌한다():
    segments = [
        _seg(3, "agent", "신분증과 임대차계약서가 필요합니다"),
        _seg(2, "customer", "전입신고에 필요한 서류가 뭔가요"),
        _seg(1, "customer", "전입신고에 필요한 서", is_final=False),
    ]
    draft = asyncio.run(RulePostcallAdapter().summarize("c1", segments))
    assert draft.summary_text.startswith(
        "고객 문의: 전입신고에 필요한 서류가 뭔가요 / 상담원 안내: 신분증과 임대차계약서가 필요합니다"
    )
    assert "발화 고객 1건 · 상담원 1건" in draft.summary_text  # interim 은 세지 않는다


def test_초안으로_돌려주고_후속조치를_DTO로_옮긴다():
    draft = asyncio.run(RulePostcallAdapter().summarize("c1", [_seg(1, "agent", "결과는 문자로 보내 드리겠습니다")]))
    assert draft.call_id == "c1"
    assert draft.confirmed is False
    assert draft.inquiry_type is None
    assert [a.action_text for a in draft.follow_up_actions] == ["결과는 문자로 보내 드리겠습니다"]
