# Requirement: 7.3절 인터페이스 계약 v2, QUA-1
"""허브 DTO 가 7.3절 v2 계약 예시를 그대로 담을 수 있는지."""

from hub.app.dtos import Card, ClosureVerdict, MaskedSpan, RecommendationCards, Source, TranscriptEvent


def test_transcript_event_matches_contract_example():
    ev = TranscriptEvent(
        call_id="c_001", segment_id=17, speaker="customer", text="카드번호는 **** 입니다",
        masked=(MaskedSpan(type="P2", span=(6, 10)),), is_final=True, utterance_end_ms=3100,
    )
    start, end = ev.masked[0].span
    assert ev.masked[0].type == "P2" and ev.text[start:end] == "****"


def test_recommendation_cards_empty_means_no_relevant_document():
    empty = RecommendationCards(call_id="c_001", trigger_at_ms=3150)
    assert empty.no_relevant_document
    card = Card(title="프로모션 할인 적용 시점 안내", summary="…",
                source=Source(doc_id="TERM-3.2", title="요금제약관 3.2조"), similarity_score=0.87)
    assert not RecommendationCards(call_id="c_001", trigger_at_ms=3150, cards=(card,)).no_relevant_document


def test_closure_verdict_carries_gs009_shape():
    v = ClosureVerdict(
        call_id="c_001", closure_type="해지",
        evidence={"위약금_안내": True, "잔여할부_안내": False, "고객확인_기록": False},
        verdict="blocked", missing=("잔여할부_안내", "고객확인_기록"),
        source=Source(doc_id="POLICY-CANCEL-1", title="내부처리규정 해지 필수 근거"),
    )
    assert v.verdict == "blocked" and v.source.doc_id == "POLICY-CANCEL-1"
