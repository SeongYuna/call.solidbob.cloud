# Requirement: C-6, SEC-1
"""CallGuardFlagRecordPort 의 PostgreSQL 구현 — `call_guard_flag` 에 append 한다.

- `phrase`·`span` 은 **마스킹된 자막 기준**이다(MANUAL-5.5). 이 어댑터는 원문을 손에 넣을 경로가 없다
- `(call_id, segment_id)` 가 `transcript_segment` 를 참조한다 — 전사가 먼저 저장돼 있어야 한다.
  게이트웨이는 `POST /hub/transcripts` 응답을 받은 뒤에 검사를 부른다
- `span` 이 없는 신호는 저장하지 않고 거부한다. 컬럼이 NOT NULL 이고, 위치를 0 으로 지어내지 않는다
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.call_guard_dto import CallGuardFlag
from hub.app.ports.output.call_guard_flag_record_port import CallGuardFlagRecordPort

from .connection import ConnectionFactory

# `source_doc_id` 는 `document` 를 외래키로 참조하는데 **그 테이블을 채우는 경로가 아직 없다**(2026-09-14 확인 —
# 조항 본문은 ES 에만 적재된다). 그대로 넣으면 모든 신호가 23503 으로 실패해 탐지 기록이 통째로 사라진다.
# 조항이 `document` 에 있을 때만 잇고 없으면 NULL 로 둔다 — 근거 조항은 API 응답에는 그대로 실린다.
_INSERT = """
INSERT INTO "call_guard_flag"
    ("call_id", "segment_id", "category", "phrase", "span_start", "span_end", "source_doc_id", "detected_at")
VALUES (%s, %s, %s, %s, %s, %s, (SELECT "document_id" FROM "document" WHERE "document_id" = %s), %s)
"""

# `call_guard_flag.phrase` VARCHAR(200). 넘치면 DB 가 거부해 신호 전체를 잃는다 — 잘라서라도 남긴다.
_PHRASE_MAX = 200


class PostgresCallGuardFlagRepository(CallGuardFlagRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, call_id: str, segment_id: int, flags: tuple[CallGuardFlag, ...]) -> None:
        if any(f.span is None for f in flags):
            # 요청이 아니라 스포크 구현이 틀린 것이다 — 422 가 아니라 500 으로 드러나야 한다
            raise RuntimeError("위치(span) 없는 콜 가드 신호는 저장하지 않는다 — 스포크가 span 을 채워야 한다")
        now = datetime.now(timezone.utc)
        rows = [
            (call_id, segment_id, f.category, f.phrase[:_PHRASE_MAX], f.span[0], f.span[1], f.source_doc_id, now)
            for f in flags
            if f.span is not None
        ]
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(_INSERT, rows)
            await conn.commit()
