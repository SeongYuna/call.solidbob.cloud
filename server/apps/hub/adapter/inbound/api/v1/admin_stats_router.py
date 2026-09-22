# Requirement: J-3, J-5, C-6
"""GET /hub/admin-stats — 관리자 현황판 숫자. 관리자 로그인이 필요하다.

전에는 화면이 목록 API 넷을 `limit=1` 로 불러 `total` 만 썼고(그중 통화 목록은 무인증), 배정 판정 집계는 부를 곳이 없었다.
**상담원 단위 숫자는 없다**(부록 A-1) — 누가 몇 건을 했는지는 이 API 로 알 수 없다.
"""

from __future__ import annotations

from admin_auth.adapter.inbound.api.admin_guard import require_admin
from fastapi import APIRouter, Depends

from hub.adapter.inbound.api.schemas.admin_stats_schema import AdminStatsResponse
from hub.app.ports.input.admin_stats_use_case import AdminStatsUseCase
from hub.dependencies.admin_stats_provider import get_admin_stats_use_case

admin_stats_router = APIRouter(prefix="/hub", tags=["hub"])


@admin_stats_router.get("/admin-stats", response_model=AdminStatsResponse, dependencies=[Depends(require_admin)])
async def get_admin_stats(use_case: AdminStatsUseCase = Depends(get_admin_stats_use_case)) -> AdminStatsResponse:
    s = await use_case.get()
    return AdminStatsResponse(
        calls_total=s.calls_total, calls_closed=s.calls_closed, call_guard_flags=s.call_guard_flags,
        pending_requests=s.pending_requests, active_entries=s.active_entries,
        routing_decisions=s.routing_decisions, routing_blacklisted=s.routing_blacklisted,
        routing_fell_back=s.routing_fell_back, counted_at=s.counted_at.isoformat(),
    )
