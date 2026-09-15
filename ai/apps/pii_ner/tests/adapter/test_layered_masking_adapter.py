# Requirement: C-5, SEC-1
"""규칙 + NER 두 겹. 모델 없이 가짜 태거로 배선만 고정한다 — 실제 모델은 `test_koelectra_ner_tagger.py`(slow)."""

from __future__ import annotations

import logging

import pytest

from hub.app.dtos.transcript_dto import MaskedSpan
from hub.app.ports.output.masking_port import MaskingPort

from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter
from pii_ner.domain.value_objects.entity import TokenTag


class PhoneOnlyRule(MaskingPort):
    """규칙 폴백 흉내 — `010` 으로 시작하는 11자리만 가린다."""

    def mask(self, text):
        i = text.find("010")
        if i < 0:
            return text, ()
        return text[:i] + "*" * 11 + text[i + 11 :], (MaskedSpan(type="P4", span=(i, i + 11)),)


class FixedTagger:
    model_name = "fake"

    def __init__(self, *pieces):
        self.pieces = pieces
        self.calls = 0

    def tag(self, text):
        self.calls += 1
        out = []
        for piece, label in self.pieces:
            i = text.find(piece)
            if i >= 0:
                out.append(TokenTag(i, i + len(piece), label))
        return out


class BrokenTagger:
    model_name = "broken"

    def tag(self, text):
        raise RuntimeError(f"모델이 죽었다: {text}")


TEXT = "제 이름은 오세준이고 번호는 01055667788 이에요"


def test_union_of_rule_and_ner():
    adapter = LayeredMaskingAdapter(PhoneOnlyRule(), FixedTagger(("오세", "PER")))
    masked, spans = adapter.mask(TEXT)
    assert "오세준" not in masked and "01055667788" not in masked
    assert {s.type for s in spans} == {"P4", "P6"}
    assert len(masked) == len(TEXT)  # 자리수 보존 — 7.3절 span 오프셋이 어긋나지 않는다


def test_spans_point_at_masked_characters():
    masked, spans = LayeredMaskingAdapter(PhoneOnlyRule(), FixedTagger(("오세", "PER"))).mask(TEXT)
    for s in spans:
        assert set(masked[s.span[0] : s.span[1]]) == {"*"}


def test_no_tagger_is_rule_only():
    rule = PhoneOnlyRule()
    adapter = LayeredMaskingAdapter(rule, None)
    assert adapter.mask(TEXT) == rule.mask(TEXT)
    assert adapter.ner_enabled is False


def test_tagger_failure_falls_back_to_rule_without_leaking_text(caplog):
    adapter = LayeredMaskingAdapter(PhoneOnlyRule(), BrokenTagger())
    with caplog.at_level(logging.WARNING):
        masked, spans = adapter.mask(TEXT)
    assert (masked, spans) == PhoneOnlyRule().mask(TEXT)
    assert adapter.ner_failures == 1
    # SEC-1 — 예외 메시지에 원문이 실려 있어도 로그에는 유형만 남는다
    assert "오세준" not in caplog.text and "01055667788" not in caplog.text


def test_no_entities_returns_rule_result_unchanged():
    adapter = LayeredMaskingAdapter(PhoneOnlyRule(), FixedTagger())
    assert adapter.mask(TEXT) == PhoneOnlyRule().mask(TEXT)


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_text(text):
    tagger = FixedTagger(("x", "PER"))
    masked, spans = LayeredMaskingAdapter(PhoneOnlyRule(), tagger).mask(text)
    assert spans == ()


class JoinedOnlyTagger:
    """붙인 사본에서만 이름을 알아보는 태거 — 실제 모델이 `"김 민준"` 을 못 잡고 `"김민준"` 은 잡은 것과 같다."""

    model_name = "fake"

    def tag(self, text):
        i = text.find("김민준")
        return [TokenTag(i, i + 3, "PER")] if i >= 0 else []


def test_split_name_is_masked_via_joined_copy():
    text = "그 김 민준 씨가 신고했어요"
    masked, spans = LayeredMaskingAdapter(PhoneOnlyRule(), JoinedOnlyTagger()).mask(text)
    assert masked == "그 **** 씨가 신고했어요"  # 가운데 공백까지 덮는다 — 자리수는 그대로
    assert len(masked) == len(text) and [s.type for s in spans] == ["P6"]
