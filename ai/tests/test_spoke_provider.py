# Requirement: B-1, B-2, B-6
"""스포크 프로바이더 팩토리 — `server/main.py` 가 쓰는 배선 지점.

**여기가 `apps/` 밖인 이유**: 팩토리(`ai/provider.py`)가 여러 스포크를 동시에 아는
합성 지점이고, 그런 코드는 계약(module-independence) 밖에 있어야 한다. 팩토리 자체도 같은
이유로 2026-08-27 에 `retrieval/` 밖으로 옮겼다. `server/tests/` 가 `main.py` 에 대해 하는 역할과 같다.

실제 ES 없이 돈다 — 팩토리에 가짜 클라이언트를 넣어 **배선만** 확인한다.
"""

from __future__ import annotations

import asyncio

import pytest

from hub.app.ports.output.retrieval_port import RetrievalPort
from hub.app.ports.output.trigger_port import TriggerPort
from provider import (
    build_es_client,
    build_retrieval_provider,
    build_trigger_provider,
)


class FakeClient:
    def search(self, **kwargs):
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "DASAN-TERM-4.2",
                        "_score": 9.98,
                        "_source": {
                            "doc_id": "DASAN-TERM-4.2",
                            "title": "대리 신청 구비서류",
                            "text": "본문",
                        },
                    }
                ]
            }
        }


def test_검색_프로바이더가_포트를_돌려준다():
    provider = build_retrieval_provider("http://localhost:9200", client=FakeClient())
    assert isinstance(provider(), RetrievalPort)


def test_클라이언트를_기동_시_한_번만_만든다():
    """요청마다 새로 만들면 연결 풀이 매번 버려진다. 같은 인스턴스가 나와야 한다."""
    provider = build_retrieval_provider("http://localhost:9200", client=FakeClient())
    assert provider() is provider()


def test_검색_프로바이더가_실제로_검색한다():
    provider = build_retrieval_provider("http://localhost:9200", client=FakeClient())
    docs = asyncio.run(provider().retrieve("대리 신청 서류", top_k=5))
    assert [d.doc_id for d in docs] == ["DASAN-TERM-4.2"]


def test_인덱스를_바꿔_끼울_수_있다():
    """인덱스 이름을 팩토리 인자로 갈아끼울 수 있다 — decisions/017.

    ⚠ 2026-08-28 단일 도메인 전환(`decisions/201`) 이후 per-domain 레이아웃은 쓸 일이 없다.
    그래도 이 주입 지점은 남긴다 — dense_vector 를 얹은 새 인덱스로 옮길 때 같은 자리를 쓴다.
    """
    c = FakeClient()
    calls = []
    c.search = lambda **kw: (calls.append(kw), FakeClient().search(**kw))[1]
    provider = build_retrieval_provider("x", client=c, index="callguard-kb-v2")
    asyncio.run(provider().retrieve("구비서류"))
    assert calls[0]["index"] == "callguard-kb-v2"


def test_트리거_프로바이더가_포트를_돌려준다():
    assert isinstance(build_trigger_provider()(), TriggerPort)


def test_트리거도_인스턴스를_재사용한다():
    provider = build_trigger_provider()
    assert provider() is provider()


def test_트리거_프로바이더에_인자를_넘길_수_있다():
    port = build_trigger_provider(now_ms=lambda: 4200)()
    from hub.app.dtos.transcript_dto import TranscriptEvent

    decision = port.decide(
        TranscriptEvent(
            call_id="c", segment_id=1, speaker="customer", text="질문", is_final=True
        )
    )
    assert decision.at_ms == 4200


def test_빈_URL_은_거부한다():
    """설정이 비었는데 조용히 뜨면 런타임에 이유 없는 연결 실패로 나타난다."""
    with pytest.raises(ValueError):
        build_es_client("")


def test_콜_가드_프로바이더는_포트를_만족하고_위치를_채운다():
    """저장 경로(`call_guard_flag.span_*` NOT NULL)가 span 을 요구한다 — 어댑터가 채워야 한다."""
    from hub.app.ports.output.call_guard_port import CallGuardPort
    from provider import build_call_guard_provider

    port = build_call_guard_provider()()
    assert isinstance(port, CallGuardPort)
    flags = asyncio.run(port.detect("이런 병신 같은"))
    assert flags, "사전에 있는 욕설을 못 잡았다"
    assert all(f.span is not None and "이런 병신 같은"[f.span[0]:f.span[1]] == f.phrase for f in flags)


def test_model_retriever_without_embed_model_is_bm25():
    from provider import build_model_retriever
    from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever

    port, layers = build_model_retriever(FakeClient(), embed_model_dir=None)
    assert isinstance(port, EsBm25Retriever) and layers == []


def test_model_retriever_missing_model_falls_back_to_bm25(tmp_path):
    """모델 디렉터리가 틀려도 서버는 뜬다 — 검색이 통째로 못 뜨는 것보다 BM25 가 낫다(decisions/206)."""
    from provider import build_model_retriever
    from retrieval.adapter.outbound.es_bm25_retriever import EsBm25Retriever

    port, layers = build_model_retriever(
        FakeClient(), embed_model_dir=tmp_path / "없음", rerank_model_dir=tmp_path / "없음"
    )
    assert isinstance(port, EsBm25Retriever) and layers == []


def _fake_model_modules(monkeypatch):
    """KoE5·리랭커 모듈을 가짜로 바꾼다 — 모델·torch 없이 **조립만** 본다."""
    import sys
    import types

    emb = types.ModuleType("retrieval.adapter.outbound.koe5_embedder")
    emb.KoE5Embedder = lambda *a, **k: object()
    monkeypatch.setitem(sys.modules, "retrieval.adapter.outbound.koe5_embedder", emb)
    import retrieval.adapter.outbound.cross_encoder_reranker as cer

    monkeypatch.setattr(cer, "BgeRerankerScorer", lambda *a, **k: object())


def _fallback_of(port):
    from retrieval.adapter.outbound.cached_retriever import CachedRetriever
    from retrieval.adapter.outbound.fallback_retriever import FallbackRetriever

    inner = port._inner if isinstance(port, CachedRetriever) else port
    assert isinstance(inner, FallbackRetriever)
    return inner


def test_threshold_is_off_by_default(monkeypatch, tmp_path):
    """B-6 기권 문턱은 보류다(decisions/215, 2026-09-22) — 운영(server/main.py)이 기본값으로 부르므로 꺼져 있어야 한다."""
    from provider import build_model_retriever

    _fake_model_modules(monkeypatch)
    port, layers = build_model_retriever(FakeClient(), embed_model_dir=tmp_path, cache_size=0)
    assert layers == ["retrieval_dense"]
    assert _fallback_of(port)._abstain_below is None


def test_dense_only_gets_no_answer_threshold_when_opted_in(monkeypatch, tmp_path):
    """켜면 dense 코사인 눈금으로 잰 값이라 dense 단독 구성에만 건다(decisions/215)."""
    from provider import build_model_retriever
    from retrieval.adapter.outbound.es_dense_retriever import NO_ANSWER_MIN_SCORE

    _fake_model_modules(monkeypatch)
    port, layers = build_model_retriever(FakeClient(), embed_model_dir=tmp_path, cache_size=0, no_answer_abstain=True)
    assert layers == ["retrieval_dense"]
    assert _fallback_of(port)._abstain_below == NO_ANSWER_MIN_SCORE == 0.67


def test_rerank_config_gets_no_threshold(monkeypatch, tmp_path):
    """리랭커가 1순위를 정하면 점수가 로짓이라 0.67 이 의미 없다 — 걸지 않는다."""
    from provider import build_model_retriever

    _fake_model_modules(monkeypatch)
    port, layers = build_model_retriever(
        FakeClient(), embed_model_dir=tmp_path, rerank_model_dir=tmp_path, cache_size=0, no_answer_abstain=True
    )
    assert layers == ["retrieval_dense", "rerank"]
    assert _fallback_of(port)._abstain_below is None


def test_measurement_can_turn_threshold_off(monkeypatch, tmp_path):
    from provider import build_model_retriever

    _fake_model_modules(monkeypatch)
    port, _ = build_model_retriever(FakeClient(), embed_model_dir=tmp_path, cache_size=0, no_answer_abstain=False)
    assert _fallback_of(port)._abstain_below is None
