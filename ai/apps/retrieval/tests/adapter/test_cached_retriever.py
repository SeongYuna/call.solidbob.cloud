# Requirement: B-2, SEC-1
"""검색 캐시 — 적중·수명·세대 무효화·키에 원문이 없는지."""

from __future__ import annotations

import asyncio

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.adapter.outbound.cached_retriever import CachedRetriever
from retrieval.domain.services.lru import LruCache, cache_key


class Counting(RetrievalPort):
    def __init__(self):
        self.calls = 0

    async def retrieve(self, utterance, top_k=5):
        self.calls += 1
        return [RetrievedDoc(doc_id=f"D-{self.calls}", title="t", snippet="s", score=1.0)]


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def run(r, q, k=5):
    return asyncio.run(r.retrieve(q, top_k=k))


def test_second_call_is_hit_and_same_result():
    inner = Counting()
    r = CachedRetriever(inner)
    assert run(r, "등본 대리 발급") == run(r, "등본 대리 발급")
    assert inner.calls == 1 and r.stats["hits"] == 1


def test_top_k_is_part_of_key():
    inner = Counting()
    r = CachedRetriever(inner)
    run(r, "q", 5)
    run(r, "q", 3)
    assert inner.calls == 2


def test_ttl_expires():
    clock, inner = Clock(), Counting()
    r = CachedRetriever(inner, ttl_s=10, clock=clock)
    run(r, "q")
    clock.t = 11
    run(r, "q")
    assert inner.calls == 2


def test_reindex_changes_epoch_and_invalidates():
    clock, inner = Clock(), Counting()
    epoch = {"v": "uuid-1"}
    r = CachedRetriever(inner, epoch=lambda: epoch["v"], epoch_check_s=5, clock=clock, ttl_s=None)
    run(r, "q")
    epoch["v"] = "uuid-2"  # --recreate 재적재
    clock.t = 6
    assert run(r, "q")[0].doc_id == "D-2"  # 옛 조항을 돌려주지 않는다
    assert r.invalidations == 1


def test_epoch_failure_distrusts_cache():
    clock, inner = Clock(), Counting()
    calls = {"n": 0}

    def epoch():
        calls["n"] += 1
        if calls["n"] > 1:
            raise ConnectionError("ES 없음")
        return "uuid-1"

    r = CachedRetriever(inner, epoch=epoch, epoch_check_s=1, clock=clock)
    run(r, "q")
    clock.t = 2
    run(r, "q")
    assert inner.calls == 2


def test_key_holds_no_raw_text():
    """SEC-1 — 캐시를 덤프해도 발화가 나오지 않는다."""
    r = CachedRetriever(Counting())
    utterance = "제 이름 박서연이고 등본 떼려고요"
    run(r, utterance)
    keys = list(r._cache._data.keys())
    assert keys and all(utterance not in k and "박서연" not in k for k in keys)
    assert keys[0] == cache_key("", 5, utterance)


def test_lru_evicts_oldest():
    c = LruCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")
    c.put("c", 3)
    assert c.get("b") is None and c.get("a") == 1


def test_empty_query_not_cached():
    inner = Counting()
    r = CachedRetriever(inner)
    assert run(r, "  ") == [] and inner.calls == 0
