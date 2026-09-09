# Requirement: B-1, B-2
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
