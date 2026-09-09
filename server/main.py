# Requirement: [Task 1] FastAPI 앱 골격, SEC-2
"""CallGuard FastAPI 코어 — 엔트리포인트 = 합성 루트.

실행 (server/ 에서):
    uvicorn main:app --reload --env-file ../.env

이 파일은 앱을 조립만 한다. 라우터는 각 앱의 adapter/inbound/api/v1/ 에, 파이프라인 배선은 hub 에 둔다
(docs/architecture.md). 스포크 구현체는 여기서 `app.dependency_overrides[<hub 프로바이더>] = <스포크 프로바이더>`
로 꽂는다 — 허브는 스포크를 import 하지 않고(계약 5), 이 파일만 양쪽을 안다. 스포크는 아직 0개다.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# apps/ 를 경로에 올려 각 앱(hub·evaluation·<스포크>)을 최상위 패키지로 인식시킨다.
# pytest.ini(pythonpath)·.importlinter(PYTHONPATH=apps) 와 같은 맥락 — 세 곳이 항상 같아야 한다.
sys.path.insert(0, str(Path(__file__).resolve().parent / "apps"))

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from core.config import Settings, load_settings  # noqa: E402
from hub.adapter.inbound.api.v1.card_feedback_router import card_feedback_router  # noqa: E402
from hub.adapter.inbound.api.v1.closure_router import closure_router  # noqa: E402
from hub.adapter.inbound.api.v1.compliance_router import compliance_router  # noqa: E402
from hub.adapter.inbound.api.v1.knowledge_gap_query_router import (  # noqa: E402
    knowledge_gap_query_router,
)
from hub.adapter.inbound.api.v1.knowledge_gap_router import knowledge_gap_router  # noqa: E402
from hub.adapter.inbound.api.v1.myself_router import myself_router  # noqa: E402
from hub.adapter.inbound.api.v1.postcall_router import postcall_router  # noqa: E402
from hub.adapter.inbound.api.v1.recommendation_router import recommendation_router  # noqa: E402
from hub.adapter.inbound.api.v1.search_router import search_router  # noqa: E402
from hub.adapter.inbound.api.v1.transcript_ingest_router import transcript_ingest_router  # noqa: E402
from hub.adapter.inbound.api.v1.transcript_query_router import transcript_query_router  # noqa: E402

SPOKES: list[str] = []  # 스포크를 꽂을 때 이름을 추가한다 — /health 가 그대로 보고한다

# `server/` 안에 사는 규칙 기반 스포크. 프로바이더 기본값이라 조건 없이 붙는다.
_BUILTIN_SPOKES = ("masking", "closure_gate")

AI_APPS = Path(__file__).resolve().parent.parent / "ai" / "apps"


def _wire_retrieval(app: FastAPI, settings: Settings) -> str | None:
    """`ai/` 의 검색 구현(B-2)을 꽂는다. 꽂았으면 이름을, 못 꽂았으면 None.

    **왜 여기서 꽂나.** `hub` 는 스포크를 import 하지 않는다(`.importlinter` 계약 2 —
    `server → ai` 금지). 이 파일은 **합성 루트**라 계약 대상이 아니고, 양쪽을 아는 유일한
    지점이다. `scripts/run_eval.py` 가 평가 경로에 대해 하는 일을 여기서 요청 경로에 대해 한다.

    **`ai/` 는 서비스가 아니라 라이브러리다** — `ai/requirements.txt` 에 웹 프레임워크가 없고
    HTTP 표면도 없다. 그래서 HTTP 로 부르지 않고 같은 프로세스에서 쓴다.
    근거·되돌리는 법: `_project/decisions/024`.

    **못 꽂으면 조용히 501 로 남는다** — 임시 구현을 만들지 않는다. `ai/` 의존성이 없는
    환경(server CI)에서도 이 파일이 import 돼야 하므로 실패를 예외로 올리지 않는다.
    다만 `/health` 의 `spokes` 가 비어 있어 밖에서 구분할 수 있다.
    """
    if not settings.elasticsearch_configured:
        return None

    sys.path.insert(0, str(AI_APPS))
    try:
        from elasticsearch import Elasticsearch  # noqa: PLC0415
        from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever  # noqa: PLC0415
        from retrieval.adapter.outbound.es_index import SINGLE_INDEX  # noqa: PLC0415
    except ModuleNotFoundError:
        # ai/ 를 함께 배포하지 않았거나 elasticsearch 패키지가 없다.
        return None

    from hub.dependencies.retrieval_provider import get_retrieval_port  # noqa: PLC0415

    # 기동 시 ping 하지 않는다 — ES 가 잠깐 내려갔다고 서버가 못 뜨면 자막·마스킹까지 멈춘다.
    # 붙지 못하면 검색 요청에서 실패하고, 그건 "등록 안 됨(501)"과 구분되는 정직한 오류다.
    client = (
        Elasticsearch(settings.elasticsearch_url, api_key=settings.elasticsearch_api_key)
        if settings.elasticsearch_api_key
        else Elasticsearch(settings.elasticsearch_url)
    )
    port = EsBm25Retriever(client, index=SINGLE_INDEX)
    app.dependency_overrides[get_retrieval_port] = lambda: port
    return "retrieval"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings

    SPOKES.clear()
    SPOKES.extend(_BUILTIN_SPOKES)
    wired = _wire_retrieval(app, settings)
    if wired:
        SPOKES.append(wired)
    yield


app = FastAPI(
    title="CallGuard Core",
    summary="실시간 상담원 어시스트 RAG — FastAPI 코어",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 는 미들웨어라 기동 전에 붙어야 한다(Starlette 는 시작 뒤 add_middleware 를 거부한다).
# 그래서 lifespan 의 settings 를 기다리지 않고 여기서 한 번 더 읽는다 — 이 값 하나만이다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(load_settings().cors_allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(card_feedback_router)
app.include_router(closure_router)
app.include_router(compliance_router)
app.include_router(knowledge_gap_query_router)
app.include_router(knowledge_gap_router)
app.include_router(myself_router)
app.include_router(postcall_router)
app.include_router(recommendation_router)
app.include_router(search_router)
app.include_router(transcript_ingest_router)
app.include_router(transcript_query_router)


@app.get("/health")
def health(request: Request) -> dict:
    """기동 여부 + 외부 자원 설정 여부 + 등록된 스포크. 설정 '값'은 절대 싣지 않는다 (SEC-2)."""
    settings: Settings = request.app.state.settings
    return {
        "status": "ok",
        "postgres_configured": settings.postgres_configured,
        "elasticsearch_configured": settings.elasticsearch_configured,
        "spokes": list(SPOKES),
    }
