# Requirement: C-5, SEC-1
"""`MaskingPort` 구현 — **규칙 마스킹 위에 NER(P6·P7)을 한 겹 더 얹는다.**

    원문 ──▶ fallback.mask()  (server/apps/masking — P1~P7 규칙)  ─┐
       └───▶ tagger.tag() → detect_entities()  (P6·P7 NER)        ─┴▶ 구간 합집합 → 마스킹

**규칙을 지우지 않고 두 겹으로 둔다**(`w5-ner-p6-p7`). 모델이 못 뜨거나 추론 중 예외가 나면
규칙 결과만 돌려준다 — 마스킹이 통째로 빠지는 것이 이름 몇 개를 놓치는 것보다 나쁘다.
반대로 NER 만 쓰고 규칙을 버리면 규칙이 잡던 문맥 이름(`"성함은 …"`)을 모델이 놓칠 때 뚫린다.
**합집합**이라 어느 한쪽이 잡으면 가려진다(누락 0건 > 과잉 억제).

`fallback` 은 **포트(추상)로 받는다.** `server/apps/masking` 을 여기서 import 하면 `ai → server`
스포크 직접 참조가 된다 — 무엇을 꽂을지는 합성 루트(`scripts/run_eval.py`·`ai/provider.py`)가 정한다.

⚠ **SEC-1**: 원문을 로그·예외 메시지에 싣지 않는다. 실패 로그에는 예외 **유형**만 남긴다.
"""

from __future__ import annotations

import logging
from typing import Protocol

from hub.app.dtos.transcript_dto import MaskedSpan
from hub.app.ports.output.masking_port import MaskingPort

from ...domain.services.spans import detect_entities_with_rejoin, merge_spans
from ...domain.value_objects.entity import EntitySpan, TokenTag

log = logging.getLogger(__name__)

# `server/apps/masking/domain/value_objects/pii_pattern.py` 의 `MASK_CHAR` 와 같아야 한다.
# import 할 수 없어(스포크 직접 참조) 값을 옮겨 적었다 — 둘이 같은지는 `ai/tests/` 가 고정한다.
MASK_CHAR = "*"

# NER 이 책임지는 패턴. 나머지(P1~P5)는 규칙만 본다.
NER_PATTERNS = ("P6", "P7")


class Tagger(Protocol):
    model_name: str

    def tag(self, text: str) -> list[TokenTag]: ...


class LayeredMaskingAdapter(MaskingPort):
    def __init__(self, fallback: MaskingPort, tagger: Tagger | None) -> None:
        self._fallback = fallback
        self._tagger = tagger
        # 모델이 실패해 규칙만으로 처리한 횟수. 운영 지표로 쓴다 — 0 이 아니면 NER 이 죽어 있다.
        self.ner_failures = 0

    @property
    def ner_enabled(self) -> bool:
        return self._tagger is not None

    def mask(self, text: str) -> tuple[str, tuple[MaskedSpan, ...]]:
        masked, rule_spans = self._fallback.mask(text)
        if self._tagger is None or not text:
            return masked, rule_spans

        try:
            # 띄어쓰기로 쪼개진 1음절(`"김 민준"`)을 붙인 사본을 한 번 더 본다 — 오류 내성 곡선에서 뚫린 2건이 전부 이것
            entities = detect_entities_with_rejoin(text, self._tagger.tag)
        except Exception as e:  # noqa: BLE001 — 어떤 실패든 규칙 결과로 내려간다
            self.ner_failures += 1
            log.warning("NER 실패 — 규칙 마스킹만 적용: %s", type(e).__name__)
            return masked, rule_spans

        if not entities:
            return masked, rule_spans

        combined = merge_spans(
            [EntitySpan(s.type, s.span[0], s.span[1]) for s in rule_spans] + entities
        )
        chars = list(masked)
        for s in combined:
            for i in range(s.start, min(s.end, len(chars))):
                chars[i] = MASK_CHAR
        return "".join(chars), tuple(
            MaskedSpan(type=s.pattern, span=(s.start, s.end)) for s in combined
        )
