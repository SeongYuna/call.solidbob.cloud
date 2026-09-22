# Requirement: B-2, E-1
"""`compare_retrievers.py` 의 항목별 상위 k 기록 — ES·모델 없이 가짜 검색기로 형식만 고정한다.
실행: `.venv/bin/python -m pytest scripts/tests -q`

2026-09-22 `w6-golden-set-loose-ends` ③ — 집계만 남아 GS-205 가 왜 틀렸는지 다시 돌려야 알 수 있었다.
**집계(`measure` 의 반환값) 형식은 그대로여야 한다** — 09-15 비교 파일과 줄끼리 대조하기 때문이다.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from compare_retrievers import item_row, items_path, measure  # noqa: E402
from evaluation.golden_set import GoldenItem  # noqa: E402
from hub.app.dtos.retrieved_doc_dto import RetrievedDoc  # noqa: E402

AGGREGATE_KEYS = {"recall_at_5", "mrr", "hits", "n", "p50_ms", "p95_ms", "missed", "top1"}


def _doc(doc_id: str, score: float) -> RetrievedDoc:
    return RetrievedDoc(doc_id=doc_id, title=f"제목 {doc_id}", snippet="…", score=score)


class _FakeRetriever:
    """질의마다 정해 둔 순위를 돌려준다."""

    def __init__(self, table: dict[str, list[str]]):
        self._table = table

    async def retrieve(self, utterance: str, top_k: int = 5):
        ids = self._table.get(utterance, [])
        return [_doc(d, 10.0 - i) for i, d in enumerate(ids)][:top_k]


def _items() -> list[GoldenItem]:
    return [
        GoldenItem(id="GS-1", module="B", customer_utterance="맞는 질의",
                   expected_doc_ids=["A"], distractor_doc_ids=["Z"]),
        GoldenItem(id="GS-2", module="B", customer_utterance="틀린 질의", expected_doc_ids=["B"],
                   context_utterances=["앞 맥락"]),
    ]


def test_item_row_records_scored_top_k_and_first_hit_rank():
    item = _items()[0]
    row = item_row(item, "맞는 질의", [_doc("X", 3.0), _doc("A", 2.5), _doc("Y", 1.0)])
    assert row["id"] == "GS-1"
    assert row["expected"] == ["A"] and row["distractors"] == ["Z"]
    assert row["hit"] is True and row["first_hit_rank"] == 2
    assert row["top_k"][0] == {"rank": 1, "doc_id": "X", "title": "제목 X", "score": 3.0}
    assert [d["rank"] for d in row["top_k"]] == [1, 2, 3]


def test_item_row_miss_has_null_rank_and_keeps_only_k():
    item = _items()[1]
    docs = [_doc(f"D{i}", 10 - i) for i in range(8)]
    row = item_row(item, "앞 맥락 틀린 질의", docs, top_k=5)
    assert row["hit"] is False and row["first_hit_rank"] is None
    assert len(row["top_k"]) == 5  # 채점한 k 만 — 그 밖의 순위는 모른다고 남긴다


def test_measure_fills_rows_without_changing_aggregate():
    items = _items()
    fake = _FakeRetriever({"맞는 질의": ["A", "X"], "앞 맥락 틀린 질의": ["X", "Y"]})
    rows: list[dict] = []
    with_rows = measure(fake, items, rows=rows)
    without = measure(fake, items)

    assert set(with_rows) == AGGREGATE_KEYS
    assert {k: v for k, v in with_rows.items() if not k.endswith("_ms")} == \
        {k: v for k, v in without.items() if not k.endswith("_ms")}
    assert with_rows["missed"] == ["GS-2"]
    # 질의는 하네스와 같은 `retrieval_query`(맥락 + 발화)로 기록된다
    assert [r["query"] for r in rows] == ["맞는 질의", "앞 맥락 틀린 질의"]
    assert [r["hit"] for r in rows] == [True, False]


def test_items_path_sits_next_to_aggregate():
    assert items_path(Path("/x/2026-09-22.json")) == Path("/x/2026-09-22.items.json")
    assert items_path(Path("/x/bm25-only.json")).name == "bm25-only.items.json"
