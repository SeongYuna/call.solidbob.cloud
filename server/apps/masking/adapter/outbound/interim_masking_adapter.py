# Requirement: C-5, SEC-1
"""중간 자막용 MaskingPort — 어떤 마스킹 구현이든 감싸고, 남은 숫자 덩어리를 한 번 더 가린다.

안쪽(규칙 또는 규칙+NER, `LayeredMaskingAdapter`)이 먼저 가리고, 그 결과에 `interim_digit_guard` 를 얹는다.
안쪽 구간은 그대로 두고 가드 구간을 더한다. 확정 자막에는 쓰지 않는다 — 인터랙터가 `is_final` 로 고른다.
"""

from __future__ import annotations

from hub.app.dtos.transcript_dto import MaskedSpan
from hub.app.ports.output.masking_port import MaskingPort

from ...domain.services.interim_digit_guard import guard_interim


class InterimMaskingAdapter(MaskingPort):
    def __init__(self, inner: MaskingPort) -> None:
        self._inner = inner

    def mask(self, text: str) -> tuple[str, tuple[MaskedSpan, ...]]:
        masked, spans = self._inner.mask(text)
        guarded, extra = guard_interim(masked)
        merged = list(spans) + [MaskedSpan(type=s.pattern, span=(s.start, s.end)) for s in extra]
        return guarded, tuple(sorted(merged, key=lambda s: s.span[0]))
