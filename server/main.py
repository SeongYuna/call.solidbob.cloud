# Requirement: [Task 1] FastAPI 앱 골격, SEC-2
"""CallGuard FastAPI 코어 — 엔트리포인트 = 합성 루트.

실행 (server/ 에서):
    uvicorn main:app --reload --env-file ../.env

이 파일은 앱을 조립만 한다. 라우터는 각 앱의 adapter/inbound/api/v1/ 에, 파이프라인 배선은 hub 에 둔다
(docs/architecture.md). 스포크 구현체는 여기서 `app.dependency_overrides[<hub 프로바이더>] = <스포크 프로바이더>`
로 꽂는다 — 허브는 스포크를 import 하지 않고(계약 5), 이 파일만 양쪽을 안다.
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

from admin_auth.adapter.inbound.api.v1.auth_router import auth_router  # noqa: E402
from agent_auth.adapter.inbound.api.v1.agent_token_router import agent_token_router  # noqa: E402
from core.config import Settings, load_settings  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_decision_router import blacklist_decision_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_entry_list_router import blacklist_entry_list_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_expiry_change_list_router import blacklist_expiry_change_list_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_expiry_change_router import blacklist_expiry_change_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_release_router import blacklist_release_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_retention_purge_router import blacklist_retention_purge_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_request_create_router import blacklist_request_create_router  # noqa: E402
from hub.adapter.inbound.api.v1.blacklist_request_list_router import blacklist_request_list_router  # noqa: E402
from hub.adapter.inbound.api.v1.call_guard_check_router import call_guard_check_router  # noqa: E402
from hub.adapter.inbound.api.v1.call_guard_flag_list_router import call_guard_flag_list_router  # noqa: E402
from hub.adapter.inbound.api.v1.call_list_router import call_list_router  # noqa: E402
from hub.adapter.inbound.api.v1.call_record_router import call_record_router  # noqa: E402
from hub.adapter.inbound.api.v1.call_start_router import call_start_router  # noqa: E402
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
from hub.adapter.inbound.api.v1.required_docs_detection_router import required_docs_detection_router  # noqa: E402
from hub.adapter.inbound.api.v1.routing_decision_router import routing_decision_router  # noqa: E402
from hub.adapter.inbound.api.v1.routing_setting_query_router import routing_setting_query_router  # noqa: E402
from hub.adapter.inbound.api.v1.routing_setting_router import routing_setting_router  # noqa: E402
from hub.adapter.inbound.api.v1.search_router import search_router  # noqa: E402
from hub.adapter.inbound.api.v1.summary_confirmation_router import summary_confirmation_router  # noqa: E402
from hub.adapter.inbound.api.v1.summary_revision_list_router import summary_revision_list_router  # noqa: E402
from hub.adapter.inbound.api.v1.summary_revision_router import summary_revision_router  # noqa: E402
from hub.adapter.inbound.api.v1.transcript_ingest_router import transcript_ingest_router  # noqa: E402
from hub.adapter.inbound.api.v1.transcript_query_router import transcript_query_router  # noqa: E402
from hub.adapter.inbound.api.v1.upload_router import upload_router  # noqa: E402

SPOKES: list[str] = []  # 스포크를 꽂을 때 이름을 추가한다 — /health 가 그대로 보고한다

# `server/` 안에 사는 규칙 기반 스포크. 프로바이더 기본값이라 조건 없이 붙는다.
_BUILTIN_SPOKES = ("masking", "closure_gate", "postcall")

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
    # 임베딩·리랭킹(decisions/206)은 모델 디렉터리가 설정됐을 때만. 못 뜨면 BM25 그대로다.
    # 켜진 층은 `/health` 에 따로 싣는다 — 같은 "retrieval" 이라도 BM25 인지 dense+rerank 인지 밖에서 보여야 한다.
    app.state.retrieval_layers = []
    if settings.retrieval_embed_model_dir:
        sys.path.insert(0, str(AI_APPS.parent))
        try:
            from provider import build_model_retriever  # noqa: PLC0415

            port, app.state.retrieval_layers = build_model_retriever(
                client,
                index=SINGLE_INDEX,
                embed_model_dir=settings.retrieval_embed_model_dir,
                rerank_model_dir=settings.retrieval_rerank_model_dir,
            )
        except (ModuleNotFoundError, ImportError):
            pass
    # 기동 전에 이미 꽂힌 것(테스트 스텁 등)은 덮지 않는다 — lifespan 은 빈 자리만 채운다.
    app.dependency_overrides.setdefault(get_retrieval_port, lambda: port)
    return "retrieval"


def _wire_trigger(app: FastAPI) -> str | None:
    """`ai/` 의 트리거 판정(B-1)을 꽂는다. 꽂았으면 이름을, 못 꽂았으면 None.

    검색과 달리 외부 자원이 없어 설정 조건이 없다. `ai/provider.py` 의 팩토리를 그대로 쓴다 —
    구현 선택(지금은 `IsFinalTrigger` v1)은 `ai/` 몫이고 여기는 꽂기만 한다.

    ⚠ 발동 시각(`trigger_at_ms`)은 **모형값**이다 — 이벤트 도착 시각이 계약에 없어
    "발화 종료 + 346ms(V4 실측)" 로 채운다. 발동 여부 판정은 진짜다. 평가 하네스는 이 포트를
    일부러 꽂지 않는다(절대 원칙 10). `ai/apps/retrieval/adapter/outbound/is_final_trigger.py` 참고.
    """
    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))  # `ai/provider.py` 를 `provider` 로 import
    try:
        from provider import build_trigger_provider  # noqa: PLC0415
    except ModuleNotFoundError:
        return None  # ai/ 를 함께 배포하지 않았다 — 501 로 남는다

    from hub.dependencies.trigger_provider import get_trigger_port  # noqa: PLC0415

    app.dependency_overrides.setdefault(get_trigger_port, build_trigger_provider())
    return "trigger"


def _wire_uploads(app: FastAPI, settings: Settings) -> str | None:
    """테스트 음성 보관(A-6)의 S3 어댑터를 꽂는다. 꽂았으면 이름을, 못 꽂았으면 None.

    **버킷과 토큰이 둘 다 있어야 꽂는다.** 하나만 있으면 반쪽이다 — 버킷만 있으면 문이 없고,
    토큰만 있으면 올릴 곳이 없다. 안 꽂히면 `get_upload_storage_port` 가 501 로 남는다.

    자격증명은 여기서 다루지 않는다. boto3 기본 체인이 EC2 인스턴스 역할을 IMDSv2 로 가져온다 —
    2026-09-14 운영 파드에서 확인했다(`역할: callguard-ec2-role`). `_project/decisions/110`.
    """
    if not settings.uploads_configured:
        return None

    try:
        from hub.adapter.outbound.s3.s3_upload_storage_adapter import (  # noqa: PLC0415
            S3UploadStorageAdapter,
        )
    except ModuleNotFoundError:
        # boto3 가 없는 환경(경량 CI 설치 목록)에서도 이 파일은 import 돼야 한다.
        return None

    from hub.dependencies.upload_provider import get_upload_storage_port  # noqa: PLC0415

    # 기동 시 버킷에 접근해 보지 않는다 — S3 가 잠깐 안 되는 것과 «설정 안 됨» 은 다른 문제이고,
    # 여기서 막으면 전사·마스킹까지 못 뜬다(`_wire_retrieval` 과 같은 원칙).
    adapter = S3UploadStorageAdapter(bucket=settings.s3_bucket, region=settings.aws_region)
    app.dependency_overrides.setdefault(get_upload_storage_port, lambda: adapter)
    return "uploads"


def _wire_call_guard(app: FastAPI) -> str | None:
    """`ai/` 의 콜 가드 탐지(C-6)를 꽂는다. 꽂았으면 이름을, 못 꽂았으면 None.

    트리거와 같다 — 규칙 사전뿐이라 설정 조건이 없고, 구현 선택(`RuleCallGuardAdapter` v1)은 `ai/` 몫이다.
    못 꽂으면 `POST /hub/call-guard-checks` 가 501 로 남는다(빈 목록을 "폭언 없음"으로 돌려주지 않는다).
    """
    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))
    try:
        from provider import build_call_guard_provider  # noqa: PLC0415
    except (ModuleNotFoundError, ImportError):
        return None

    from hub.dependencies.call_guard_provider import get_call_guard_port  # noqa: PLC0415

    app.dependency_overrides.setdefault(get_call_guard_port, build_call_guard_provider())
    return "call_guard"


def _wire_pii_ner(app: FastAPI, settings: Settings) -> str | None:
    """C-5 — 규칙 마스킹(`server/apps/masking`) 위에 `ai/` 의 NER(P6·P7)을 **한 겹 더** 얹는다.

    **규칙을 대체하지 않는다.** `ai/provider.py` 가 규칙 어댑터를 폴백으로 받아 두 결과의 합집합을
    가린다 — 모델이 추론 중 실패해도 규칙 결과는 나간다. `PII_NER_MODEL_DIR` 이 비었거나 torch·모델이
    없으면 **아무것도 바꾸지 않고** 기본 프로바이더(규칙)가 그대로 돈다. 그래서 켜졌을 때만 이름을 돌려준다 —
    `/health` 에 `pii_ner` 가 없으면 P6·P7 은 규칙 폴백뿐이라는 뜻이다.

    ⚠ 모델 로드·예열이 기동 시간에 1초 남짓 더해진다(2026-09-15 로컬 CPU 실측). 요청당 추론은 10ms 대다.
    """
    if not settings.pii_ner_model_dir:
        return None

    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))
    try:
        from provider import build_masking_provider  # noqa: PLC0415
    except (ModuleNotFoundError, ImportError):
        return None

    from hub.dependencies.masking_provider import get_masking_port  # noqa: PLC0415
    from masking.adapter.outbound.rule_masking_adapter import RuleMaskingAdapter  # noqa: PLC0415

    provider, ner_enabled = build_masking_provider(
        RuleMaskingAdapter(), ner_model_dir=settings.pii_ner_model_dir
    )
    if not ner_enabled:
        return None
    app.dependency_overrides.setdefault(get_masking_port, provider)
    return "pii_ner"


def _wire_generation(app: FastAPI, settings: Settings) -> str | None:
    """B-4 — `ai/` 의 서류 목록 카드 생성을 꽂는다(`decisions/207`). 꽂았으면 이름을, 아니면 None.

    **`OLLAMA_URL` 과 `GENERATION_MODEL` 이 둘 다 있어야** 켠다. 안 켜면 기본 프로바이더(스니펫 카드)가 그대로 돈다 —
    지어내지 않는 정식 폴백이다. 기동 시 Ollama 에 붙어 보지 않는다: 생성이 실패하면 카드마다 스니펫으로 내려가므로
    추천이 멈추지 않는다(`DocumentListCardAdapter`). ⚠ 켜면 추천 한 번에 모델 호출 1회(상위 1건)만큼 지연이 는다 —
    로컬 실측 p95 0.9~1.0초(2026-09-15), 운영 T4 미측정.
    """
    if not (settings.ollama_url and settings.generation_model):
        return None
    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))
    try:
        from provider import build_generation_provider  # noqa: PLC0415
    except (ModuleNotFoundError, ImportError):
        return None

    from hub.dependencies.generation_provider import get_generation_port  # noqa: PLC0415

    app.dependency_overrides.setdefault(
        get_generation_port, build_generation_provider(settings.ollama_url, model=settings.generation_model)
    )
    return "generation"


def _wire_postcall_model(app: FastAPI, settings: Settings) -> str | None:
    """D-1 모델 요약 · D-2 유형 제안을 규칙 발췌 초안(`decisions/306`) **위에** 얹는다(`w7-postcall-spoke`).

    **생성과 같은 스위치다** — `OLLAMA_URL` 과 `GENERATION_MODEL` 이 둘 다 있어야 켠다. 검색 스포크가 꽂혀 있으면 D-2 에 쓴다.
    안 켜면 규칙 초안(유형 None)이 그대로다. 요약·유형은 전부 **초안**이고 `confirmed` 는 False 다.
    """
    if not (settings.ollama_url and settings.generation_model):
        return None
    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))
    try:
        from provider import build_postcall_provider  # noqa: PLC0415
    except (ModuleNotFoundError, ImportError):
        return None

    from hub.dependencies.postcall_provider import get_postcall_port  # noqa: PLC0415
    from hub.dependencies.retrieval_provider import get_retrieval_port  # noqa: PLC0415
    from postcall.adapter.outbound.rule_postcall_adapter import RulePostcallAdapter  # noqa: PLC0415

    retrieval_factory = app.dependency_overrides.get(get_retrieval_port)
    app.dependency_overrides.setdefault(
        get_postcall_port,
        build_postcall_provider(
            RulePostcallAdapter(),
            ollama_url=settings.ollama_url,
            model=settings.generation_model,
            retrieval=retrieval_factory() if retrieval_factory else None,
        ),
    )
    return "postcall_model"


def _wire_compliance(app: FastAPI) -> str | None:
    """`ai/` 의 컴플라이언스 탐지(C-1~C-4)를 꽂는다. 콜 가드와 같다 — 규칙표뿐이라 설정 조건이 없다.

    못 꽂으면 `POST /hub/compliance-checks` 가 501 로 남는다(빈 목록을 「위반 없음」으로 돌려주지 않는다).
    """
    sys.path.insert(0, str(AI_APPS))
    sys.path.insert(0, str(AI_APPS.parent))
    try:
        from provider import build_compliance_provider  # noqa: PLC0415
    except (ModuleNotFoundError, ImportError):
        return None

    from hub.dependencies.compliance_provider import get_compliance_port  # noqa: PLC0415

    app.dependency_overrides.setdefault(get_compliance_port, build_compliance_provider())
    return "compliance"


def _install_missing_index_handler(app: FastAPI) -> None:
    """ES 인덱스가 없거나 ES 에 연결하지 못할 때 500 대신 **503 + 이유**를 돌려준다.

    운영 ES 에 지식베이스가 적재되지 않은 채로 검색 스포크가 꽂히면 `/hub/search`·
    `/hub/recommendations` 가 `index_not_found_exception` 으로 500 이 났다(2026-09-08~09 실측).
    500 은 "코드가 틀렸다"로 읽히지만 실제로는 "적재가 안 됐다"이고, 고치는 사람이 다르다.
    기동 시 ping 으로 미리 막지 않는 이유는 `_wire_retrieval` 주석과 같다 — ES 가 잠깐
    내려갔다고 마스킹까지 멈추면 안 된다.
    """
    try:
        from elasticsearch import NotFoundError  # noqa: PLC0415
    except ModuleNotFoundError:
        return

    from fastapi.responses import JSONResponse  # noqa: PLC0415

    async def _handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "검색 인덱스가 없다 — 지식베이스를 적재해야 한다 "
                               "(scripts/index_knowledge_base.py --to-es). "
                               f"ES: {getattr(exc, 'message', str(exc))}"},
        )

    app.add_exception_handler(NotFoundError, _handler)

    # ES 에 **연결 자체를** 못 할 때도 같다(2026-09-14, `w4-es-unreachable-503`) — 로컬에 ES 가 없거나
    # 파드가 내려가 있으면 500 이었다. 인덱스 없음과 달리 고칠 곳은 적재가 아니라 ES 기동이다.
    # 예외 메시지에는 ES 주소가 들어 있어 본문에 싣지 않는다(SEC-2).
    from elasticsearch import ConnectionError as EsConnectionError  # noqa: PLC0415
    from elasticsearch import ConnectionTimeout as EsConnectionTimeout  # noqa: PLC0415

    async def _unreachable(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "검색 엔진(Elasticsearch)에 연결하지 못했다 — ES 가 떠 있는지 확인해야 한다 "
                               f"({type(exc).__name__})"},
        )

    app.add_exception_handler(EsConnectionError, _unreachable)
    app.add_exception_handler(EsConnectionTimeout, _unreachable)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    app.state.settings = settings

    SPOKES.clear()
    SPOKES.extend(_BUILTIN_SPOKES)
    for wired in (
        _wire_retrieval(app, settings),
        _wire_trigger(app),
        _wire_call_guard(app),
        _wire_compliance(app),
        _wire_pii_ner(app, settings),
        _wire_generation(app, settings),
        _wire_postcall_model(app, settings),
        _wire_uploads(app, settings),
    ):
        if wired:
            SPOKES.append(wired)
    SPOKES.extend(getattr(app.state, "retrieval_layers", ()))
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
_install_missing_index_handler(app)

app.include_router(auth_router)
app.include_router(agent_token_router)
app.include_router(blacklist_decision_router)
app.include_router(blacklist_entry_list_router)
app.include_router(blacklist_expiry_change_router)
app.include_router(blacklist_expiry_change_list_router)
app.include_router(blacklist_release_router)
app.include_router(blacklist_retention_purge_router)
app.include_router(blacklist_request_create_router)
app.include_router(blacklist_request_list_router)
app.include_router(call_guard_check_router)
app.include_router(call_guard_flag_list_router)
app.include_router(call_list_router)
app.include_router(call_record_router)
app.include_router(call_start_router)
app.include_router(card_feedback_router)
app.include_router(closure_router)
app.include_router(compliance_router)
app.include_router(knowledge_gap_query_router)
app.include_router(knowledge_gap_router)
app.include_router(myself_router)
app.include_router(postcall_router)
app.include_router(summary_confirmation_router)
app.include_router(summary_revision_router)
app.include_router(summary_revision_list_router)
app.include_router(recommendation_router)
app.include_router(required_docs_detection_router)
app.include_router(routing_decision_router)
app.include_router(routing_setting_router)
app.include_router(routing_setting_query_router)
app.include_router(search_router)
app.include_router(transcript_ingest_router)
app.include_router(transcript_query_router)
app.include_router(upload_router)


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
