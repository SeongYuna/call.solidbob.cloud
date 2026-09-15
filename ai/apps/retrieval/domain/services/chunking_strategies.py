# Requirement: B-2
"""청킹 전략 비교용 — 고정 길이 · 시멘틱. 기본 전략(「1 조항 = 1 청크」)은 `chunking.py` 에 있다 (`w4-chunking-compare`).

**운영 색인은 여전히 `chunking.chunk_markdown` 이다.** 이 파일은 비교 실험에만 쓴다.

## 채점을 먼저 정한다 — 대표 조항 ID

골든셋 `expected_doc_ids` 는 조항 ID 단위다. 조항 경계를 넘나드는 청크에는 ID 를 하나만 달 수 있으므로
규칙을 고정한다:

    대표 조항 = 그 청크 안에서 **글자를 가장 많이 차지한 조항** (동률이면 앞에 나온 조항)

`Chunk.doc_id` 에 대표 조항을 넣으면 검색 어댑터(`collapse: doc_id`)와 채점기가 **한 줄도 안 바뀌고** 돈다.
그 대가로 «정답 조항이 청크 안에 들어 있는데 대표가 아니라서 틀림» 이 생긴다 — 그래서 청크가 덮은 조항 전부를
`covered_doc_ids` 로 함께 돌려준다. 비교 스크립트가 **엄격(대표 ID)·느슨(덮은 조항 중 하나)** 두 채점을
나란히 찍어 «못 찾아서» 와 «채점이 못 알아봐서» 를 가른다.

## 순수 파이썬이다

시멘틱 청킹은 문장 임베딩이 필요하지만 **벡터는 인자로 받는다** — 모델 호출은 adapter 몫이다(`ai/.importlinter` 계약 3).
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from ..value_objects.chunk import Chunk


@dataclass(frozen=True)
class StreamChunk:
    chunk: Chunk
    covered_doc_ids: tuple[str, ...]  # 청크가 한 글자라도 덮은 조항, 등장 순


@dataclass(frozen=True)
class _Segment:
    doc_id: str
    start: int
    end: int


def _stream(articles: Sequence[Chunk]) -> tuple[str, list[_Segment]]:
    """조항들을 원래 순서대로 이어 붙인 글 한 편 + 글자 구간별 소유 조항.

    제목을 본문 앞에 넣는다 — 고정 길이·시멘틱 청크에는 `title` 필드가 따로 없으므로(청크가 조항을 가로지른다)
    조항 청크가 `title` 필드로 보는 정보를 본문으로 옮겨야 비교가 «입력» 이 아니라 «자르는 법» 차이가 된다.
    """
    parts, segments, pos = [], [], 0
    for a in articles:
        piece = f"{a.title}\n{a.text}\n\n"
        parts.append(piece)
        segments.append(_Segment(a.doc_id, pos, pos + len(piece)))
        pos += len(piece)
    return "".join(parts), segments


def _ownership(segments: list[_Segment], start: int, end: int) -> tuple[str, tuple[str, ...]]:
    counts: Counter[str] = Counter()
    order: list[str] = []
    for s in segments:
        overlap = min(end, s.end) - max(start, s.start)
        if overlap > 0:
            counts[s.doc_id] += overlap
            order.append(s.doc_id)
    best = max(order, key=lambda d: (counts[d], -order.index(d)))  # 글자 수, 동률이면 앞 조항
    return best, tuple(order)


def _make(prefix: str, n: int, text: str, rep: str, template: Chunk, covered: tuple[str, ...]) -> StreamChunk:
    chunk = Chunk(
        chunk_id=f"{prefix}-{n:04d}",
        doc_id=rep,
        domain=template.domain,
        doc_type=rep.split("-")[1],
        title="",
        text=text.strip(),
        part=n,
    )
    return StreamChunk(chunk, covered)


def fixed_length_chunks(
    articles: Sequence[Chunk], *, size: int = 200, overlap: int = 50, prefix: str = "FIXED"
) -> list[StreamChunk]:
    """글자 수로 자른다. 조항 경계를 보지 않는다 — 그게 비교 대상이다.

    `size=200` 은 조항 길이 중앙값(121자)과 최대(311자) 사이에서 잡은 값이다. **골든셋으로 고르지 않았다.**
    """
    if not articles:
        return []
    if not 0 <= overlap < size:
        raise ValueError(f"overlap 은 0 이상 size 미만이어야 한다: {overlap} / {size}")
    text, segments = _stream(articles)
    out: list[StreamChunk] = []
    step = size - overlap
    for n, start in enumerate(range(0, len(text), step)):
        end = min(start + size, len(text))
        piece = text[start:end]
        if piece.strip():
            rep, covered = _ownership(segments, start, end)
            out.append(_make(prefix, n, piece, rep, articles[0], covered))
        if end == len(text):
            break
    return out


_SENTENCE = re.compile(r"[^.!?。\n]+(?:[.!?。]+|\n+|$)")


def split_sentences(text: str) -> list[tuple[int, int]]:
    """문장 구간. 마침표·물음표·줄바꿈에서 끊는다(한국어 조문은 목록형 줄바꿈이 많다)."""
    return [(m.start(), m.end()) for m in _SENTENCE.finditer(text) if text[m.start() : m.end()].strip()]


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def semantic_breakpoints(vectors: Sequence[Sequence[float]], *, percentile: float = 90.0) -> list[int]:
    """인접 문장 간 거리(1 − 코사인)가 **이 글 안에서** 상위 `100−percentile`% 인 자리에서 끊는다.

    LangChain `SemanticChunker` 의 percentile 방식과 같은 발상이다. 절대 임계값을 쓰지 않는 이유:
    임베딩 모델마다 코사인 분포가 달라 고정값은 모델을 바꾸면 의미가 사라진다.
    `90` 은 **골든셋으로 고르지 않은 값이다.** 반환값은 «이 인덱스의 문장부터 새 청크» 목록.
    """
    if len(vectors) < 2:
        return []
    distances = [1 - _cosine(vectors[i], vectors[i + 1]) for i in range(len(vectors) - 1)]
    ordered = sorted(distances)
    rank = (percentile / 100) * (len(ordered) - 1)
    lo, hi = math.floor(rank), math.ceil(rank)
    threshold = ordered[lo] + (ordered[hi] - ordered[lo]) * (rank - lo)
    return [i + 1 for i, d in enumerate(distances) if d > threshold]


def semantic_chunks(
    articles: Sequence[Chunk],
    sentence_vectors: Sequence[Sequence[float]],
    *,
    percentile: float = 90.0,
    max_chars: int = 400,
    prefix: str = "SEMANTIC",
) -> list[StreamChunk]:
    """문장 임베딩이 크게 달라지는 자리에서 자른다. `sentence_vectors` 는 `semantic_sentences()` 순서와 같아야 한다.

    `max_chars` 를 넘으면 의미 경계가 아니어도 자른다 — 기본 전략의 상한(400)과 같게 둬서 청크 크기가 교란 변수가 되지 않게 한다.
    """
    if not articles:
        return []
    text, segments = _stream(articles)
    spans = split_sentences(text)
    if len(spans) != len(sentence_vectors):
        raise ValueError(f"문장 {len(spans)}개 ≠ 벡터 {len(sentence_vectors)}개")
    breaks = set(semantic_breakpoints(sentence_vectors, percentile=percentile))

    out: list[StreamChunk] = []
    cur_start = spans[0][0] if spans else 0
    cur_end = cur_start
    for i, (s, e) in enumerate(spans):
        if i > 0 and (i in breaks or e - cur_start > max_chars):
            rep, covered = _ownership(segments, cur_start, cur_end)
            out.append(_make(prefix, len(out), text[cur_start:cur_end], rep, articles[0], covered))
            cur_start = s
        cur_end = e
    if cur_end > cur_start:
        rep, covered = _ownership(segments, cur_start, cur_end)
        out.append(_make(prefix, len(out), text[cur_start:cur_end], rep, articles[0], covered))
    return out


def semantic_sentences(articles: Sequence[Chunk]) -> list[str]:
    """시멘틱 청킹이 임베딩할 문장 목록(adapter 가 이것을 임베딩해 `semantic_chunks` 에 넘긴다)."""
    text, _ = _stream(articles)
    return [text[s:e].strip() for s, e in split_sentences(text)]


def article_stream_chunks(articles: Sequence[Chunk]) -> list[StreamChunk]:
    """기본 전략(1 조항 = 1 청크)을 같은 형태로 — 대조표의 기준 줄."""
    return [StreamChunk(a, (a.doc_id,)) for a in articles]
