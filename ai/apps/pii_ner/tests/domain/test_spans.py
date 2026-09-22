# Requirement: C-5
"""P6·P7 구간 규칙. 태그 모양은 2026-09-15 `koelectra-ner` 실측 출력을 그대로 옮겼다."""

from __future__ import annotations

import pytest

from pii_ner.domain.services.spans import (
    address_spans,
    detect_entities,
    join_split_syllables,
    map_spans_back,
    merge_spans,
    person_spans,
)
from pii_ner.domain.value_objects.entity import EntitySpan, TokenTag


def tags_for(text: str, *pieces: tuple[str, str]) -> list[TokenTag]:
    """(조각, 유형) 순서대로 원문에서 찾아 태그를 만든다."""
    out, cursor = [], 0
    for piece, label in pieces:
        i = text.index(piece, cursor)
        out.append(TokenTag(i, i + len(piece), label))
        cursor = i + len(piece)
    return out


def covered(text: str, spans: list[EntitySpan]) -> list[str]:
    return [text[s.start : s.end] for s in spans]


class TestPerson:
    def test_self_intro_name_with_particle(self):  # GS-412 — 규칙 폴백이 놓친 건
        t = "저는 최지훈이고요 등본 발급 문의드려요"
        assert covered(t, person_spans(t, tags_for(t, ("최지", "PER"), ("훈", "PER")))) == ["최지훈"]

    def test_name_before_euro(self):  # GS-413
        t = "신청인 이름은 한서윤으로 넣어주세요"
        tags = tags_for(t, ("한", "PER"), ("서", "PER"), ("윤", "PER"))
        assert covered(t, person_spans(t, tags)) == ["한서윤"]

    def test_model_drops_last_syllable_extends_to_eojeol(self):
        # 실측: "오세준이고" 에서 모델은 "오세" 만 PER. 끝 글자 "준" 이 노출되면 누락이다
        t = "제 이름은 오세준이고 번호는 01055667788 이에요"
        assert covered(t, person_spans(t, tags_for(t, ("오세", "PER")))) == ["오세준"]

    def test_context_free_name(self):  # GS-056 — 규칙이 구조적으로 못 잡는 것
        t = "그 김민준 씨가 어제 신고한 건 확인 부탁드려요"
        tags = tags_for(t, ("김민", "PER"), ("준", "PER"), ("어제", "DAT"))
        assert covered(t, person_spans(t, tags)) == ["김민준"]

    def test_unknown_ending_masks_whole_eojeol(self):
        # 벗길 수 없는 활용이 붙으면 어절째 가린다 — 애매하면 가린다
        t = "오세준이었다던데"
        assert covered(t, person_spans(t, tags_for(t, ("오세", "PER")))) == ["오세준이었다던데"]

    def test_never_shrinks_below_model_span(self):
        # 모델이 "이" 까지 이름이라고 했으면 조사처럼 보여도 벗기지 않는다
        t = "김은이 씨"
        assert covered(t, person_spans(t, tags_for(t, ("김은이", "PER")))) == ["김은이"]

    def test_digit_only_per_is_ignored(self):
        # 실측: 카드번호 가운데 "89" 를 PER 로 줬다
        t = "카드 1234567890123456 으로 결제했어요"
        assert person_spans(t, tags_for(t, ("89", "PER"))) == []

    def test_separate_names_stay_separate(self):
        t = "김민준 이영희"
        tags = tags_for(t, ("김민준", "PER"), ("이영희", "PER"))
        assert covered(t, person_spans(t, tags)) == ["김민준", "이영희"]

    def test_stops_at_punctuation(self):
        t = "박지민, 맞아요"
        assert covered(t, person_spans(t, tags_for(t, ("박지", "PER")))) == ["박지민"]

    # ── 2026-09-22 `w6-c5-name-tail-leak` — 벗긴 조사 「이」 가 이름 끝 글자일 수 있다 ──
    def test_short_name_keeps_trailing_i(self):
        # 모델이 「유」 만 PER 로 주면 꼬리 「이」 를 조사로 벗겨 「이」 가 샌다(SYN-017 「다나카 유이」 모양)
        t = "저 이름 다나카 유이."
        tags = tags_for(t, ("다나카", "PER"), ("유", "PER"))
        assert covered(t, person_spans(t, tags)) == ["다나카", "유이"]

    def test_two_syllable_korean_stem_keeps_i_of_copula(self):
        # 실측(2026-09-22): "김서이에요" 에서 모델은 「김」 만 PER. 「이에요」 를 벗기면 「김서」 만 남는다
        t = "제 이름은 김서이에요."
        assert covered(t, person_spans(t, tags_for(t, ("김", "PER")))) == ["김서이"]

    def test_three_syllable_name_still_strips_copula(self):
        # 「이」 를 붙이는 것은 두 글자 이하일 때만 — 흔한 세 글자 이름 + 「이고」 는 그대로 벗긴다
        t = "제 이름은 오세준이고 번호는"
        assert covered(t, person_spans(t, tags_for(t, ("오세", "PER")))) == ["오세준"]

    # ── 2026-09-22 `w6-c5-overmask-request-word` — 운영 블랙리스트 사유 ──
    def test_request_word_before_name_is_not_person(self):
        # 실측 태그 그대로: 뒤에 이름이 오면 모델이 「요청」 과 여는 괄호까지 PER 로 준다
        t = "운영 점검용 테스트 요청 (정성윤, 09-22) — 블랙리스트 확인"
        tags = tags_for(t, ("요청", "PER"), ("(", "PER"), ("정성", "PER"), ("윤", "PER"), ("09", "AFW"))
        assert covered(t, person_spans(t, tags)) == ["정성윤"]

    def test_test_word_before_name_is_not_person(self):
        # 같은 문장을 줄이면 이번엔 「테스트」 를 PER 로 준다(같은 날 실측)
        t = "테스트 요청 (정성윤, 09-22) — 반복 폭언 고객 차단 요청"
        tags = tags_for(t, ("테스트", "PER"), ("(", "PER"), ("정성", "PER"), ("윤", "PER"))
        assert covered(t, person_spans(t, tags)) == ["정성윤"]

    def test_excluded_word_only_when_whole_span(self):
        # 목록 단어가 이름 **일부**일 때는 빼지 않는다 — 어절 전체가 그 말일 때만
        t = "요청희 씨"
        assert covered(t, person_spans(t, tags_for(t, ("요청희", "PER")))) == ["요청희"]


class TestAddress:
    def test_full_address_strips_trailing_copula(self):  # GS-033
        t = "저희 집 주소가 서울시 강남구 테헤란로 123번지 456호예요"
        tags = tags_for(
            t, ("서울시", "LOC"), ("강남구", "LOC"), ("테헤란", "AFW"), ("로", "AFW"),
            ("123", "NUM"), ("45", "NUM"),
        )
        assert covered(t, address_spans(t, tags)) == ["서울시 강남구 테헤란로 123번지 456호"]

    def test_road_address_with_particle(self):  # GS-415
        t = "성북구 정릉로 77길 12에서 물이 새요"
        tags = tags_for(t, ("성북구", "LOC"), ("정", "AFW"), ("릉", "AFW"), ("로", "AFW"), ("77", "NUM"))
        assert covered(t, address_spans(t, tags)) == ["성북구 정릉로 77길 12"]

    def test_district_alone_is_not_detailed_address(self):
        t = "강남구 민원실 어디예요"
        assert address_spans(t, tags_for(t, ("강남구", "LOC"))) == []

    def test_number_without_place_is_not_address(self):  # GS-419
        t = "1234 번지 앞에 불법주차가 있어요"
        assert address_spans(t, tags_for(t, ("123", "NUM"), ("4", "NUM"))) == []

    def test_money_after_place_is_not_address_number(self):
        t = "서울시 25만원을 받았어요"
        assert address_spans(t, tags_for(t, ("서울시", "LOC"))) == []

    def test_afw_without_road_suffix_is_not_place(self):
        # AFW 는 도로가 아닌 인공물에도 붙는다
        t = "갤럭시 12 샀어요"
        assert address_spans(t, tags_for(t, ("갤럭시", "AFW"))) == []


class TestMerge:
    def test_wider_pattern_wins(self):
        merged = merge_spans([EntitySpan("P6", 0, 3), EntitySpan("P7", 2, 10)])
        assert merged == [EntitySpan("P7", 0, 10)]

    def test_non_overlapping_kept(self):
        spans = [EntitySpan("P6", 0, 3), EntitySpan("P4", 5, 16)]
        assert merge_spans(spans) == spans

    def test_detect_entities_combines_both(self):
        t = "저는 최지훈이고 성북구 정릉로 12에 살아요"
        tags = tags_for(t, ("최지훈", "PER"), ("성북구", "LOC"), ("정릉로", "AFW"))
        assert covered(t, detect_entities(t, tags)) == ["최지훈", "성북구 정릉로 12"]


class TestSplitSyllables:
    """STT 띄어쓰기 쪼개짐 — 2026-09-15 오류 내성 곡선에서 규칙+NER 을 뚫은 두 모양."""

    @pytest.mark.parametrize(
        "text, joined",
        [
            ("그 김 민준 씨가", "그 김민준 씨가"),  # 1음절끼리는 안 붙인다 — "그" 는 그대로
            ("성북구 정 릉로 77길 12에서", "성북구 정릉로 77길 12에서"),
            ("김민 준 씨", "김민준 씨"),  # 오른쪽이 1음절뿐이면 왼쪽에 붙인다
            ("서울시 강남구", "서울시 강남구"),  # 정상 띄어쓰기는 건드리지 않는다
            ("이 오 이 오", "이 오 이 오"),
            # ↓ 2026-09-17 AI Hub 실제 발화 20,278건에서 NER 이 가짜 이름을 만든 자리 — 감탄사·대명사 한 글자는 붙이지 않는다
            ("네 이제 신청할게요", "네 이제 신청할게요"),  # "네이제" 를 인명으로 태깅했다(6건)
            ("네 제 이름은요", "네 제 이름은요"),  # "제이름은" → "네 제" 가림(9건)
            ("아 유선으로 할게요", "아 유선으로 할게요"),
            ("네 오늘 방문했어요", "네 오늘 방문했어요"),
        ],
    )
    def test_join(self, text, joined):
        assert join_split_syllables(text)[0] == joined

    def test_spans_map_back_over_removed_space(self):
        text = "그 김 민준 씨가"
        joined, index_map = join_split_syllables(text)
        i = joined.index("김민준")
        (span,) = map_spans_back([EntitySpan("P6", i, i + 3)], index_map)
        assert text[span.start : span.end] == "김 민준"
