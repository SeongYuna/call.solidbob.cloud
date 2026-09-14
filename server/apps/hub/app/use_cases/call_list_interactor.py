# Requirement: D-1, D-2
"""통화 목록 인터랙터. 페이지 경계만 검사하고 포트를 부른다 — 정렬은 리포지토리가 한다(인덱스·페이지 경계)."""

from __future__ import annotations

from hub.app.dtos.call_list_dto import MAX_LIMIT, CallListPage, CallListQuery
from hub.app.ports.input.call_list_use_case import CallListUseCase
from hub.app.ports.output.call_list_port import CallListPort


class CallListInteractor(CallListUseCase):
    def __init__(self, list_port: CallListPort) -> None:
        self._calls = list_port

    async def list(self, query: CallListQuery) -> CallListPage:
        if not 1 <= query.limit <= MAX_LIMIT:
            raise ValueError(f"limit 은 1~{MAX_LIMIT} 사이여야 합니다: {query.limit}")
        if query.offset < 0:
            raise ValueError(f"offset 은 0 이상이어야 합니다: {query.offset}")
        customer_id = query.customer_id.strip() if query.customer_id is not None else None
        if customer_id == "":
            raise ValueError("customer_id 가 비어 있습니다")

        calls = await self._calls.list_calls(query.limit, query.offset, customer_id)
        total = await self._calls.count_calls(customer_id)
        return CallListPage(calls=tuple(calls), total=total, limit=query.limit, offset=query.offset)
