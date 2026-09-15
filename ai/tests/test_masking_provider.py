# Requirement: C-5, SEC-1
"""`build_masking_provider` — 규칙 마스킹 위에 NER 을 얹는 합성 지점.

`pii_ner` 가 `server/apps/masking` 을 import 할 수 없어 옮겨 적은 값(`MASK_CHAR`)이 실제와 같은지를
**두 모듈을 동시에 볼 수 있는 여기서** 고정한다.
"""

from __future__ import annotations

from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter
from masking.domain.value_objects.pii_pattern import MASK_CHAR as SERVER_MASK_CHAR

from pii_ner.adapter.outbound.layered_masking_adapter import MASK_CHAR, NER_PATTERNS
from pii_ner.domain.value_objects.entity import TokenTag
from provider import build_masking_provider


def test_mask_char_matches_server():
    assert MASK_CHAR == SERVER_MASK_CHAR


def test_ner_patterns_are_the_ones_server_marks_partial():
    from masking.adapter.outbound.rule_masking_adapter import PARTIAL_PATTERNS

    assert set(NER_PATTERNS) == set(PARTIAL_PATTERNS)


def test_missing_model_dir_is_rule_only(tmp_path):
    provider, enabled = build_masking_provider(RuleMaskingAdapter(), ner_model_dir=tmp_path / "없음")
    assert enabled is False
    text = "그 김민준 씨가 연락처 010-1234-5678 남겼어요"
    assert provider().mask(text) == RuleMaskingAdapter().mask(text)


def test_with_tagger_layers_on_real_rule_adapter():
    class Tagger:
        model_name = "fake"

        def tag(self, text):
            i = text.find("김민준")
            return [TokenTag(i, i + 3, "PER")] if i >= 0 else []

    provider, enabled = build_masking_provider(RuleMaskingAdapter(), ner_model_dir=None, tagger=Tagger())
    assert enabled is True
    masked, spans = provider().mask("그 김민준 씨가 연락처 010-1234-5678 남겼어요")
    assert "김민준" not in masked and "1234" not in masked
    assert {s.type for s in spans} == {"P4", "P6"}
