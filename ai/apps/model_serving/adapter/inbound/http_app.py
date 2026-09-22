# Requirement: B-2, B-3, B-4, C-5, SEC-1, SEC-2
"""모델 HTTP 표면 — FastAPI 앱 팩토리(`decisions/213`).

    GET  /health                 인증 없음. 상태만(모델별 loaded·reason, 인증 locked|unconfigured)
    POST /v1/ner/spans           C-5  P6·P7 구간 — 마스킹 판정·가린 텍스트는 돌려주지 않는다
    POST /v1/embeddings          B-2  KoE5 벡터 (query | passage 접두어는 여기서 붙인다)
    POST /v1/rerank              B-3  크로스 인코더 점수 (입력 순서 그대로)
    POST /v1/generation/cards    B-4  서류 목록 카드 + 조항별 outcome

## 오류 계약 — 조용한 빈 결과를 내지 않는다

부르는 쪽(서버 원격 어댑터)이 **규칙·BM25·스니펫으로 내려갈지**를 상태 코드만 보고 정할 수 있어야 한다(`decisions/121` 4번).
본문은 전부 `{"code": ..., "model"?: ..., "reason"?: ...}` 한 모양이다.

| 상태 | code | 뜻 |
|---|---|---|
| 401 | `unauthorized` | `Authorization: Bearer` 가 없거나 틀렸다 |
| 503 | `auth_not_configured` | 표면에 토큰(`MODEL_SERVICE_TOKEN`)이 없다 — **fail-closed**, 아무것도 추론하지 않는다 |
| 503 | `model_not_loaded` | 그 모델이 안 실렸다 (`reason`: `not_configured` · `load_failed:<예외 유형>`) |
| 503 | `model_unavailable` | 생성을 시도한 조항이 **전부** 백엔드(Ollama) 오류였다 — 스니펫 카드로 채워 200 을 주지 않는다 |
| 500 | `inference_failed` | 추론 중 예외 (`reason`: 예외 **유형**만) |
| 422 | `invalid_request` | 모양·길이 상한 위반 (`fields`: 어느 필드인지만 — 입력값은 되돌려주지 않는다) |

## SEC-1 — 원문이 로그·응답 오류에 남지 않는다

- 요청 본문을 찍는 미들웨어를 두지 않는다. 실패 로그는 예외 **유형**만.
- FastAPI 기본 422 는 `input` 에 **요청 값을 그대로 되돌려준다** — 발화가 서버 쪽 오류 로그로 새어 나간다.
  그래서 핸들러를 바꿔 필드 위치만 준다.
- uvicorn 접근 로그는 메서드·경로·상태만 찍는다(본문 없음). 그래도 운영은 `--no-access-log` 를 권한다(`decisions/213`).
"""

from __future__ import annotations

import asyncio
import hmac
import logging
import threading
import time
from typing import Any, Callable

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from hub.app.dtos.retrieved_doc_dto import RetrievedDoc

from ...app.ports import ModelRegistry, ModelSlot
from .schemas import (
    CardOut,
    CardSource,
    EmbeddingRequest,
    EmbeddingResponse,
    GenerationRequest,
    GenerationResponse,
    NerRequest,
    NerResponse,
    Outcome,
    RerankRequest,
    RerankResponse,
    Span,
)

log = logging.getLogger(__name__)


class SurfaceError(Exception):
    def __init__(self, status: int, code: str, **extra: Any) -> None:
        super().__init__(code)
        self.status = status
        self.body = {"code": code, **extra}


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


def create_http_app(registry: ModelRegistry, *, token: str | None) -> FastAPI:
    """`token` 이 비면 `/v1/*` 전부 503(`auth_not_configured`). 환경변수는 여기서 읽지 않는다 — 합성 루트가 넘긴다."""
    app = FastAPI(title="CallGuard model surface", docs_url=None, redoc_url=None, openapi_url=None)
    expected = token.encode() if token else None
    # torch 모델은 스레드 안전을 보장하지 않는다 — 모델마다 한 번에 하나(런북 14-1 NUM_PARALLEL=1 과 같은 취지)
    locks = {name: threading.Lock() for name in registry.slots()}
    gen_lock = asyncio.Lock()

    @app.exception_handler(SurfaceError)
    async def _surface_error(_: Request, exc: SurfaceError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return JSONResponse(exc.body, status_code=exc.status, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [".".join(str(p) for p in e.get("loc", ())) for e in exc.errors()]
        return JSONResponse({"code": "invalid_request", "fields": fields}, status_code=422)

    def require_service_token(request: Request) -> None:
        if expected is None:
            raise SurfaceError(503, "auth_not_configured")
        header = request.headers.get("authorization", "")
        scheme, _, value = header.partition(" ")
        # 바이트 비교 — 비-ASCII 헤더에서 compare_digest(str) 가 TypeError(→500) 를 내지 않게(`decisions/120` 과 같다)
        if scheme.lower() != "bearer" or not hmac.compare_digest(value.strip().encode("utf-8", "surrogateescape"), expected):
            raise SurfaceError(401, "unauthorized")

    def loaded(name: str) -> Any:
        slot: ModelSlot[Any] = registry.slots()[name]
        if slot.impl is None:
            raise SurfaceError(503, "model_not_loaded", model=name, reason=slot.reason)
        return slot.impl

    async def run(name: str, fn: Callable[[], Any]) -> Any:
        def locked() -> Any:
            with locks[name]:
                return fn()

        try:
            return await asyncio.to_thread(locked)
        except SurfaceError:
            raise
        except Exception as e:  # noqa: BLE001 — 원문을 싣지 않고 유형만(SEC-1)
            log.warning("%s 추론 실패: %s", name, type(e).__name__)
            raise SurfaceError(500, "inference_failed", model=name, reason=type(e).__name__) from None

    guard = [Depends(require_service_token)]

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "auth": "locked" if expected else "unconfigured",
            "models": {
                name: {"loaded": s.loaded, **({"model": s.impl.model_name} if s.loaded else {"reason": s.reason})}
                for name, s in registry.slots().items()
            },
        }

    @app.post("/v1/ner/spans", dependencies=guard, response_model=NerResponse)
    async def ner_spans(req: NerRequest) -> NerResponse:
        ner = loaded("ner")
        t0 = time.perf_counter()
        spans = await run("ner", lambda: list(ner.spans(req.text)))
        return NerResponse(
            model=ner.model_name,
            spans=[Span(pattern=s.pattern, start=s.start, end=s.end) for s in spans],
            elapsed_ms=_ms(t0),
        )

    @app.post("/v1/embeddings", dependencies=guard, response_model=EmbeddingResponse)
    async def embeddings(req: EmbeddingRequest) -> EmbeddingResponse:
        emb = loaded("embedding")
        t0 = time.perf_counter()

        def call() -> tuple[list[list[float]], int]:
            before = emb.truncated
            fn = emb.embed_queries if req.kind == "query" else emb.embed_passages
            vectors = fn(req.texts)
            return vectors, emb.truncated - before

        vectors, truncated = await run("embedding", call)
        return EmbeddingResponse(
            model=emb.model_name, dims=emb.dims, vectors=vectors, truncated=truncated, elapsed_ms=_ms(t0)
        )

    @app.post("/v1/rerank", dependencies=guard, response_model=RerankResponse)
    async def rerank(req: RerankRequest) -> RerankResponse:
        scorer = loaded("rerank")
        t0 = time.perf_counter()
        scores = await run("rerank", lambda: list(scorer.score(req.query, req.passages)))
        if len(scores) != len(req.passages):
            raise SurfaceError(500, "inference_failed", model="rerank", reason="score_count_mismatch")
        return RerankResponse(model=scorer.model_name, scores=scores, elapsed_ms=_ms(t0))

    @app.post("/v1/generation/cards", dependencies=guard, response_model=GenerationResponse)
    async def generation_cards(req: GenerationRequest) -> GenerationResponse:
        gen = loaded("generation")
        t0 = time.perf_counter()
        docs = [RetrievedDoc(doc_id=d.doc_id, title=d.title, snippet=d.snippet, score=d.score) for d in req.docs]
        async with gen_lock:  # last_details 가 인스턴스 상태라 요청끼리 섞이지 않게
            try:
                cards = await gen.to_cards(req.utterance, docs)
            except Exception as e:  # noqa: BLE001
                log.warning("generation 실패: %s", type(e).__name__)
                raise SurfaceError(500, "inference_failed", model="generation", reason=type(e).__name__) from None
            outcomes = [Outcome(doc_id=d.doc_id, outcome=d.outcome) for d in gen.last_details]
        if outcomes and all(o.outcome == "error" for o in outcomes):
            # 어댑터는 이때 스니펫 카드로 채워 준다. 그걸 200 으로 내면 「생성이 죽었다」가 밖에서 안 보인다
            raise SurfaceError(503, "model_unavailable", model="generation", reason="generation_backend_error")
        return GenerationResponse(
            model=gen.model_name,
            cards=[
                CardOut(
                    title=c.title,
                    summary=c.summary,
                    source=CardSource(doc_id=c.source.doc_id, title=c.source.title),
                    similarity_score=c.similarity_score,
                )
                for c in cards
            ],
            outcomes=outcomes,
            elapsed_ms=_ms(t0),
        )

    return app
