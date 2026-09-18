# Requirement: F-2, QUA-1
"""HTTP 표면. 2026-08-27 부터 실제 게이트(closure_gate 스포크)가 기본으로 붙어 있다.

그 전에는 501 을 확인하는 테스트였다 — 스포크가 없을 때 통과시키지 않는 것이 절대 규칙이라서다.
이제 구현이 있으므로 **기본 배선으로 실제 판정이 나오는지**를 본다. 지키려는 성질은 그대로다:
**근거가 미충족이면 어떤 경로로도 `approved` 가 나오지 않는다.**
"""

from fastapi.testclient import TestClient

from hub.app.dtos import ClosureVerdict
from hub.app.ports.output import ClosureGatePort
from hub.dependencies.closure_provider import get_closure_gate_port
from main import app

BODY = {"call_id": "c_001", "procedure": "DASAN-TERM-4.4",
        "evidence": {"신고서": True}, "reason": "안내 완료"}


class _Stub(ClosureGatePort):
    def evaluate(self, call_id, procedure, evidence, reason=None):
        missing = tuple(k for k, v in evidence.items() if not v)
        return ClosureVerdict(call_id=call_id, procedure=procedure, evidence=dict(evidence),
                              verdict="incomplete" if missing else "complete", missing=missing, reason=reason)


def test_기본_배선으로_실제_규칙이_판정한다():
    """스텁 없이 — `main.py` 가 조립한 그대로. 빠진 서류는 `complete` 가 될 수 없다."""
    with TestClient(app) as client:
        r = client.post("/hub/closure-checks", json=BODY)
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "incomplete"
    assert body["missing"] == ["신고인 신분증"]  # 키가 빠진 것도 누락이다
    assert body["evidence"] == {"신고서": "true", "신고인 신분증": "false"}
    assert body["source"]["doc_id"] == "DASAN-TERM-4.4" and body["detected"] == "false"
    assert body["conditional"]


def test_규칙표에_없는_절차는_판정하지_않고_422다():
    """판정할 규칙이 없는 것이지 서류가 빠진 것이 아니다 — complete 도 incomplete 도 거짓말이다."""
    with TestClient(app) as client:
        r = client.post("/hub/closure-checks", json={**BODY, "procedure": "DASAN-TERM-3.4"})  # 3.4 는 EXCLUDED — 2.6 은 09-18 규칙이 생겼다
    assert r.status_code == 422
    assert "complete" not in r.text


def test_빈_근거는_422다():
    app.dependency_overrides[get_closure_gate_port] = lambda: _Stub()
    try:
        with TestClient(app) as client:
            r = client.post("/hub/closure-checks", json={**BODY, "evidence": {}})
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_자동_판정_경로는_상담원_발화로_누락을_찾는다():
    body = {"call_id": "c_002", "procedure": "DASAN-TERM-4.4", "agent_utterances": ["신고서 작성해 주세요"]}
    with TestClient(app) as client:
        r = client.post("/hub/required-docs-checks", json=body)
        empty = client.post("/hub/required-docs-checks", json={**body, "agent_utterances": []})
        unknown = client.post("/hub/required-docs-checks", json={**body, "procedure": "DASAN-TERM-3.4"})
    assert r.status_code == 200
    assert r.json()["missing"] == ["신고인 신분증"] and r.json()["detected"] == "true"
    assert empty.json()["missing"] == ["신고서", "신고인 신분증"]
    assert unknown.status_code == 422
