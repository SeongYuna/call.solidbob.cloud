# Requirement: 관리자 로그인(구글), QUA-1
"""`GET /admin/auth/test` — 배포 확인용 프로브.

**이 파일이 확인하는 것은 두 가지다.** ① 엔드포인트가 인증 없이 200 을 돌려준다
② `/openapi.json` 에 그 경로가 **실제로 공표된다** — 스웨거가 바뀌는지가 이 작업의 목적이라,
라우트만 있고 스키마에 안 실리는 경우(`include_in_schema=False` 등)를 여기서 잡는다.
"""

from fastapi.testclient import TestClient

from admin_auth.adapter.inbound.api.v1.auth_router import PROBE_MARKER
from main import app


def test_프로브는_토큰_없이_200을_돌려준다():
    with TestClient(app) as client:
        r = client.get("/admin/auth/test")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "router": "admin_auth", "marker": PROBE_MARKER}


def test_openapi에_경로가_공표된다():
    """조서희가 보는 것도, 배포 확인에 쓰는 것도 `/openapi.json` 이다."""
    with TestClient(app) as client:
        spec = client.get("/openapi.json").json()
    op = spec["paths"]["/admin/auth/test"]["get"]
    assert op["tags"] == ["admin_auth"]
    assert op["summary"] == "배포 확인용 프로브"


def test_응답에_비밀이_없다():
    """SEC-2 — 프로브는 설정 여부조차 싣지 않는다. 값이 셋뿐인 것을 고정한다."""
    with TestClient(app) as client:
        body = client.get("/admin/auth/test").json()
    assert set(body) == {"status", "router", "marker"}
    assert all(isinstance(v, str) for v in body.values())  # 7.3절 — 응답 말단은 전부 문자열
