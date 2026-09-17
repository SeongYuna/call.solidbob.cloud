# Requirement: A-6, SEC-2
"""업로드 슬라이스의 배선과 **문**.

`_project/decisions/110` 4번: **토큰이 설정돼 있지 않으면 전부 거절한다(fail-closed).**
잠기지 않은 발급 지점은 익명 업로드 프록시라, 「브라우저에 키가 없으니 안전하다」가 성립하지 않는다.
콜 미디에이터(`services/call-mediator`)의 문과 같은 원칙이다(`decisions/109` 3번).
"""

from __future__ import annotations

import secrets

from fastapi import Depends, Header, HTTPException, Request, status

from hub.app.ports.input.upload_use_case import UploadUseCase
from hub.app.ports.output.upload_storage_port import UploadStoragePort
from hub.app.use_cases.upload_interactor import UploadInteractor


def get_upload_storage_port() -> UploadStoragePort:
    """합성 루트(`main.py`)가 실제 어댑터로 덮어쓴다.

    안 꽂혔으면 **501 로 남는다** — 임시 구현을 만들지 않는다(`decisions/024` 와 같은 설계).
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="업로드 저장소가 설정되지 않았다 — S3_BUCKET 을 넣어야 한다",
    )


def get_upload_max_bytes(request: Request) -> int:
    return int(request.app.state.settings.upload_max_bytes)


def require_upload_token(
    request: Request,
    authorization: str | None = Header(default=None),
) -> None:
    """`Authorization: Bearer <UPLOAD_TOKEN>` 만 받는다. URL 에 비밀을 싣지 않는다.

    비교는 `compare_digest` 로 한다 — `==` 는 앞에서부터 다른 지점에서 멈춰 **응답 시간이
    토큰을 흘린다.** 문이 하나뿐이라 여기서 새면 막을 곳이 없다.
    """
    expected = getattr(request.app.state.settings, "upload_token", None)
    if not expected:
        # 토큰 미설정 = 잠긴 상태다. 열린 상태가 아니다.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업로드 문이 잠겨 있다 — UPLOAD_TOKEN 이 설정되지 않았다",
        )
    scheme, _, token = (authorization or "").partition(" ")
    # ⚠ `compare_digest` 는 **비-ASCII 문자열에 TypeError 를 낸다** — 한글 토큰을 보내면 401 이
    #    아니라 500 이 났다(이 파일의 테스트가 잡았다). 바이트로 비교하면 그런 입력이 없다.
    if (
        scheme.lower() != "bearer"
        or not token
        or not secrets.compare_digest(token.encode("utf-8"), expected.encode("utf-8"))
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 없거나 틀렸다",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_upload_use_case(
    storage: UploadStoragePort = Depends(get_upload_storage_port),
    max_bytes: int = Depends(get_upload_max_bytes),
) -> UploadUseCase:
    return UploadInteractor(storage=storage, max_bytes=max_bytes)
