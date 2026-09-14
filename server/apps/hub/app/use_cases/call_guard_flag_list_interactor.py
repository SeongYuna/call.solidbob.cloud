# Requirement: C-6
"""콜 가드 로그 인터랙터 — 필터·페이지 경계만 확인하고 포트를 부른다."""

from __future__ import annotations

from hub.app.dtos.call_guard_flag_list_dto import CATEGORIES, MAX_LIMIT, CallGuardFlagListQuery, CallGuardFlagPage
from hub.app.ports.input.call_guard_flag_list_use_case import CallGuardFlagListUseCase
from hub.app.ports.output.call_guard_flag_query_port import CallGuardFlagQueryPort


class CallGuardFlagListInteractor(CallGuardFlagListUseCase):
    def __init__(self, query_port: CallGuardFlagQueryPort) -> None:
        self._query = query_port

    async def list(self, query: CallGuardFlagListQuery) -> CallGuardFlagPage:
        if query.category is not None and query.category not in CATEGORIES:
            raise ValueError(f"'{query.category}' 는 콜 가드 갈래가 아닙니다 (가능: {', '.join(CATEGORIES)})")
        if not 1 <= query.limit <= MAX_LIMIT:
            raise ValueError(f"limit 은 1~{MAX_LIMIT} 사이여야 합니다: {query.limit}")
        if query.offset < 0:
            raise ValueError(f"offset 은 0 이상이어야 합니다: {query.offset}")

        flags = await self._query.list_flags(query.call_id, query.category, query.limit, query.offset)
        total = await self._query.count_flags(query.call_id, query.category)
        return CallGuardFlagPage(flags=tuple(flags), total=total, limit=query.limit, offset=query.offset)
