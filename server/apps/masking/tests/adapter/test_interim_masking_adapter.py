# Requirement: C-5, QUA-1
"""중간 자막 어댑터 — 어떤 마스킹 구현이든 감싸고, 남은 숫자 덩어리를 한 번 더 가린다."""

from hub.app.dtos.transcript_dto import MaskedSpan
from hub.app.ports.output.masking_port import MaskingPort
from masking.adapter.outbound.interim_masking_adapter import InterimMaskingAdapter
from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter


class _NameOnly(MaskingPort):
    def mask(self, text):
        i = text.find("김민준")
        if i < 0:
            return text, ()
        return text[:i] + "***" + text[i + 3:], (MaskedSpan(type="P6", span=(i, i + 3)),)


def test_안쪽_구현의_구간을_지우지_않고_숫자_구간을_더한다():
    masked, spans = InterimMaskingAdapter(_NameOnly()).mask("김민준 010 0000")
    assert masked == "*** *** ****"
    assert [(s.type, s.span) for s in spans] == [("P6", (0, 3)), ("P4", (4, 12))]


def test_완성된_번호는_안쪽_규칙이_잡은_그대로다():
    masked, spans = InterimMaskingAdapter(RuleMaskingAdapter()).mask("제 번호는 01012345678 이요")
    assert "01012345678" not in masked
    assert [s.type for s in spans] == ["P4"]
