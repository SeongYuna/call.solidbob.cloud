# Requirement: B-2, B-3, B-4, C-5
"""표면이 싣는 모델의 모양(Protocol)과 «실렸는가» 상태.

순수 파이썬이다 — 프레임워크·모델 라이브러리를 모른다(`.importlinter` 계약 3). 구현은 합성 루트
(`ai/model_server.py`)가 `pii_ner`·`retrieval`·`generation` 에서 골라 꽂는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, Sequence, TypeVar

from hub.app.dtos.recommendation_card_dto import Card
from hub.app.dtos.retrieved_doc_dto import RetrievedDoc


class SpanLike(Protocol):
    pattern: str  # "P6" | "P7"
    start: int
    end: int


class NerSpans(Protocol):
    """C-5 P6·P7 구간. **마스킹 판정이 아니다** — 구간만 준다(절대 원칙 9)."""

    model_name: str

    def spans(self, text: str) -> Sequence[SpanLike]: ...


class Embedder(Protocol):
    """B-2 KoE5. `truncated` 는 누적 잘림 수 — 요청 한 건의 몫은 표면이 차이로 센다."""

    model_name: str
    dims: int
    truncated: int

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]: ...


class PairScorer(Protocol):
    """B-3 크로스 인코더. 점수는 **입력 순서 그대로** — 다시 세우는 것은 부르는 쪽이다."""

    model_name: str

    def score(self, query: str, passages: Sequence[str]) -> list[float]: ...


class CardGenerator(Protocol):
    """B-4 서류 목록 카드. `last_details` 의 `outcome` 으로 생성이 실제로 됐는지 밖에서 구분한다."""

    model_name: str
    last_details: list[Any]

    async def to_cards(self, utterance: str, docs: list[RetrievedDoc]) -> list[Card]: ...


T = TypeVar("T")


@dataclass
class ModelSlot(Generic[T]):
    """모델 한 자리. `impl` 이 None 이면 **안 실렸다** — `reason` 이 그 이유(코드)다.

    `reason` 에 경로·원문을 넣지 않는다 — `/health` 로 나간다(SEC-2). `"not_configured"` · `"load_failed:OSError"` 식.
    """

    impl: T | None = None
    reason: str = "not_configured"

    @property
    def loaded(self) -> bool:
        return self.impl is not None


@dataclass
class ModelRegistry:
    ner: ModelSlot[NerSpans] = field(default_factory=ModelSlot)
    embedding: ModelSlot[Embedder] = field(default_factory=ModelSlot)
    rerank: ModelSlot[PairScorer] = field(default_factory=ModelSlot)
    generation: ModelSlot[CardGenerator] = field(default_factory=ModelSlot)

    def slots(self) -> dict[str, ModelSlot[Any]]:
        return {"ner": self.ner, "embedding": self.embedding, "rerank": self.rerank, "generation": self.generation}
