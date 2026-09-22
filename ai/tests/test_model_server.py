# Requirement: B-2, B-3, B-4, C-5, SEC-1, SEC-2
"""모델 HTTP 표면의 합성 루트(`ai/model_server.py`) — 배선 · 실제 소켓 왕복 · 의존 방향.

- 의존 방향 검사(server 가 이 표면을 import 하지 않는다)는 fastapi 없이 돌아야 해서 `test_dependency_direction.py` 로 뺐다.
- 왕복 테스트는 **uvicorn 을 진짜 포트에 띄우고 표준 라이브러리(`urllib`)로 부른다** — 장민석 님의 서버 원격 어댑터
  (`w6-server-remote-model-adapter`) 자리를 대신 선다. 모델은 가짜다.
- 실제 모델 스모크는 `@pytest.mark.slow` — `pytest -m slow -s tests/test_model_server.py` (`CALLGUARD_MODELS_DIR` 로 모델 경로를 바꾼다).
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# --- 아래는 fastapi·uvicorn 이 있을 때만 -------------------------------------------------------

fastapi = pytest.importorskip("fastapi")
uvicorn = pytest.importorskip("uvicorn")

import model_server  # noqa: E402
from model_serving.adapter.inbound.http_app import create_http_app  # noqa: E402
from model_serving.app.ports import ModelRegistry, ModelSlot  # noqa: E402


def test_env_가_비면_모두_미적재_토큰도_없다():
    app = model_server.create_app({})
    from fastapi.testclient import TestClient

    c = TestClient(app)
    h = c.get("/health").json()
    assert h["auth"] == "unconfigured"
    assert {k: v["loaded"] for k, v in h["models"].items()} == {
        "ner": False, "embedding": False, "rerank": False, "generation": False,
    }
    assert c.post("/v1/ner/spans", json={"text": "x"}).json() == {"code": "auth_not_configured"}


def test_모델_디렉터리가_틀리면_load_failed_유형만_남고_프로세스는_뜬다(tmp_path):
    reg = model_server.build_registry({"PII_NER_MODEL_DIR": str(tmp_path / "없음"), "RETRIEVAL_RERANK_MODEL_DIR": str(tmp_path)})
    for slot in (reg.ner, reg.rerank):
        assert not slot.loaded
        assert slot.reason.startswith("load_failed:")
        assert str(tmp_path) not in slot.reason  # 경로를 /health 로 내보내지 않는다


def test_생성은_URL_과_모델명이_둘_다_있어야_켜진다():
    reg = model_server.build_registry({"OLLAMA_URL": "http://127.0.0.1:9"})
    assert not reg.generation.loaded and reg.generation.reason.startswith("not_configured")
    reg = model_server.build_registry({"OLLAMA_URL": "http://127.0.0.1:9", "GENERATION_MODEL": "kanana-1.5-2.1b-instruct:q4_k_m"})
    assert reg.generation.loaded and reg.generation.impl.model_name == "kanana-1.5-2.1b-instruct:q4_k_m"


def test_생성_백엔드가_꺼져_있으면_503_model_unavailable():
    """Ollama 가 없는 주소 — 어댑터는 스니펫 카드로 내려가지만 표면은 그것을 200 으로 숨기지 않는다."""
    from fastapi.testclient import TestClient

    app = model_server.create_app(
        {"OLLAMA_URL": "http://127.0.0.1:9", "GENERATION_MODEL": "kanana-1.5-2.1b-instruct:q4_k_m", "MODEL_SERVICE_TOKEN": "tok"}
    )
    r = TestClient(app).post(
        "/v1/generation/cards",
        json={"utterance": "u", "docs": [{"doc_id": "D-1", "title": "t", "snippet": "신분증", "score": 1.0}]},
        headers={"Authorization": "Bearer tok"},
    )
    assert r.status_code == 503 and r.json()["code"] == "model_unavailable"


# --- 실제 소켓 왕복 ---------------------------------------------------------------------------


class _Span:
    def __init__(self, pattern: str, start: int, end: int) -> None:
        self.pattern, self.start, self.end = pattern, start, end


class _Ner:
    model_name = "fake-ner"

    def spans(self, text):
        i = text.find("김민준")
        return [_Span("P6", i, i + 3)] if i >= 0 else []


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def live_surface():
    port = _free_port()
    app = create_http_app(ModelRegistry(ner=ModelSlot(_Ner(), "")), token="round-trip-token")
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    deadline = time.time() + 10
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("uvicorn 이 뜨지 않았다")
        time.sleep(0.02)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    t.join(timeout=5)


def _call(base: str, path: str, body: dict | None, token: str | None, timeout: float = 2.0) -> tuple[int, dict]:
    """서버 원격 어댑터가 할 호출의 최소형 — 표준 라이브러리만, 짧은 타임아웃."""
    headers = {"content-type": "application/json"}
    if token:
        headers["authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_왕복_ner_구간_인증_미적재(live_surface):
    text = "네 제 이름은 김민준입니다"
    status, body = _call(live_surface, "/v1/ner/spans", {"text": text}, "round-trip-token")
    assert status == 200
    assert body["spans"] == [{"pattern": "P6", "start": 8, "end": 11}]
    assert text[8:11] == "김민준"  # 원문 오프셋 — 부르는 쪽이 규칙 구간과 합쳐 가린다

    assert _call(live_surface, "/v1/ner/spans", {"text": text}, None)[0] == 401
    assert _call(live_surface, "/v1/ner/spans", {"text": text}, "wrong")[0] == 401
    status, body = _call(live_surface, "/v1/embeddings", {"kind": "query", "texts": ["a"]}, "round-trip-token")
    assert (status, body["code"], body["model"]) == (503, "model_not_loaded", "embedding")

    status, health = _call(live_surface, "/health", None, None)
    assert status == 200 and health["auth"] == "locked" and health["models"]["ner"]["loaded"] is True


def test_표면이_꺼져_있으면_연결_거부로_바로_드러난다():
    """GPU 인스턴스가 꺼진 상태 — 부르는 쪽은 예외를 받고 규칙으로 내려가야 한다(`decisions/121` 4번)."""
    with pytest.raises(urllib.error.URLError):
        _call(f"http://127.0.0.1:{_free_port()}", "/v1/ner/spans", {"text": "x"}, "t", timeout=1.0)


# --- 실제 모델 스모크 (선택) -----------------------------------------------------------------

MODELS = Path(os.environ.get("CALLGUARD_MODELS_DIR") or REPO / "models")  # 워크트리에는 models/ 가 없다(gitignore)


@pytest.mark.slow
@pytest.mark.skipif(not (MODELS / "koelectra-ner" / "config.json").exists(), reason="models/ 없음")
def test_실제_모델_스모크():
    from fastapi.testclient import TestClient

    env = {
        "MODEL_SERVICE_TOKEN": "smoke",
        "PII_NER_MODEL_DIR": str(MODELS / "koelectra-ner"),
        "RETRIEVAL_EMBED_MODEL_DIR": str(MODELS / "koe5"),
        "RETRIEVAL_RERANK_MODEL_DIR": str(MODELS / "bge-reranker-v2-m3"),
    }
    t0 = time.perf_counter()
    c = TestClient(model_server.create_app(env))
    load_s = time.perf_counter() - t0
    auth = {"Authorization": "Bearer smoke"}
    assert all(v["loaded"] for k, v in c.get("/health").json()["models"].items() if k != "generation")

    def timed(path, body, n=5):
        ms = []
        for _ in range(n):
            r = c.post(path, json=body, headers=auth)
            assert r.status_code == 200, r.text
            ms.append(r.json()["elapsed_ms"])
        return r.json(), sorted(ms)[n // 2]

    ner, ner_ms = timed("/v1/ner/spans", {"text": "제 이름은 김민준이고 성북구 정릉로 77길 12에 살아요"})
    assert {s["pattern"] for s in ner["spans"]} >= {"P6"}
    emb, emb_ms = timed("/v1/embeddings", {"kind": "query", "texts": ["전입신고 할 때 필요한 서류"]})
    assert emb["dims"] == 1024 and len(emb["vectors"][0]) == 1024
    rr, rr_ms = timed("/v1/rerank", {"query": "전입신고 서류", "passages": ["전입신고 시 신분증을 지참", "주차 요금 안내"] * 3})
    assert rr["scores"][0] > rr["scores"][1]
    print(f"\n[로컬 참고] 적재 {load_s:.1f}s · 표면 내부 p50 — ner {ner_ms}ms · embed {emb_ms}ms · rerank(6) {rr_ms}ms (CPU, TestClient — 네트워크 홉 없음)")
