# Requirement: C-5
"""실제 `koelectra-ner` 로 골든셋이 놓쳤던 이름을 잡는지. 모델이 없으면 건너뛴다 — CI 에 모델 다운로드를 넣지 않는다."""

from __future__ import annotations

from pathlib import Path

import pytest

from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger, _entity_type
from pii_ner.domain.services.spans import detect_entities

MODEL_DIR = Path(__file__).resolve().parents[5] / "models" / "koelectra-ner"


@pytest.mark.parametrize(
    "label, expected",
    [("PER-B", "PER"), ("LOC-I", "LOC"), ("B-PER", "PER"), ("I_ORG", "ORG"), ("O", "O")],
)
def test_entity_type_strips_bio_either_side(label, expected):
    assert _entity_type(label) == expected


@pytest.mark.slow
@pytest.mark.skipif(not MODEL_DIR.exists(), reason="models/koelectra-ner 없음")
@pytest.mark.parametrize(
    "text, name",
    [
        ("저는 최지훈이고요 등본 발급 문의드려요", "최지훈"),  # GS-412
        ("신청인 이름은 한서윤으로 넣어주세요", "한서윤"),  # GS-413
        ("그 김민준 씨가 어제 신고한 건 확인 부탁드려요", "김민준"),  # GS-056
        ("제 이름은 오세준이고 번호는 01055667788 이에요", "오세준"),  # GS-416
    ],
)
def test_real_model_covers_names(text, name):
    tagger = _tagger()
    covered = [text[s.start : s.end] for s in detect_entities(text, tagger.tag(text)) if s.pattern == "P6"]
    assert name in covered


@pytest.mark.slow
@pytest.mark.skipif(not MODEL_DIR.exists(), reason="models/koelectra-ner 없음")
def test_long_text_is_scanned_to_the_end():
    # 창을 나누지 않고 truncation 에만 맡기면 뒤쪽 이름을 아예 안 본다
    text = "민원 내용 설명입니다 " * 20 + "신청인 이름은 한서윤으로 넣어주세요"
    spans = detect_entities(text, _tagger().tag(text))
    assert any(text[s.start : s.end] == "한서윤" for s in spans)


_CACHED: list[KoElectraNerTagger] = []


def _tagger() -> KoElectraNerTagger:
    if not _CACHED:
        _CACHED.append(KoElectraNerTagger(MODEL_DIR))
    return _CACHED[0]
