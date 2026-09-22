# Requirement: F-2, QUA-1
"""필요서류 판정 두 경로 — 통화가 없으면 500 이 아니라 404(`decisions/318`)."""

import pytest
from fastapi.testclient import TestClient

from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError
from hub.dependencies.closure_provider import get_closure_check_use_case
from hub.dependencies.required_docs_detection_provider import get_required_docs_detection_use_case
from main import app


class _NoCall:
    async def check(self, command):
        raise CallNotStartedError(command.call_id)


@pytest.mark.parametrize("provider,path,body", [
    (get_required_docs_detection_use_case, "/hub/required-docs-checks",
     {"call_id": "ghost", "procedure": "DASAN-TERM-4.4", "agent_utterances": ["신고서 준비하세요"]}),
    (get_closure_check_use_case, "/hub/closure-checks",
     {"call_id": "ghost", "procedure": "DASAN-TERM-4.4", "evidence": {"신고서": True}}),
], ids=["required_docs", "closure_check"])
def test_통화가_없으면_404다(monkeypatch, provider, path, body):
    monkeypatch.delenv("INGEST_SERVICE_TOKEN", raising=False)  # 쓰기 경로 문은 test_main_ingest_guard 가 본다
    app.dependency_overrides[provider] = lambda: _NoCall()
    try:
        with TestClient(app) as c:
            r = c.post(path, json=body)
        assert r.status_code == 404 and "ghost" in r.json()["detail"]
    finally:
        app.dependency_overrides.clear()
