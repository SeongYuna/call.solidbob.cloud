# Requirement: B-1, B-2, B-6
"""스포크를 hub 포트에 꽂기 위한 팩토리. **이 파일은 `server/main.py` 를 위한 것이다.**

`server/` 는 `ai/` 를 import 할 수 없다(`server/.importlinter` 계약 2 — 두 서브도메인을 따로
배포하기 위한 경계다). 그 경계 밖에 있는 유일한 곳이 **합성 루트 `server/main.py`** 이고,
거기서 아래 팩토리를 불러 `dependency_overrides` 에 꽂는다.

    # server/main.py — sys.path 에 ai/apps 와 ai 를 함께 올린다
    from provider import build_retrieval_provider, build_trigger_provider
    from hub.dependencies.retrieval_provider import get_retrieval_port
    from hub.dependencies.trigger_provider import get_trigger_port

    if settings.elasticsearch_configured:
        app.dependency_overrides[get_retrieval_port] = build_retrieval_provider(
            settings.elasticsearch_url, api_key=settings.elasticsearch_api_key
        )
        SPOKES.append("retrieval")

    app.dependency_overrides[get_trigger_port] = build_trigger_provider()
    SPOKES.append("trigger")

    # B-0 도메인 라우팅은 2026-08-28 단일 도메인 전환으로 사라졌다(`decisions/201`).
    # 허브 포트(`DomainRoutingPort`)는 계약으로 남아 있지만 구현체가 없다 —
    # 기본값이 None 이라 501 이 아니고, 하네스는 "측정 불가"로 보고한다.

`sys.path` 에 **`ai/apps` 와 `ai` 둘 다** 올린다 — 앞의 것은 `retrieval`·`evaluation` 을 최상위
패키지로 보이게 하고, 뒤의 것은 이 파일 자체를 `provider` 로 import 하기 위해서다.
`main.py` 가 이미 `server/apps` 에 대해 하는 일과 같다.

**이 파일이 `apps/` 밖에 있는 이유**: 여러 스포크를 동시에 알아야 하는데, 스포크끼리 서로를
import 하면 `.importlinter` 계약 2(module-independence)가 깨진다.
합성은 계약 밖에서 한다 — `ai/tests/` 와 같은 자리다.

**설정은 인자로 받는다.** 여기서 `os.environ` 을 읽지 않는다 — `ai/` 에는 config 모듈이 없고,
서버의 설정은 `server/core/config.py` 한 곳에서만 읽는다는 규칙(`server/CLAUDE.md` 3번)을
스포크가 우회하면 안 된다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from hub.app.ports.output.call_guard_port import CallGuardPort
from hub.app.ports.output.compliance_port import CompliancePort
from hub.app.ports.output.generation_port import GenerationPort
from hub.app.ports.output.masking_port import MaskingPort
from hub.app.ports.output.postcall_port import PostcallPort
from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.ports.output.trigger_port import TriggerPort

from call_guard.adapter.outbound.rule_call_guard_adapter import RuleCallGuardAdapter
from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever
from retrieval.adapter.outbound.es_index import SINGLE_INDEX
from retrieval.adapter.outbound.is_final_trigger import IsFinalTrigger


def build_es_client(url: str, api_key: str | None = None) -> Any:
    """ES 클라이언트 하나. 요청마다 새로 만들지 않는다 — 연결 풀이 매번 버려진다."""
    if not url:
        raise ValueError("elasticsearch_url 이 비어 있다")
    try:
        from elasticsearch import Elasticsearch
    except ModuleNotFoundError as e:  # pragma: no cover - 설치 안내
        raise RuntimeError("elasticsearch 패키지가 없다: pip install -r ai/requirements.txt") from e

    return Elasticsearch(url, api_key=api_key) if api_key else Elasticsearch(url)


def build_retrieval_provider(
    url: str,
    *,
    api_key: str | None = None,
    index: str = SINGLE_INDEX,
    client: Any | None = None,
) -> Callable[[], RetrievalPort]:
    """`get_retrieval_port` 를 대체할 프로바이더.

    클라이언트를 **기동 시 한 번** 만들어 재사용한다. `client=` 로 갈아끼울 수 있어
    테스트에서 실제 ES 없이도 배선을 확인할 수 있다.

    ⚠ 동기 클라이언트를 쓰므로 `EsBm25Retriever` 가 `asyncio.to_thread` 로 감싼다.
    요청량이 늘면 `AsyncElasticsearch` 로 바꾸는 편이 낫다 — 그때 이 팩토리만 고치면 된다.
    """
    port = EsBm25Retriever(client or build_es_client(url, api_key), index=index)
    return lambda: port


def build_model_retriever(
    client: Any,
    *,
    index: str = SINGLE_INDEX,
    embed_model_dir: str | Path | None,
    rerank_model_dir: str | Path | None = None,
    rerank_candidates: int = 5,
    device: str | None = None,
    cache_size: int = 1024,
    no_answer_abstain: bool = False,
) -> tuple[RetrievalPort, list[str]]:
    """임베딩(+리랭킹) 검색 — **실측으로 고른 구성**을 만든다(`_project/decisions/206`).

        KoE5 kNN ─▶ (bge-reranker 후보 5) ─▶ 0건이면 BM25 로 내려감
                                           └▶ 1순위 < 0.67 이면 기권 — 카드 0장(B-6, decisions/215 · 리랭커 없을 때만)

    2026-09-15 실측(골든셋 v1-150, n96): BM25 0.833/0.659 · dense 0.979/0.885 · RRF 하이브리드 0.927/0.828 ·
    dense+리랭킹(후보 5) 0.979/0.919. **RRF 는 BM25 가 dense 를 끌어내려 채택하지 않았다.**

    돌려주는 두 번째 값은 실제로 켜진 층 이름이다 — `/health` 에 싣는다. 모델·torch 가 없으면 BM25 하나와
    빈 목록을 돌려준다(예외를 올리지 않는다 — 검색이 통째로 못 뜨는 것보다 BM25 가 낫다).
    """
    from retrieval.adapter.outbound.es_dense_retriever import EsDenseRetriever
    from retrieval.adapter.outbound.fallback_retriever import FallbackRetriever

    bm25 = EsBm25Retriever(client, index=index)
    if not embed_model_dir:
        return bm25, []
    try:
        from retrieval.adapter.outbound.koe5_embedder import KoE5Embedder

        primary: RetrievalPort = EsDenseRetriever(client, KoE5Embedder(embed_model_dir, device=device), index=index)
    except (ModuleNotFoundError, FileNotFoundError, OSError):
        return bm25, []
    layers = ["retrieval_dense"]

    if rerank_model_dir:
        try:
            from retrieval.adapter.outbound.cross_encoder_reranker import (
                BgeRerankerScorer,
                CrossEncoderReranker,
            )

            primary = CrossEncoderReranker(
                primary, BgeRerankerScorer(rerank_model_dir, device=device), candidates=rerank_candidates
            )
            layers.append("rerank")
        except (ModuleNotFoundError, FileNotFoundError, OSError):
            pass  # 리랭커만 못 뜨면 dense 까지는 쓴다
    # B-6 기권 문턱(`decisions/215`)은 dense 코사인 눈금으로 잰 값이라 **dense 가 1순위를 정할 때만** 건다.
    # 리랭커가 켜지면 1순위 점수가 로짓으로 바뀌어 이 값이 의미를 잃는다 — 그 구성의 문턱은 잰 적이 없으니 걸지 않는다.
    from retrieval.adapter.outbound.es_dense_retriever import NO_ANSWER_MIN_SCORE

    # ⚠ **기본은 꺼짐이다(2026-09-22, `decisions/215` 보류).** 채택 당일 E2E 24건에서 대화체 발화의 dense 1순위가
    # 0.60~0.67 에 몰려 발동 추천의 60%(114/189)가 기권했고 SYN-015·017 의 필요서류 절차가 사라졌다 — 운영(`server/main.py`)은
    # 기본값으로 부르므로 문턱이 걸리지 않는다. 장치(`FallbackRetriever(abstain_below=...)`)는 대화체 표본으로 다시 잴 때 켠다.
    abstain_below = NO_ANSWER_MIN_SCORE if (no_answer_abstain and "rerank" not in layers) else None
    port: RetrievalPort = FallbackRetriever(primary, bm25, abstain_below=abstain_below)
    if cache_size > 0:
        # 결과 캐시(`w7-lru-cache`) — 키는 발화 해시(SEC-1), 인덱스 UUID 가 바뀌면(--recreate 재적재) 비운다. BM25 단독에는 안 건다(p95 4ms 라 이득이 없다)
        from retrieval.adapter.outbound.cached_retriever import CachedRetriever, es_index_epoch

        port = CachedRetriever(port, maxsize=cache_size, epoch=es_index_epoch(client, index))
        layers.append("retrieval_cache")
    return port, layers


def build_trigger_provider(**kwargs: Any) -> Callable[[], TriggerPort]:
    """`get_trigger_port` 를 대체할 프로바이더. 규칙 계산뿐이라 외부 자원이 필요 없다.

    ⚠ `at_ms`(발동 시각)를 무엇으로 채우는지는 `IsFinalTrigger` 의 주석을 반드시 읽는다 —
    포트 시그니처에 도착 시각이 없어서 지금은 **실측 상수로 모형화**하고 있다.
    """
    port = IsFinalTrigger(**kwargs)
    return lambda: port


def build_masking_provider(
    fallback: MaskingPort,
    *,
    ner_model_dir: str | Path | None,
    tagger: Any | None = None,
) -> tuple[Callable[[], MaskingPort], bool]:
    """`get_masking_port` 를 대체할 프로바이더(C-5) — **규칙 마스킹 위에 NER(P6·P7)을 얹는다.**

    `fallback` 은 `server/apps/masking` 의 규칙 어댑터다. 여기서 import 하지 않고 받는 이유는
    `ai/` 가 `server/` 의 스포크를 직접 알면 안 되기 때문이다 — 합성 루트(`server/main.py`)가 넘긴다.

    **모델을 못 띄우면 예외를 올리지 않고 규칙만 쓴다.** 두 번째 값이 NER 이 실제로 켜졌는지다 —
    `/health` 가 `pii_ner` 를 보고할지 여기서 정한다. 조용히 규칙만 도는 상태를 밖에서 구분할 수 있어야 한다.
    """
    from pii_ner.adapter.outbound.layered_masking_adapter import LayeredMaskingAdapter

    if tagger is None and ner_model_dir:
        try:
            from pii_ner.adapter.outbound.koelectra_ner_tagger import KoElectraNerTagger

            tagger = KoElectraNerTagger(ner_model_dir)
        except (ModuleNotFoundError, FileNotFoundError, OSError):
            tagger = None
    port = LayeredMaskingAdapter(fallback, tagger)
    return (lambda: port), port.ner_enabled


def build_generation_provider(ollama_url: str, *, model: str, generate_top_n: int = 1) -> Callable[[], GenerationPort]:
    """`get_generation_port` 를 대체할 프로바이더(B-4 서류 목록, `decisions/207`).

    모델이 조항에서 서류 이름을 고르고 **규칙이 근거 대조**한다. 실패·「없음」·근거 없는 항목뿐이면 스니펫 카드로 내려간다.
    JSON 스키마 강제는 모델이 받을 때만 켠다 — kanana(Ollama 0.33.3)는 스키마 요청에 500 을 낸다(2026-09-15 실측).
    """
    from generation.adapter.outbound.document_list_card_adapter import DocumentListCardAdapter
    from generation.adapter.outbound.ollama_chat import OllamaChat

    use_schema = "kanana" not in model
    port = DocumentListCardAdapter(OllamaChat(ollama_url, model=model), generate_top_n=generate_top_n, use_schema=use_schema)
    return lambda: port


def build_compliance_provider() -> Callable[[], CompliancePort]:
    """`get_compliance_port` 를 대체할 프로바이더(C-1~C-4). 규칙표뿐이라 외부 자원이 필요 없다.

    ⚠ 규칙 v1 이다 — 명세는 KcELECTRA 분류기다(기획서 2.4절). 학습 데이터가 없어 먼저 두었다. 수치는 상한으로 읽는다(`w6-compliance-spoke`).
    """
    from compliance.adapter.outbound.rule_compliance_adapter import RuleComplianceAdapter

    port = RuleComplianceAdapter()
    return lambda: port


def build_postcall_provider(
    fallback: PostcallPort,
    *,
    ollama_url: str | None,
    model: str | None,
    retrieval: RetrievalPort | None,
) -> Callable[[], PostcallPort]:
    """`get_postcall_port` 를 대체할 프로바이더(D-1 모델 요약 · D-2 유형 제안, `w7-postcall-spoke`).

    `fallback` 은 `server/apps/postcall` 규칙 발췌 초안(`decisions/306`) — 합성 루트가 넘긴다. 모델·검색이 없거나 실패하면 그 초안이 그대로 나간다.
    D-3 후속조치는 규칙 초안 것을 쓴다(모델이 할 일을 지어내지 않게).
    """
    from postcall_summary.adapter.outbound.model_postcall_adapter import ModelPostcallAdapter

    chat = None
    if ollama_url and model:
        from generation.adapter.outbound.ollama_chat import OllamaChat

        chat = OllamaChat(ollama_url, model=model, num_predict=160, timeout_s=30)  # 통화 후 처리 — 실시간 예산 밖이라 길게 둔다
    port = ModelPostcallAdapter(fallback, chat=chat, retrieval=retrieval)
    return lambda: port


def build_call_guard_provider() -> Callable[[], CallGuardPort]:
    """`get_call_guard_port` 를 대체할 프로바이더(C-6). 규칙 사전뿐이라 외부 자원이 필요 없다.

    ⚠ 호출하는 쪽이 **마스킹된 고객 발화**를 넘겨야 한다 — 잡힌 `phrase` 가 그대로 저장된다(MANUAL-5.5).
    """
    port = RuleCallGuardAdapter()
    return lambda: port


def wrap_no_answer(port: RetrievalPort, layers: list[str]) -> RetrievalPort:
    """수동 검색(`POST /hub/search`)이 쓸 포트에 B-6 기권을 씌운다(`_project/decisions/135`).

    자동 추천은 **씌우지 않는다** — `decisions/215` 가 보류한 것이 그쪽이다. 여기서 거는 것은
    상담원이 직접 친 질의뿐이고, 문턱을 잰 보류 표본이 바로 그 모양이다.

    dense 가 1순위를 정할 때만 건다. 리랭커가 켜지면 점수가 로짓이라 이 눈금이 의미를 잃고,
    BM25 단독이면 raw 점수라 마찬가지다 — 그 구성의 문턱은 잰 적이 없으니 걸지 않는다.
    """
    if layers != ["retrieval_dense"]:
        return port
    from retrieval.adapter.outbound.abstaining_retriever import AbstainingRetriever
    from retrieval.adapter.outbound.es_dense_retriever import NO_ANSWER_MIN_SCORE

    return AbstainingRetriever(port, min_score=NO_ANSWER_MIN_SCORE)
