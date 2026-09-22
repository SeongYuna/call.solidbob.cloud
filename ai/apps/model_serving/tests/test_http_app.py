# Requirement: B-2, B-3, B-4, C-5, SEC-1, SEC-2
"""모델 HTTP 표면 — 엔드포인트별 인증·미적재·정상 모양. **가짜 모델만 쓴다**(가중치를 읽지 않는다).

⚠ CI `ai` job 은 fastapi·httpx 를 설치하지 않는다(2026-09-22 `test.yml`) — 없으면 이 파일은 건너뛴다.
`decisions/213` 「남는 것」 참고.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from hub.app.dtos.recommendation_card_dto import Card, Source  # noqa: E402

from model_serving.adapter.inbound.http_app import create_http_app  # noqa: E402
from model_serving.app.ports import ModelRegistry, ModelSlot  # noqa: E402

TOKEN = "t-0123456789"
AUTH = {"Authorization": f"Bearer {TOKEN}"}


@dataclass(frozen=True)
class _Span:
    pattern: str
    start: int
    end: int


class FakeNer:
    model_name = "fake-ner"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def spans(self, text: str):
        if self.fail:
            raise RuntimeError(text)  # 원문을 예외에 실어도 응답·로그에 나가면 안 된다
        i = text.find("김민준")
        return [_Span("P6", i, i + 3)] if i >= 0 else []


class FakeEmbedder:
    model_name = "fake-koe5"
    dims = 3

    def __init__(self) -> None:
        self.truncated = 0
        self.calls: list[str] = []

    def embed_queries(self, texts):
        self.calls.append("query")
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_passages(self, texts):
        self.calls.append("passage")
        self.truncated += 1
        return [[0.0, 1.0, 0.0] for _ in texts]


class FakeScorer:
    model_name = "fake-reranker"

    def score(self, query, passages):
        return [float(len(p)) for p in passages]


@dataclass
class _Detail:
    doc_id: str
    outcome: str


class FakeGenerator:
    model_name = "fake-kanana"

    def __init__(self, outcome: str = "generated") -> None:
        self.outcome = outcome
        self.last_details: list[_Detail] = []

    async def to_cards(self, utterance, docs):
        self.last_details = [_Detail(d.doc_id, self.outcome) for d in docs[:1]]
        return [
            Card(title=d.title, summary="필요 서류: 신분증", source=Source(doc_id=d.doc_id, title=d.title), similarity_score=d.score)
            for d in docs
        ]


def full_registry(**over) -> ModelRegistry:
    reg = ModelRegistry(
        ner=ModelSlot(FakeNer(), ""),
        embedding=ModelSlot(FakeEmbedder(), ""),
        rerank=ModelSlot(FakeScorer(), ""),
        generation=ModelSlot(FakeGenerator(), ""),
    )
    for k, v in over.items():
        setattr(reg, k, v)
    return reg


def client(reg: ModelRegistry | None = None, token: str | None = TOKEN) -> TestClient:
    return TestClient(create_http_app(reg or full_registry(), token=token), raise_server_exceptions=False)


DOCS = [{"doc_id": "DASAN-MANUAL-3.1", "title": "전입신고", "snippet": "신분증을 지참한다", "score": 0.9}]
ENDPOINTS = [
    ("/v1/ner/spans", "ner", {"text": "제 이름은 김민준입니다"}),
    ("/v1/embeddings", "embedding", {"kind": "query", "texts": ["전입신고 서류"]}),
    ("/v1/rerank", "rerank", {"query": "전입신고", "passages": ["가", "나다"]}),
    ("/v1/generation/cards", "generation", {"utterance": "전입신고 뭐 가져가요", "docs": DOCS}),
]


# --- 인증 -------------------------------------------------------------------------------------


@pytest.mark.parametrize("path,_slot,body", ENDPOINTS)
def test_헤더가_없으면_401(path, _slot, body):
    r = client().post(path, json=body)
    assert r.status_code == 401
    assert r.json() == {"code": "unauthorized"}
    assert r.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header", [f"Bearer {TOKEN}x", f"Basic {TOKEN}", TOKEN, "Bearer ", "Bearer 토큰"]
)
def test_틀린_토큰은_401_비ASCII도_500이_아니다(header):
    r = client().post("/v1/ner/spans", json={"text": "x"}, headers={"Authorization": header.encode("utf-8")})
    assert r.status_code == 401


@pytest.mark.parametrize("path,_slot,body", ENDPOINTS)
@pytest.mark.parametrize("token", [None, ""])
def test_토큰이_설정되지_않으면_fail_closed(path, _slot, body, token):
    """토큰 없는 표면은 **올바른 척하는 헤더**가 와도 추론하지 않는다."""
    r = client(token=token).post(path, json=body, headers={"Authorization": "Bearer "})
    assert r.status_code == 503
    assert r.json() == {"code": "auth_not_configured"}


# --- 모델 미적재 → 503 (조용한 빈 결과 금지) ---------------------------------------------------


@pytest.mark.parametrize("path,slot,body", ENDPOINTS)
def test_모델이_안_실렸으면_503_과_이유(path, slot, body):
    reg = full_registry(**{slot: ModelSlot(None, "load_failed:OSError")})
    r = client(reg).post(path, json=body, headers=AUTH)
    assert r.status_code == 503
    assert r.json() == {"code": "model_not_loaded", "model": slot, "reason": "load_failed:OSError"}


def test_추론_예외는_500_이고_원문을_싣지_않는다(caplog):
    reg = full_registry(ner=ModelSlot(FakeNer(fail=True), ""))
    r = client(reg).post("/v1/ner/spans", json={"text": "제 이름은 김민준입니다"}, headers=AUTH)
    assert r.status_code == 500
    assert r.json() == {"code": "inference_failed", "model": "ner", "reason": "RuntimeError"}
    assert "김민준" not in r.text
    assert "김민준" not in caplog.text


def test_422_는_입력값을_되돌려주지_않는다():
    """FastAPI 기본 422 는 `input` 에 요청 값을 싣는다 — 발화가 부르는 쪽 오류 로그로 샌다(SEC-1)."""
    r = client().post("/v1/ner/spans", json={"text": "김민준" * 1000}, headers=AUTH)
    assert r.status_code == 422
    assert r.json() == {"code": "invalid_request", "fields": ["body.text"]}
    assert "김민준" not in r.text


# --- 정상 모양 --------------------------------------------------------------------------------


def test_ner_은_구간만_준다_가린_텍스트도_판정도_없다():
    r = client().post("/v1/ner/spans", json={"text": "제 이름은 김민준입니다"}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"model", "spans", "elapsed_ms"}
    assert body["model"] == "fake-ner"
    assert body["spans"] == [{"pattern": "P6", "start": 6, "end": 9}]
    assert "*" not in r.text  # 마스킹된 문자열을 돌려주지 않는다(절대 원칙 9 — 가리는 것은 규칙과 합친 서버다)


def test_ner_구간이_없으면_빈_목록_200():
    """모델이 **실렸고** 아무것도 못 찾은 것은 정상 빈 결과다 — 미적재(503)와 구분된다."""
    r = client().post("/v1/ner/spans", json={"text": "전입신고 하려고요"}, headers=AUTH)
    assert r.status_code == 200 and r.json()["spans"] == []


def test_임베딩_query_passage_갈라_부르고_잘림을_요청_단위로_센다():
    emb = FakeEmbedder()
    c = client(full_registry(embedding=ModelSlot(emb, "")))
    q = c.post("/v1/embeddings", json={"kind": "query", "texts": ["a", "b"]}, headers=AUTH).json()
    p = c.post("/v1/embeddings", json={"kind": "passage", "texts": ["a"]}, headers=AUTH).json()
    p2 = c.post("/v1/embeddings", json={"kind": "passage", "texts": ["a"]}, headers=AUTH).json()
    assert emb.calls == ["query", "passage", "passage"]
    assert q["dims"] == 3 and q["vectors"] == [[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]] and q["truncated"] == 0
    assert p["truncated"] == 1 and p2["truncated"] == 1  # 누적값이 아니라 이 요청의 몫


def test_임베딩_kind_가_틀리면_422():
    r = client().post("/v1/embeddings", json={"kind": "doc", "texts": ["a"]}, headers=AUTH)
    assert r.status_code == 422


def test_리랭크는_입력_순서_그대로_점수():
    r = client().post("/v1/rerank", json={"query": "q", "passages": ["가", "나다", "라"]}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["scores"] == [1.0, 2.0, 1.0]
    assert r.json()["model"] == "fake-reranker"


def test_생성_카드와_outcome():
    r = client().post("/v1/generation/cards", json={"utterance": "u", "docs": DOCS}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["cards"] == [
        {
            "title": "전입신고",
            "summary": "필요 서류: 신분증",
            "source": {"doc_id": "DASAN-MANUAL-3.1", "title": "전입신고"},
            "similarity_score": 0.9,
        }
    ]
    assert body["outcomes"] == [{"doc_id": "DASAN-MANUAL-3.1", "outcome": "generated"}]


def test_생성_문서가_없으면_빈_카드_B6():
    r = client().post("/v1/generation/cards", json={"utterance": "u", "docs": []}, headers=AUTH)
    assert r.status_code == 200 and r.json()["cards"] == [] and r.json()["outcomes"] == []


def test_생성이_전부_백엔드_오류면_503_스니펫으로_채우지_않는다():
    reg = full_registry(generation=ModelSlot(FakeGenerator(outcome="error"), ""))
    r = client(reg).post("/v1/generation/cards", json={"utterance": "u", "docs": DOCS}, headers=AUTH)
    assert r.status_code == 503
    assert r.json() == {"code": "model_unavailable", "model": "generation", "reason": "generation_backend_error"}


def test_생성_none_은_정상_응답이다():
    """모델이 「없음」이라 답한 것은 오류가 아니다 — 카드는 스니펫이고 outcome 이 그것을 말한다."""
    reg = full_registry(generation=ModelSlot(FakeGenerator(outcome="none"), ""))
    r = client(reg).post("/v1/generation/cards", json={"utterance": "u", "docs": DOCS}, headers=AUTH)
    assert r.status_code == 200 and r.json()["outcomes"][0]["outcome"] == "none"


# --- /health ----------------------------------------------------------------------------------


def test_health_는_인증_없이_상태만():
    reg = full_registry(rerank=ModelSlot(None, "not_configured"))
    r = client(reg).get("/health")
    assert r.status_code == 200
    assert r.json() == {
        "status": "ok",
        "auth": "locked",
        "models": {
            "ner": {"loaded": True, "model": "fake-ner"},
            "embedding": {"loaded": True, "model": "fake-koe5"},
            "rerank": {"loaded": False, "reason": "not_configured"},
            "generation": {"loaded": True, "model": "fake-kanana"},
        },
    }
    assert TOKEN not in r.text


def test_health_토큰이_없으면_unconfigured():
    assert client(token=None).get("/health").json()["auth"] == "unconfigured"


def test_문서_페이지를_열지_않는다():
    c = client()
    assert c.get("/docs").status_code == 404
    assert c.get("/openapi.json").status_code == 404
