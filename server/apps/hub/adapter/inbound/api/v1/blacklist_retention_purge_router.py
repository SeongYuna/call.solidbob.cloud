# Requirement: J-4, SEC-1
"""POST /hub/blacklist-retention/purge — 보존 기간(끝난 뒤 180일)이 지난 블랙리스트 문장을 비운다(`decisions/312`).

관리자 로그인이 필요하다. 행은 지우지 않고 문장만 표시로 바꾼다. 여러 번 불러도 결과가 같다 — 나중에 주기 실행이 같은 경로를 부를 수 있다.
"""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.blacklist_retention_purge_schema import RetentionPurgeResponse
from hub.app.ports.input.blacklist_retention_purge_use_case import BlacklistRetentionPurgeUseCase
from hub.dependencies.blacklist_retention_purge_provider import get_blacklist_retention_purge_use_case

blacklist_retention_purge_router = APIRouter(prefix="/hub", tags=["hub"])


@blacklist_retention_purge_router.post(
    "/blacklist-retention/purge", response_model=RetentionPurgeResponse, dependencies=[Depends(require_admin)]
)
async def purge_blacklist_retention(
    use_case: BlacklistRetentionPurgeUseCase = Depends(get_blacklist_retention_purge_use_case),
) -> RetentionPurgeResponse:
    r = await use_case.purge()
    return RetentionPurgeResponse(retention_days=r.retention_days, cutoff=r.cutoff.isoformat(),
                                  expiry_change_reasons_purged=r.expiry_change_reasons_purged,
                                  rejected_requests_purged=r.rejected_requests_purged)
