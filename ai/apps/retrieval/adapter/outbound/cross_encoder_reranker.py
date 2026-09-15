# Requirement: B-3
"""리랭킹 — 앞 단계 검색의 상위 후보를 크로스 인코더로 다시 세운다 (`w4-reranker`).

    발화 ─▶ inner.retrieve(top=candidates) ─▶ scorer.score(발화, 후보들) ─▶ reorder ─▶ top_k

**겨냥하는 것은 MRR 이다.** 2026-09-09 실측이 Recall@5 0.833 · MRR 0.659 — 찾기는 하는데 1위에 못 올린다.

⚠ **Recall@5 가 변하는지는 `candidates` 에 달렸다.** `candidates == top_k` 면 같은 5건을 다시 세울 뿐이라
Recall@5 가 변하면 버그다(티켓 완료 조건). `candidates > top_k` 면 6위 이하가 5위 안으로 들어올 수 있어
**변하는 게 정상**이다. 둘을 섞어 적지 않는다.

모델 로더(`BgeRerankerScorer`)는 이 파일 아래쪽에 있다 — torch 는 생성할 때만 import 한다.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Protocol, Sequence

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc
from hub.app.ports.output.retrieval_port import RetrievalPort

from retrieval.domain.services.rerank import reorder


class PairScorer(Protocol):
    model_name: str

    def score(self, query: str, passages: Sequence[str]) -> list[float]: ...


class CrossEncoderReranker(RetrievalPort):
    def __init__(self, inner: RetrievalPort, scorer: PairScorer, *, candidates: int = 20) -> None:
        self._inner = inner
        self._scorer = scorer
        self._candidates = candidates

    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        if not utterance.strip():
            return []
        docs = await self._inner.retrieve(utterance, top_k=max(self._candidates, top_k))
        if not docs:
            return []
        passages = [f"{d.title}\n{d.snippet}" for d in docs]
        scores = await asyncio.to_thread(self._scorer.score, utterance, passages)
        return [
            RetrievedDoc(doc_id=d.doc_id, title=d.title, snippet=d.snippet, score=s)
            for d, s in reorder(docs, scores)[:top_k]
        ]


class BgeRerankerScorer:
    """`BAAI/bge-reranker-v2-m3` 크로스 인코더(시퀀스 분류 헤드 1개 — 로짓이 곧 관련도).

    받는 법: `huggingface_hub.snapshot_download("BAAI/bge-reranker-v2-m3", local_dir="models/bge-reranker-v2-m3")`.
    ⚠ **`decisions/010` 에 없는 모델이다** — 010 은 리랭커를 고르지 않았다. 채택하면 결정 기록을 쓴다.
    """

    def __init__(
        self, model_dir: str | Path, *, device: str | None = None, max_length: int = 512, batch_size: int = 16
    ) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        model_dir = Path(model_dir)
        if not (model_dir / "config.json").exists():
            raise FileNotFoundError(f"리랭커 모델이 없다: {model_dir}")
        self._torch = torch
        self.device = device or "cpu"
        self._tok = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval().to(self.device)
        self._max_length = max_length
        self._batch_size = batch_size
        self.model_name = model_dir.name

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        out: list[float] = []
        for i in range(0, len(passages), self._batch_size):
            batch = list(passages[i : i + self._batch_size])
            enc = self._tok(
                [query] * len(batch), batch, padding=True, truncation=True,
                max_length=self._max_length, return_tensors="pt",
            ).to(self.device)
            with self._torch.no_grad():
                logits = self._model(**enc).logits.view(-1).float()
            out.extend(logits.cpu().tolist())
        return out
