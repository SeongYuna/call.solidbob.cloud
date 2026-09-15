# Requirement: B-2
"""청킹 비교 전략 — 대표 조항 ID 규칙을 고정한다 (`w4-chunking-compare`)."""

from __future__ import annotations

import pytest

from retrieval.domain.services.chunking_strategies import (
    article_stream_chunks,
    fixed_length_chunks,
    semantic_breakpoints,
    semantic_chunks,
    semantic_sentences,
    split_sentences,
)
from retrieval.domain.value_objects.chunk import Chunk


def art(doc_id: str, title: str, text: str) -> Chunk:
    return Chunk(chunk_id=doc_id, doc_id=doc_id, domain="dasan", doc_type=doc_id.split("-")[1], title=title, text=text)


A = art("DASAN-TERM-1.1", "목적", "가" * 30)
B = art("DASAN-TERM-1.2", "정의", "나" * 90)
C = art("DASAN-MANUAL-2.1", "응대", "다" * 10)


class TestFixed:
    def test_representative_is_article_with_most_chars(self):
        # 스트림: "목적\n"+가30+"\n\n"(35) · "정의\n"+나90+"\n\n"(95) · ...
        chunks = fixed_length_chunks([A, B, C], size=60, overlap=0)
        first = chunks[0]
        assert first.covered_doc_ids == ("DASAN-TERM-1.1", "DASAN-TERM-1.2")
        assert first.chunk.doc_id == "DASAN-TERM-1.1"  # 35자 vs 25자
        assert chunks[1].chunk.doc_id == "DASAN-TERM-1.2"

    def test_tie_goes_to_earlier_article(self):
        a = art("DASAN-TERM-1.1", "", "가" * 8)   # "\n"+8+"\n\n" = 11
        b = art("DASAN-TERM-1.2", "", "나" * 8)
        chunk = fixed_length_chunks([a, b], size=22, overlap=0)[0]
        assert chunk.chunk.doc_id == "DASAN-TERM-1.1"

    def test_doc_type_follows_representative(self):
        chunks = fixed_length_chunks([A, B, C], size=500, overlap=0)
        assert chunks[0].chunk.doc_type == "TERM"

    def test_overlap_windows_and_unique_ids(self):
        chunks = fixed_length_chunks([A, B, C], size=60, overlap=20)
        ids = [c.chunk.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))
        assert all(len(c.chunk.text) <= 60 for c in chunks)

    def test_bad_overlap(self):
        with pytest.raises(ValueError):
            fixed_length_chunks([A], size=10, overlap=10)


class TestSemantic:
    def test_breakpoints_at_largest_jumps(self):
        vecs = [[1, 0], [1, 0.01], [0, 1], [0.01, 1]]  # 1→2 사이만 크게 벌어진다
        assert semantic_breakpoints(vecs, percentile=50) == [2]

    def test_sentences_split_on_period_and_newline(self):
        text = "첫 문장입니다. 둘째 문장\n셋째"
        assert [text[s:e].strip() for s, e in split_sentences(text)] == ["첫 문장입니다.", "둘째 문장", "셋째"]

    def test_chunks_cut_where_vectors_jump_and_carry_representative(self):
        a = art("DASAN-TERM-1.1", "등본", "등본 발급. 신분증 필요.")
        b = art("DASAN-TERM-1.2", "버스", "버스 노선. 환승 안내.")
        sentences = semantic_sentences([a, b])
        vecs = [[1, 0] if i < 3 else [0, 1] for i in range(len(sentences))]
        chunks = semantic_chunks([a, b], vecs, percentile=50)
        assert [c.chunk.doc_id for c in chunks] == ["DASAN-TERM-1.1", "DASAN-TERM-1.2"]

    def test_vector_count_must_match(self):
        with pytest.raises(ValueError):
            semantic_chunks([A], [[1.0]] * 99)

    def test_max_chars_forces_cut(self):
        long = art("DASAN-TERM-1.1", "t", ". ".join(["문장" * 10] * 10))
        sentences = semantic_sentences([long])
        chunks = semantic_chunks([long], [[1, 0]] * len(sentences), max_chars=100)
        assert len(chunks) > 1 and all(len(c.chunk.text) <= 100 for c in chunks)


def test_article_strategy_is_identity():
    assert [c.covered_doc_ids for c in article_stream_chunks([A, B])] == [("DASAN-TERM-1.1",), ("DASAN-TERM-1.2",)]
