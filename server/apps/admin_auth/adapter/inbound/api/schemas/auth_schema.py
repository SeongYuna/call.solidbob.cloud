# Requirement: 관리자 로그인(구글), 7.3절 인터페이스 계약
"""HTTP 표면 스키마. 회원가입 필드가 없다 — 구글 id_token 하나로 로그인이 끝난다.

응답의 숫자 필드는 `StrField` 로 문자열화한다 — 2026-09-10 조서희·장민석 합의
(`hub/adapter/inbound/api/schemas/_types.py`, `test_segment_id_contract.py` 가 전체 OpenAPI
스키마에 대해 이 규칙을 강제한다). 요청(Request) 스키마는 대상이 아니다."""

from __future__ import annotations

from pydantic import BaseModel, Field

from hub.adapter.inbound.api.schemas._types import StrField


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1, description="Google Identity Services가 프론트에 준 id_token(JWT credential)")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str | None = Field(default=None, description="없어도 access token 세션만 정리하고 끝난다")


class TokenPairResponse(BaseModel):
    access_token: str
    access_token_expires_in: StrField = Field(description="초. 문자열로 나간다(7.3절 계약)")
    refresh_token: str
    refresh_token_expires_in: StrField = Field(description="초. 문자열로 나간다(7.3절 계약)")


class AdminMeResponse(BaseModel):
    email: str
    name: str | None


class AuthProbeResponse(BaseModel):
    """`GET /admin/auth/test` 의 응답. 필드가 전부 `str` 인 것은 위 계약 때문이다."""

    status: str = Field(description="항상 \"ok\" — 이 라우터가 떠 있다는 것 외에는 아무 뜻이 없다")
    router: str = Field(description="어느 라우터가 응답했는지. 항상 \"admin_auth\"")
    marker: str = Field(
        description="배포 확인용 표식. **자동이 아니다** — 새 이미지가 떴는지 눈으로 보려고 "
                    "`infra/k8s/base/kustomization.yaml` 의 newTag 와 같이 손으로 올린다"
    )
