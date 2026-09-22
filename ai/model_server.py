# Requirement: B-2, B-3, B-4, C-5, SEC-2
"""모델 HTTP 표면의 **합성 루트** — GPU 인스턴스에서 도는 별도 프로세스(`decisions/213`).

    cd ai && uvicorn --factory model_server:create_app --host 0.0.0.0 --port 8100 --no-access-log

`provider.py` 가 `server/main.py` 를 위한 합성 루트라면 이 파일은 **모델 쪽 프로세스**를 위한 것이다.
`model_serving`(HTTP 표면)과 `pii_ner`·`retrieval`·`generation`(모델 어댑터)을 **둘 다 아는 유일한 곳**이라
`apps/` 밖에 둔다(`.importlinter` 계약 2). **`server/` 는 이 파일도 `model_serving` 도 import 하지 않는다** —
`ai/tests/test_model_server.py` 가 검사한다.

## 설정 — 서버와 같은 이름을 쓴다

`server/core/config.py` 와 **같은 변수명**을 쓴다. 같은 모델을 가리키는데 이름이 둘이면 한쪽만 고쳐지는 일이 생긴다.

| 변수 | 켜는 것 | 비면 |
|---|---|---|
| `MODEL_SERVICE_TOKEN` | `/v1/*` 인증 | **전부 503**(fail-closed) — `/health` 만 연다 |
| `PII_NER_MODEL_DIR` | `/v1/ner/spans` | 503 `model_not_loaded` |
| `RETRIEVAL_EMBED_MODEL_DIR` | `/v1/embeddings` | 〃 |
| `RETRIEVAL_RERANK_MODEL_DIR` | `/v1/rerank` | 〃 |
| `OLLAMA_URL` + `GENERATION_MODEL` | `/v1/generation/cards` — **둘 다 있어야** | 〃 |
| `MODEL_DEVICE` | `cpu`(기본) · `cuda` · `mps` — 임베딩·리랭커만 | 자동 선택하지 않는다(측정값의 장치가 흔들리지 않게) |
| `GENERATION_TOP_N` | 생성할 상위 조항 수(기본 1, `decisions/207`) | |

모델 하나가 못 떠도 **프로세스는 뜬다** — 그 자리만 503 이 된다. 이유는 `/health` 의 `reason` 에 **예외 유형만** 남긴다(경로 없음).
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

_AI = Path(__file__).resolve().parent
for _p in (_AI / "apps", _AI.parent / "server" / "apps", _AI):  # pytest.ini pythonpath 와 같은 셋
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from model_serving.adapter.inbound.http_app import create_http_app  # noqa: E402
from model_serving.app.ports import ModelRegistry, ModelSlot  # noqa: E402

log = logging.getLogger(__name__)


def _env(env: Mapping[str, str], key: str) -> str | None:
    v = (env.get(key) or "").strip()
    return v or None


def _load(name: str, build: Callable[[], Any]) -> ModelSlot[Any]:
    try:
        return ModelSlot(impl=build(), reason="")
    except Exception as e:  # noqa: BLE001 — 한 모델이 못 떠도 나머지는 연다
        log.warning("%s 모델을 싣지 못했다: %s", name, type(e).__name__)
        return ModelSlot(impl=None, reason=f"load_failed:{type(e).__name__}")


class _NamedGenerator:
    """`DocumentListCardAdapter` 에 `model_name` 을 붙인다(어댑터 자체는 채팅 클라이언트만 이름을 안다)."""

    def __init__(self, inner: Any, model_name: str) -> None:
        self._inner = inner
        self.model_name = model_name

    @property
    def last_details(self) -> list[Any]:
        return self._inner.last_details

    async def to_cards(self, utterance: str, docs: list[Any]) -> list[Any]:
        return await self._inner.to_cards(utterance, docs)


def build_registry(env: Mapping[str, str]) -> ModelRegistry:
    """환경변수 → 실린 모델. 테스트는 모델 디렉터리를 비운 env 로 부른다(가중치를 읽지 않는다)."""
    device = _env(env, "MODEL_DEVICE")
    reg = ModelRegistry()

    if ner_dir := _env(env, "PII_NER_MODEL_DIR"):

        def ner() -> Any:
            from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger
            from pii_ner.adapter.outbound.ner_span_detector import NerSpanDetector

            return NerSpanDetector(KoElectraNerTagger(ner_dir))  # NER 은 CPU 고정(어댑터 주석 — 11~14ms)

        reg.ner = _load("ner", ner)

    if embed_dir := _env(env, "RETRIEVAL_EMBED_MODEL_DIR"):

        def embed() -> Any:
            from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder

            return KoE5Embedder(embed_dir, device=device)

        reg.embedding = _load("embedding", embed)

    if rerank_dir := _env(env, "RETRIEVAL_RERANK_MODEL_DIR"):

        def rerank() -> Any:
            from retrieval.adapter.outbound.cross_encoder_reranker import BgeRerankerScorer

            return BgeRerankerScorer(rerank_dir, device=device)

        reg.rerank = _load("rerank", rerank)

    ollama_url, gen_model = _env(env, "OLLAMA_URL"), _env(env, "GENERATION_MODEL")
    if ollama_url and gen_model:
        top_n = int(_env(env, "GENERATION_TOP_N") or 1)

        def gen() -> Any:
            from provider import build_generation_provider  # 서버와 같은 구성(스키마 강제 여부 포함)을 한 곳에서

            return _NamedGenerator(build_generation_provider(ollama_url, model=gen_model, generate_top_n=top_n)(), gen_model)

        reg.generation = _load("generation", gen)
    elif ollama_url or gen_model:
        reg.generation = ModelSlot(impl=None, reason="not_configured:needs_OLLAMA_URL_and_GENERATION_MODEL")

    return reg


def create_app(env: Mapping[str, str] | None = None) -> Any:
    env = os.environ if env is None else env
    return create_http_app(build_registry(env), token=_env(env, "MODEL_SERVICE_TOKEN"))
