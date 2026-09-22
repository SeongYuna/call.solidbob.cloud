# Requirement: B-2, B-3, B-4, C-5
"""요청·응답 모양(pydantic). 길이 상한을 둔다 — 한 요청이 GPU 를 오래 붙잡으면 다른 통화의 발화가 줄을 선다."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MAX_TEXT = 2000  # 발화·조항 한 건 (글자)
MAX_ITEMS = 64  # 임베딩 한 번에
MAX_PASSAGES = 50  # 리랭킹 후보
MAX_DOCS = 10  # 카드 생성 조항


class NerRequest(BaseModel):
    text: str = Field(max_length=MAX_TEXT)


class Span(BaseModel):
    pattern: str
    start: int
    end: int


class NerResponse(BaseModel):
    model: str
    spans: list[Span]
    elapsed_ms: float


class EmbeddingRequest(BaseModel):
    kind: Literal["query", "passage"]
    texts: list[str] = Field(min_length=1, max_length=MAX_ITEMS)


class EmbeddingResponse(BaseModel):
    model: str
    dims: int
    vectors: list[list[float]]
    truncated: int  # 이 요청에서 상한(512 토큰)을 넘어 잘린 입력 수
    elapsed_ms: float


class RerankRequest(BaseModel):
    query: str = Field(max_length=MAX_TEXT)
    passages: list[str] = Field(min_length=1, max_length=MAX_PASSAGES)


class RerankResponse(BaseModel):
    model: str
    scores: list[float]  # passages 와 같은 순서
    elapsed_ms: float


class Doc(BaseModel):
    doc_id: str
    title: str
    snippet: str = Field(max_length=MAX_TEXT * 2)
    score: float


class GenerationRequest(BaseModel):
    utterance: str = Field(max_length=MAX_TEXT)
    docs: list[Doc] = Field(max_length=MAX_DOCS)


class CardSource(BaseModel):
    doc_id: str
    title: str


class CardOut(BaseModel):
    title: str
    summary: str
    source: CardSource
    similarity_score: float


class Outcome(BaseModel):
    doc_id: str
    outcome: str  # "generated" | "none" | "no_grounded_items" | "error"


class GenerationResponse(BaseModel):
    model: str
    cards: list[CardOut]  # 비어 있으면 「관련 문서 없음」(B-6) — docs 가 비었을 때만 그렇다
    outcomes: list[Outcome]  # 생성을 시도한 조항별 결과. 원출력은 싣지 않는다
    elapsed_ms: float
