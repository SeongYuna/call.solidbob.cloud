# Requirement: B-2, B-3, B-6, QUA-1
"""HTTP 표면: retrieval 스포크가 없으면 501 (빈 목록으로 통과시키지 않음), 있으면 계약 형태로 응답."""

from fastapi.testclient import TestClient

from hub.app.dtos import RetrievedDoc
from hub.app.ports.output import RetrievalPort
from hub.dependencies.retrieval_provider import get_retrieval_port
from main import app

DOCS = [
    RetrievedDoc(doc_id="SHOP-TERM-4.1", title="반품 배송비 부담", snippet="단순 변심은 고객 부담", score=0.91),
    RetrievedDoc(doc_id="SHOP-TERM-4.2", title="교환 절차", snippet="…", score=0.55),
]


class _StubRetrieval(RetrievalPort):
    async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
        return DOCS[:top_k]


def test_스포크가_없으면_501이다():
    """빈 목록으로 200 을 돌려주면 '검색이 죽은 것'과 '관련 문서 없음'(B-6)이 구분되지 않는다."""
    with TestClient(app) as client:
        r = client.post("/hub/search", json={"utterance": "반품 배송비"})
    assert r.status_code == 501


def test_스포크가_있으면_계약_형태로_돌려준다():
    app.dependency_overrides[get_retrieval_port] = lambda: _StubRetrieval()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "반품 배송비", "top_k": 2})
        assert r.status_code == 200
        body = r.json()
        assert body["query"] == "반품 배송비"
        assert [d["doc_id"] for d in body["docs"]] == ["SHOP-TERM-4.1", "SHOP-TERM-4.2"]
        # 출처(doc_id)는 항상 있어야 한다 — 근거 없는 결과를 내지 않는다 (B-6)
        assert all(d["doc_id"] for d in body["docs"])
    finally:
        app.dependency_overrides.clear()


def test_top_k를_그대로_반영한다():
    app.dependency_overrides[get_retrieval_port] = lambda: _StubRetrieval()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "반품", "top_k": 1})
        assert len(r.json()["docs"]) == 1
    finally:
        app.dependency_overrides.clear()


def test_빈_검색어는_422다():
    """스포크를 꽂은 상태에서 본다 — 미등록이면 의존성 해석이 먼저라 입력과 무관하게 501 이 난다."""
    app.dependency_overrides[get_retrieval_port] = lambda: _StubRetrieval()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": ""})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_범위를_벗어난_top_k는_422다():
    app.dependency_overrides[get_retrieval_port] = lambda: _StubRetrieval()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "카드", "top_k": 999})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_스포크_미등록이면_입력이_잘못돼도_501이다():
    """의존성이 먼저 해석되므로 501 이 422 보다 앞선다. 구현이 없다는 사실이 먼저 알려진다."""
    with TestClient(app) as client:
        r = client.post("/hub/search", json={"utterance": ""})
    assert r.status_code == 501


def test_수동_검색은_전용_포트를_쓴다_자동_추천과_갈라져_있다():
    """`decisions/135` — 합성 루트가 수동 검색에만 B-6 기권을 씌운다. 그 자리가 실제로 갈라져 있는지 본다.

    수동 QA Q-44(`ㅁㄴㅇㄹ` 에도 결과 4건)의 고침이 여기에 기댄다.
    """
    from hub.dependencies.search_provider import get_search_retrieval_port

    class _Abstains(RetrievalPort):
        async def retrieve(self, utterance: str, top_k: int = 5) -> list[RetrievedDoc]:
            return []

    app.dependency_overrides[get_retrieval_port] = lambda: _StubRetrieval()
    app.dependency_overrides[get_search_retrieval_port] = lambda: _Abstains()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "ㅁㄴㅇㄹ"})
        assert r.status_code == 200 and r.json()["docs"] == []  # 「관련 문서 없음」
    finally:
        app.dependency_overrides.clear()


def test_전용_포트를_안_꽂으면_자동_추천과_같은_포트를_쓴다():
    """이행기·테스트·BM25 단독 구성에서 오늘까지의 동작 그대로여야 한다."""
    app.dependency_overrides[get_retrieval_port] = lambda: _StubRetrieval()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/search", json={"utterance": "반품 배송비", "top_k": 1})
        assert r.status_code == 200 and [d["doc_id"] for d in r.json()["docs"]] == ["SHOP-TERM-4.1"]
    finally:
        app.dependency_overrides.clear()
