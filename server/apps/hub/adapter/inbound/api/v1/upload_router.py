# Requirement: A-6, SEC-1, SEC-2
"""테스트 음성 업로드·보관 — `POST /hub/uploads/ticket` · `GET /hub/uploads` · 다시 듣기.

브라우저는 서버에서 **티켓만** 받고 S3 로 직접 올린다. 파일 바이트는 이 서버를 지나가지 않는다 —
파드 메모리·디스크에 음성이 남지 않고(SEC-1), 업로드가 커도 요청 경로(전사·마스킹)를 막지 않는다.

문은 `require_upload_token` 이다(`_project/decisions/110` 4번). 페이지(`GET /hub/uploads/page`)만
토큰 없이 열린다 — 비밀이 없는 껍데기이고, 사람이 거기에 토큰을 붙여 넣는다(`decisions/109` 와 같은 모양).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse

from hub.adapter.inbound.api.schemas.upload_schema import (
    DownloadTicketRequest,
    DownloadTicketSchema,
    StoredUploadListSchema,
    StoredUploadSchema,
    UploadTicketRequest,
    UploadTicketSchema,
)
from hub.adapter.inbound.api.v1.upload_page import UPLOAD_PAGE_HTML
from hub.app.dtos.upload_dto import UploadTicketCommand
from hub.app.ports.input.upload_use_case import UploadUseCase
from hub.app.use_cases.upload_interactor import UploadRejected
from hub.dependencies.upload_provider import get_upload_use_case, require_upload_token

upload_router = APIRouter(prefix="/hub", tags=["hub"])


@upload_router.post(
    "/uploads/ticket",
    response_model=UploadTicketSchema,
    dependencies=[Depends(require_upload_token)],
)
async def issue_upload_ticket(
    body: UploadTicketRequest,
    use_case: UploadUseCase = Depends(get_upload_use_case),
) -> UploadTicketSchema:
    try:
        ticket = await use_case.issue(
            UploadTicketCommand(
                filename=body.filename,
                content_type=body.content_type,
                content_length=body.content_length,
            )
        )
    except UploadRejected as exc:
        # 거절 사유는 규칙이지 값이 아니다 — 파일명·토큰이 본문에 실리지 않는다.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UploadTicketSchema(
        url=ticket.url, fields=ticket.fields, key=ticket.key, expires_in=ticket.expires_in
    )


@upload_router.get(
    "/uploads",
    response_model=StoredUploadListSchema,
    dependencies=[Depends(require_upload_token)],
)
async def list_uploads(
    limit: int = Query(default=50, ge=1, le=200),
    use_case: UploadUseCase = Depends(get_upload_use_case),
) -> StoredUploadListSchema:
    items = await use_case.list_recent(limit)
    return StoredUploadListSchema(
        items=[
            StoredUploadSchema(key=i.key, size=i.size, last_modified=i.last_modified)
            for i in items
        ],
        total=len(items),
    )


@upload_router.post(
    "/uploads/download-ticket",
    response_model=DownloadTicketSchema,
    dependencies=[Depends(require_upload_token)],
)
async def issue_download_ticket(
    body: DownloadTicketRequest,
    use_case: UploadUseCase = Depends(get_upload_use_case),
) -> DownloadTicketSchema:
    try:
        ticket = await use_case.issue_download(body.key)
    except UploadRejected as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DownloadTicketSchema(url=ticket.url, key=ticket.key, expires_in=ticket.expires_in)


@upload_router.get("/uploads/page", response_class=HTMLResponse, include_in_schema=False)
async def upload_page() -> HTMLResponse:
    """팀원이 여는 페이지. **비밀이 들어 있지 않다** — 토큰은 사람이 붙여 넣고 브라우저에만 남는다."""
    return HTMLResponse(UPLOAD_PAGE_HTML)
