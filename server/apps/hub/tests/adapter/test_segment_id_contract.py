# Requirement: 7.3절 인터페이스 계약, QUA-1
"""**응답 필드는 전부 문자열이다** (2026-09-10 조서희·장민석 합의 — 프론트 파서가 문자열만 받는다).
DB 는 원래 타입, 내부 DTO 도 원래 타입 — 변환은 스키마 계층(`schemas/_types.py` `StrField`)에서만 한다.
이 파일이 그 계약을 고정한다: 실제 응답과 `/openapi.json` 공표 둘 다."""

from fastapi.testclient import TestClient

from main import app

BODY = {"call_id": "c_001", "segment_id": 7, "speaker": "customer", "text": "여권 재발급 서류가 뭐예요",
        "is_final": True, "utterance_end_ms": 1000}


def _leaves(value):
    """JSON 트리의 말단 값만 모은다 — None 은 허용(“값이 없다”는 정보를 문자열로 뭉개지 않는다)."""
    if isinstance(value, dict):
        for v in value.values():
            yield from _leaves(v)
    elif isinstance(value, list):
        for v in value:
            yield from _leaves(v)
    else:
        yield value


def test_전사_응답은_말단_값이_전부_문자열이다():
    with TestClient(app) as client:
        body = client.post("/hub/transcripts", json={**BODY, "text": "제 번호는 01012345678 이에요"}).json()
    assert body["segment_id"] == "7" and body["is_final"] == "true" and body["utterance_end_ms"] == "1000"
    assert body["masked"][0]["span"] == ["6", "17"]
    assert all(v is None or isinstance(v, str) for v in _leaves(body)), body


def test_요청은_숫자_문자열도_받는다():
    """프론트가 계약대로 문자열을 보내도 422 가 아니다."""
    with TestClient(app) as client:
        r = client.post("/hub/transcripts", json={**BODY, "segment_id": "7", "utterance_end_ms": "1000", "is_final": "true"})
    assert r.status_code == 200 and r.json()["segment_id"] == "7"


def test_통화_시작_응답도_문자열이다():
    with TestClient(app) as client:
        body = client.post("/hub/calls", json={"call_id": "test-c001"}).json()
    assert body["created"] == "true" and body["channel_count"] == "1"


def test_OpenAPI_응답_스키마에_숫자_불리언_타입이_없다():
    """조서희가 붙일 때 읽는 것은 /openapi.json 이다 — 응답 스키마가 전부 string 이어야 한다.
    `/health` 는 스키마가 없는 dict 라 대상이 아니다(런북 19장 배포 검증 항목 — 불리언 유지)."""
    with TestClient(app) as client:
        spec = client.get("/openapi.json").json()
    schemas = spec["components"]["schemas"]
    response_names = set()
    for ops in spec["paths"].values():
        for op in ops.values():
            ref = (op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {})
                   .get("schema", {}).get("$ref"))
            if ref:
                response_names.add(ref.split("/")[-1])

    def walk(name, seen):
        if name in seen:
            return
        seen.add(name)
        for field, prop in schemas[name].get("properties", {}).items():
            for node in [prop, *prop.get("anyOf", []), prop.get("items", {}), *prop.get("prefixItems", [])]:
                if "$ref" in node:
                    walk(node["$ref"].split("/")[-1], seen)
                if "additionalProperties" in node and "$ref" in node["additionalProperties"]:
                    walk(node["additionalProperties"]["$ref"].split("/")[-1], seen)
                t = node.get("type")
                if node.get("additionalProperties") and isinstance(node["additionalProperties"], dict):
                    t2 = node["additionalProperties"].get("type")
                    assert t2 not in ("integer", "number", "boolean"), (name, field, node)
                assert t not in ("integer", "number", "boolean"), (name, field, node)

    seen: set = set()
    for n in response_names:
        walk(n, seen)
    assert seen  # 아무것도 안 본 초록은 초록이 아니다
