# Requirement: D-4
"""GET /hub/knowledge-gaps · /summary · PATCH /hub/knowledge-gaps/{id}

[2.5절 D-4](/docs/02/)의 누적 루프에서 **읽는 쪽**이다. 접수(`POST`)는
`knowledge_gap_router.py` 가 맡는다 — 쓰기와 읽기를 한 파일에 두지 않는다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from hub.adapter.inbound.api.schemas.knowledge_gap_query_schema import (
    GapCountSchema,
    GapResolutionRequest,
    GapResolutionResponse,
    KnowledgeGapItemSchema,
    KnowledgeGapPageResponse,
    KnowledgeGapSummaryResponse,
)
from hub.app.dtos.knowledge_gap_query_dto import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    GapResolution,
    KnowledgeGapQuery,
)
from hub.app.ports.input.knowledge_gap_query_use_case import KnowledgeGapQueryUseCase
from hub.dependencies.knowledge_gap_query_provider import get_knowledge_gap_query_use_case

knowledge_gap_query_router = APIRouter(prefix="/hub", tags=["hub"])


def _count(c) -> GapCountSchema:
    return GapCountSchema(key=c.key, open=c.open, resolved=c.resolved, total=c.total)


@knowledge_gap_query_router.get("/knowledge-gaps", response_model=KnowledgeGapPageResponse)
async def list_knowledge_gaps(
    module: str | None = Query(default=None, description="B · C · F"),
    gap_status: str | None = Query(default=None, alias="status", description="open · resolved"),
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
    use_case: KnowledgeGapQueryUseCase = Depends(get_knowledge_gap_query_use_case),
) -> KnowledgeGapPageResponse:
    try:
        page = await use_case.list_gaps(
            KnowledgeGapQuery(module=module, status=gap_status, limit=limit, offset=offset)
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    return KnowledgeGapPageResponse(
        gaps=[
            KnowledgeGapItemSchema(
                gap_id=g.gap_id, module=g.module, description=g.description, status=g.status,
                created_at=g.created_at, call_id=g.call_id,
                segment_id=None if g.segment_id is None else str(g.segment_id),
                closure_id=g.closure_id, domain=g.domain,
            )
            for g in page.gaps
        ],
        total=page.total, limit=page.limit, offset=page.offset,
    )


@knowledge_gap_query_router.get("/knowledge-gaps/summary", response_model=KnowledgeGapSummaryResponse)
async def summarize_knowledge_gaps(
    use_case: KnowledgeGapQueryUseCase = Depends(get_knowledge_gap_query_use_case),
) -> KnowledgeGapSummaryResponse:
    s = await use_case.summarize()
    return KnowledgeGapSummaryResponse(
        by_module=[_count(c) for c in s.by_module],
        by_domain=[_count(c) for c in s.by_domain],
        total=s.total,
    )


@knowledge_gap_query_router.patch(
    "/knowledge-gaps/{gap_id}", response_model=GapResolutionResponse
)
async def resolve_knowledge_gap(
    gap_id: int,
    body: GapResolutionRequest,
    use_case: KnowledgeGapQueryUseCase = Depends(get_knowledge_gap_query_use_case),
) -> GapResolutionResponse:
    try:
        moved = await use_case.resolve(GapResolution(gap_id=gap_id, status=body.status))
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    if not moved:
        # 없는 것을 옮겼다고 하지 않는다 — 화면이 "처리했다"고 표시하면 거짓이 된다.
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"공백 신고 {gap_id} 를 찾을 수 없습니다")
    return GapResolutionResponse(gap_id=gap_id, status=body.status)
