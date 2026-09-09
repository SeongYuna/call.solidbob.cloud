# Requirement: B-4, B-5, B-6, QUA-1
"""폴백 생성 — 스니펫을 그대로 옮긴다. 지어내지 않으므로 환각이 구조적으로 0이다."""

import asyncio

from hub.adapter.outbound.snippet_card_adapter import SnippetCardAdapter
from hub.app.dtos import RetrievedDoc

DOCS = [
    RetrievedDoc(doc_id="SHOP-TERM-4.1", title="반품 배송비", snippet="단순 변심은 고객 부담", score=0.91),
    RetrievedDoc(doc_id="SHOP-TERM-4.2", title="교환 절차", snippet="재고 확인 후 진행", score=0.55),
]


def _cards(docs):
    return asyncio.run(SnippetCardAdapter().to_cards("반품 배송비", docs))


def test_스니펫을_그대로_summary로_옮긴다():
    """요약하지 않으므로 원문에 없는 말이 섞일 수 없다 (B-6 환각 0)."""
    cards = _cards(DOCS)
    assert [c.summary for c in cards] == ["단순 변심은 고객 부담", "재고 확인 후 진행"]


def test_출처를_반드시_채운다():
    cards = _cards(DOCS)
    assert all(c.source.doc_id for c in cards)
    assert [c.source.doc_id for c in cards] == ["SHOP-TERM-4.1", "SHOP-TERM-4.2"]


def test_점수를_그대로_옮긴다():
    """화면에 표시되는 유사도다 — '위험도'가 아니다 (부록 A-1)."""
    assert [c.similarity_score for c in _cards(DOCS)] == [0.91, 0.55]


def test_검색_순서를_바꾸지_않는다():
    assert [c.title for c in _cards(DOCS)] == ["반품 배송비", "교환 절차"]


def test_출처가_없는_문서는_카드가_되지_않는다():
    """근거 없는 카드를 렌더링하지 않는다 (B-5·B-6)."""
    docs = DOCS + [RetrievedDoc(doc_id="", title="출처없음", snippet="…", score=0.9)]
    assert len(_cards(docs)) == 2


def test_검색_결과가_없으면_빈_목록이다():
    """'관련 문서 없음'(B-6) — 억지로 채우지 않는다."""
    assert _cards([]) == []
