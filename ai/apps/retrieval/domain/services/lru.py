# Requirement: B-2
"""LRU 캐시 — 순수 파이썬(`OrderedDict`). 검색 결과 캐시(`adapter/outbound/cached_retriever.py`)가 쓴다 (`w7-lru-cache`).

런북 「만들지 말 것」·`server/CLAUDE.md` §6 이 캐시를 **인메모리 LRU** 로 정했다(ElastiCache·Redis 를 쓰지 않는다).

**키에 원문을 두지 않는다**(SEC-1 — 「마스킹 전 원문이 DB·로그 **어디에도** 남지 않음」, 메모리 캐시도 어디에 해당한다).
키는 호출부가 만든 해시다. 이 클래스는 키가 무엇인지 모른다 — 그래서 `cache_key()` 를 함께 둔다.

**시계를 주입받는다** — 최대 수명(TTL)을 테스트에서 시간을 흘려 확인할 수 있어야 한다.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Callable, Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


def cache_key(*parts: object) -> str:
    """SHA-256 16진수. 원문을 되돌릴 수 없는 키 — 캐시를 덤프해도 발화가 나오지 않는다."""
    h = hashlib.sha256()
    for p in parts:
        h.update(repr(p).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class LruCache(Generic[K, V]):
    def __init__(self, maxsize: int, *, ttl_s: float | None = None, clock: Callable[[], float] = time.monotonic) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize 는 양수여야 한다")
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()
        self._maxsize = maxsize
        self._ttl = ttl_s
        self._clock = clock
        self.hits = 0
        self.misses = 0

    def get(self, key: K) -> V | None:
        item = self._data.get(key)
        if item is None:
            self.misses += 1
            return None
        stored_at, value = item
        if self._ttl is not None and self._clock() - stored_at > self._ttl:
            del self._data[key]
            self.misses += 1
            return None
        self._data.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: K, value: V) -> None:
        self._data[key] = (self._clock(), value)
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else float("nan")
