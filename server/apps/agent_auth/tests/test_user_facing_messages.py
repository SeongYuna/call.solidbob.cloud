# Requirement: SEC-2, QUA-1
"""화면에 그대로 뜨는 오류 문구는 존댓말이어야 한다 (2026-09-23, 수동 QA Q-11).

`apps/call`·`apps/admin` 의 API 클라이언트는 서버 응답의 `detail` 을 **그대로** 오류 메시지로 띄운다
(`apps/call/src/lib/api/coreClient.ts`). 그래서 이 문들의 문구는 개발자 로그가 아니라 **상담원·관리자가 읽는 문장**이다.
수동 QA 에서 틀린 토큰으로 로그인했더니 「…새 토큰을 받아라」가 화면에 떴다 — 다른 화면 문구는 전부 존댓말이다.

콜 미디에이터·개발자만 보는 문(`ingest_guard` · 전사 409 등)은 이 검사 밖이다 — 사람이 읽는 화면이 아니다.
"""
import re

import pytest
from fastapi import HTTPException

from admin_auth.adapter.inbound.api.admin_guard import bearer_token as admin_bearer_token
from agent_auth.adapter.inbound.api.agent_guard import agent_bearer_token, require_agent

# 존댓말 종결 — 「…습니다」·「…합니다」·「…주세요」·「…세요」
POLITE = re.compile(r"(니다|세요)([.!]|\s|$)")


def _detail(exc: HTTPException) -> str:
    return str(exc.detail)


def test_상담원_토큰이_없으면_존댓말로_안내한다():
    with pytest.raises(HTTPException) as err:
        agent_bearer_token(authorization=None)
    assert err.value.status_code == 401
    assert POLITE.search(_detail(err.value)), _detail(err.value)


def test_상담원_토큰이_폐기됐으면_존댓말로_안내한다():
    import asyncio

    class _Revoked:
        async def current(self, token: str) -> str | None:
            return None

    with pytest.raises(HTTPException) as err:
        asyncio.run(require_agent(token="cga_revoked", use_case=_Revoked()))
    assert err.value.status_code == 401
    detail = _detail(err.value)
    assert POLITE.search(detail), detail
    assert "받아라" not in detail  # 2026-09-23 이전 문구


def test_관리자_로그인_헤더가_없으면_존댓말로_안내한다():
    with pytest.raises(HTTPException) as err:
        admin_bearer_token(authorization=None)
    assert err.value.status_code == 401
    assert POLITE.search(_detail(err.value)), _detail(err.value)


def test_관리자_세션이_만료됐으면_존댓말로_안내한다():
    import asyncio

    from admin_auth.adapter.inbound.api.admin_guard import require_admin

    class _Expired:
        async def current(self, token: str):
            return None

    with pytest.raises(HTTPException) as err:
        asyncio.run(require_admin(token="expired", use_case=_Expired()))
    assert err.value.status_code == 401
    detail = _detail(err.value)
    assert POLITE.search(detail), detail
    assert "하라" not in detail
