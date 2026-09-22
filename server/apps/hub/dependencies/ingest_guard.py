# Requirement: SEC-2, A-3
"""쓰기 경로의 문 — 콜 미디에이터만 서버에 쓸 수 있게 한다 (`_project/decisions/120`).

2026-09-20 운영 왕복에서 `POST /hub/calls`·`/hub/transcripts`·`/hub/recommendations` 등이 **토큰 없이 200** 이었다 —
주소를 아는 사람은 누구나 운영 DB 에 통화·전사를 쓸 수 있었다(CORS 는 브라우저에만 걸린다).

**상담원 토큰(`require_agent`)을 쓰지 않는 이유.** 이 경로들을 부르는 것은 브라우저가 아니라 **콜 미디에이터**(서버 ↔ 서버)다.
상담원 토큰은 사람 것이라 의미가 어긋난다. 대시보드가 직접 부르는 쓰기(`/close`·요약 확정·카드 피드백)는
**이 문이 아니라 상담원 토큰 몫**이다 — 여기서 같이 잠그면 화면이 깨진다.

업로드 문(`require_upload_token`)과 같은 모양이다 — `Authorization: Bearer`, 바이트 `compare_digest`.
**다른 점 하나: 토큰이 없으면 연다.** 이행기 동작이고 `/health` 가 그 상태를 드러낸다(`core/config.py` 주석).
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request, status


def ingest_guard_state(settings: object) -> str:
    """`/health` 가 싣는 값. 열려 있는 것이 **조용하지 않게** 한다."""
    return "locked" if getattr(settings, "ingest_service_token", None) else "open"


def service_token_matches(expected: str | None, token: str) -> bool:
    """서비스 토큰과 같은가. 미설정(`expected` 없음)이면 **같지 않다** — 열어 두는 판단은 부르는 쪽 몫이다.

    `compare_digest` 는 비-ASCII **문자열**에 TypeError 를 낸다 — 바이트로 비교해 401 이 500 이 되지 않게 한다
    (`upload_provider.require_upload_token` 이 같은 함정을 테스트로 잡았다)
    """
    return bool(expected) and bool(token) and secrets.compare_digest(token.encode("utf-8"), expected.encode("utf-8"))


def require_ingest_service(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    expected = getattr(request.app.state.settings, "ingest_service_token", None)
    if not expected:
        return  # 이행기 — 미설정이면 연다. 영구 상태가 아니다(`decisions/120` 4번에서 닫는다)

    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not service_token_matches(expected, token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 없거나 틀렸다",
            headers={"WWW-Authenticate": "Bearer"},
        )
