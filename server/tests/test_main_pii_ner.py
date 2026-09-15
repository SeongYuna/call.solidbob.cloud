# Requirement: C-5, SEC-1
"""합성 루트가 `ai/` 의 NER(P6·P7)을 규칙 마스킹 **위에** 꽂는지 (`w5-ner-p6-p7`).

server CI 에는 torch·모델이 없다 — 그 환경에서는 설정을 넣어도 **규칙 마스킹이 그대로 돌아야** 한다.
모델이 있는 로컬에서만 실제로 켜지는 경로를 확인한다.
"""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hub.dependencies.masking_provider import get_masking_port
from main import app

MODEL_DIR = Path(__file__).resolve().parents[2] / "models" / "koelectra-ner"
NER_AVAILABLE = importlib.util.find_spec("transformers") is not None and MODEL_DIR.exists()


@pytest.fixture(autouse=True)
def _clear_masking_override():
    # 전역 `app` 에 꽂힌 프로바이더가 다른 테스트로 새지 않게 한다 — lifespan 은 빈 자리만 채운다(setdefault)
    app.dependency_overrides.pop(get_masking_port, None)
    yield
    app.dependency_overrides.pop(get_masking_port, None)


def test_설정이_없으면_규칙_마스킹만_돈다(monkeypatch):
    monkeypatch.delenv("PII_NER_MODEL_DIR", raising=False)
    with TestClient(app) as client:
        spokes = client.get("/health").json()["spokes"]
    assert "masking" in spokes and "pii_ner" not in spokes
    assert get_masking_port not in app.dependency_overrides


def test_모델_디렉터리가_없으면_조용히_규칙으로_내려간다(monkeypatch, tmp_path):
    """모델이 없다고 서버가 못 뜨면 자막·마스킹까지 멈춘다 — 그게 이름 몇 개 놓치는 것보다 나쁘다."""
    monkeypatch.setenv("PII_NER_MODEL_DIR", str(tmp_path / "없는-모델"))
    with TestClient(app) as client:
        spokes = client.get("/health").json()["spokes"]
    assert "masking" in spokes and "pii_ner" not in spokes


def test_스포크_이름에_모델_경로가_새지_않는다(monkeypatch, tmp_path):
    monkeypatch.setenv("PII_NER_MODEL_DIR", str(tmp_path / "secret-model-path"))
    with TestClient(app) as client:
        body = client.get("/health").json()
    assert "secret-model-path" not in str(body)


@pytest.mark.skipif(not NER_AVAILABLE, reason="transformers 또는 models/koelectra-ner 없음")
def test_모델이_있으면_NER_이_규칙_위에_꽂힌다(monkeypatch):
    monkeypatch.setenv("PII_NER_MODEL_DIR", str(MODEL_DIR))
    with TestClient(app) as client:
        assert "pii_ner" in client.get("/health").json()["spokes"]
        port = app.dependency_overrides[get_masking_port]()
    # 규칙은 문맥 없는 이름을 못 잡는다(GS-056) — NER 겹이 붙어야 가려진다
    masked, spans = port.mask("그 김민준 씨가 어제 신고한 건 확인 부탁드려요 번호는 01012345678")
    assert "김민준" not in masked and "01012345678" not in masked
    assert {s.type for s in spans} == {"P4", "P6"}


def test_임베딩_설정이_없으면_검색은_BM25_층만(monkeypatch):
    """`decisions/206` — 모델 디렉터리가 없으면 `/health` 에 `retrieval_dense`·`rerank` 가 뜨지 않는다."""
    monkeypatch.setenv("ELASTICSEARCH_URL", "http://es.internal:9200")
    monkeypatch.delenv("RETRIEVAL_EMBED_MODEL_DIR", raising=False)
    with TestClient(app) as client:
        spokes = client.get("/health").json()["spokes"]
    assert "retrieval_dense" not in spokes and "rerank" not in spokes



def test_생성은_OLLAMA_URL_만으로는_안_켜진다(monkeypatch):
    """런북 16-1 이 OLLAMA_URL 을 이미 주입한다 — 그것만으로 켜지면 다음 배포에서 조용히 추천 지연이 는다(`decisions/207`)."""
    from hub.dependencies.generation_provider import get_generation_port

    app.dependency_overrides.pop(get_generation_port, None)
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    monkeypatch.delenv("GENERATION_MODEL", raising=False)
    with TestClient(app) as client:
        assert "generation" not in client.get("/health").json()["spokes"]
    assert get_generation_port not in app.dependency_overrides


def test_생성_모델까지_넣으면_꽂힌다(monkeypatch):
    from hub.dependencies.generation_provider import get_generation_port
    from hub.dependencies.postcall_provider import get_postcall_port

    app.dependency_overrides.pop(get_generation_port, None)
    app.dependency_overrides.pop(get_postcall_port, None)
    monkeypatch.setenv("OLLAMA_URL", "http://ollama:11434")
    monkeypatch.setenv("GENERATION_MODEL", "kanana-1.5-2.1b-instruct:q4_k_m")
    try:
        with TestClient(app) as client:
            spokes = client.get("/health").json()["spokes"]
        assert "generation" in spokes and "postcall_model" in spokes  # D-1·D-2 도 같은 스위치(w7-postcall-spoke)
        assert "ollama:11434" not in str(spokes)  # 주소가 새지 않는다(SEC-2)
    finally:
        app.dependency_overrides.pop(get_generation_port, None)
        app.dependency_overrides.pop(get_postcall_port, None)
