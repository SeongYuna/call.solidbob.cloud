# Requirement: B-2
"""검색 결과 캐시 — 어떤 `RetrievalPort` 든 감싼다 (`w7-lru-cache`).

**무엇을 캐시하나**: `retrieve(utterance, top_k)` 의 결과 목록 전체. 임베딩·리랭킹·ES 호출이 전부 건너뛰어진다 —
임베딩만 캐시하면 리랭킹(p95 의 대부분)이 그대로 남는다(`decisions/206` 실측: dense 59ms → rerank 521ms, CPU).

**키**: `sha256(인덱스 세대, top_k, 발화)` — 원문을 키에 두지 않는다(SEC-1). 받는 발화 자체도 **마스킹본**이어야 한다(`RecommendCommand` 계약).

**지식베이스를 재적재하면 무효화한다** — 캐시가 옛 조항을 계속 돌려주면 안 된다. `epoch()` 가 인덱스 세대를 알려 준다:
ES 인덱스 UUID(`--recreate` 로 새로 만들면 바뀐다). ⚠ `--recreate` 없이 덮어쓴 재적재는 UUID 가 그대로라 못 알아챈다 —
그래서 **최대 수명(`ttl_s`)** 을 함께 둔다. 세대 조회는 요청마다 하지 않고 `epoch_check_s` 마다 한다(ES 왕복을 지연에 섞지 않는다).

**품질 수치를 바꾸면 버그다** — 켠 값과 끈 값의 Recall@5·MRR 이 같아야 한다(`scripts/measure_cache.py` 가 확인한다).
"""

from __future__ import annotations

import time
from typing import Callable

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.domain.services.lru import LruCache, cache_key


class CachedRetriever(RetrievalPort):
    def __init__(
        self,
        inner: RetrievalPort,
        *,
        maxsize: int = 1024,
        ttl_s: float | None = 600.0,
        epoch: Callable[[], str] | None = None,
        epoch_check_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._cache: LruCache[str, tuple[RetrievedDoc, ...]] = LruCache(maxsize, ttl_s=ttl_s, clock=clock)
        self._epoch_fn = epoch
        self._epoch = epoch() if epoch else ""
        self._epoch_checked_at = clock()
        self._epoch_check_s = epoch_check_s
        self._clock = clock
        self.invalidations = 0

    @property
    def stats(self) -> dict:
        return {"hits": self._cache.hits, "misses": self._cache.misses, "size": len(self._cache), "invalidations": self.invalidations}

    def invalidate(self) -> None:
        self._cache.clear()
        self.invalidations += 1

    def _refresh_epoch(self) -> None:
        if self._epoch_fn is None or self._clock() - self._epoch_checked_at < self._epoch_check_s:
            return
        self._epoch_checked_at = self._clock()
        try:
            current = self._epoch_fn()
        except Exception:  # noqa: BLE001 — 세대를 못 읽으면 캐시를 믿지 않는다
            self.invalidate()
            return
        if current != self._epoch:
            self._epoch = current
            self.invalidate()

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if not utterance.strip():
            return []
        self._refresh_epoch()
        key = cache_key(self._epoch, top_k, utterance)
        cached = self._cache.get(key)
        if cached is not None:
            return list(cached)
        docs = await self._inner.retrieve(utterance, top_k=top_k)
        self._cache.put(key, tuple(docs))
        return docs


def es_index_epoch(client, index: str) -> Callable[[], str]:
    """ES 인덱스 UUID 를 세대로 쓴다. `--recreate` 재적재에서 바뀐다."""

    def _epoch() -> str:
        settings = client.indices.get_settings(index=index)
        return next(iter(settings.values()))["settings"]["index"]["uuid"]

    return _epoch
