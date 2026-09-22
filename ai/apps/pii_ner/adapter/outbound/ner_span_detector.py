# Requirement: C-5, SEC-1
"""NER 태거 → P6·P7 **구간**만 돌려주는 어댑터. 모델 HTTP 표면(`decisions/213`)이 이것을 싣는다.

**마스킹 판정을 하지 않는다**(절대 원칙 9). 가린 텍스트도, 「가려야 한다」는 결론도 내지 않는다 —
구간만 준다. P1~P7 규칙 마스킹과 합집합을 만들어 실제로 가리는 일은 부르는 쪽(`server/apps/masking` +
원격 어댑터)이 한다. 같은 프로세스 구성에서 `LayeredMaskingAdapter` 가 하는 일의 **NER 절반**이다.
"""

from __future__ import annotations

from typing import Protocol

from ...domain.services.spans import detect_entities_with_rejoin
from ...domain.value_objects.entity import EntitySpan, TokenTag


class Tagger(Protocol):
    model_name: str

    def tag(self, text: str) -> list[TokenTag]: ...


class NerSpanDetector:
    def __init__(self, tagger: Tagger) -> None:
        self._tagger = tagger
        self.model_name = tagger.model_name

    def spans(self, text: str) -> list[EntitySpan]:
        if not text.strip():
            return []
        return detect_entities_with_rejoin(text, self._tagger.tag)
