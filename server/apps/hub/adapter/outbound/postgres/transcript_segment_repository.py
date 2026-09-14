# Requirement: 7.3절 전사 이벤트, C-5, SEC-1
"""TranscriptIngestRecordPort 의 PostgreSQL 구현. LogTranscriptIngestRecordAdapter 를 대체한다.

**두 가지를 지킨다.**

1. **SEC-1 — 마스킹 완료본만 저장한다.** 이 어댑터는 `TranscriptEvent` 만 받는데, 그 안의 `text` 는
   이미 MaskingPort 를 거친 것이다. 원문(`TranscriptIngestCommand.raw_text`)은 인터랙터 밖으로
   나오지 않으므로 여기서는 손에 넣을 방법 자체가 없다. `transcript_segment.text` 컬럼 주석과 같은 규칙이다.

2. **interim 은 저장하지 않는다.** [7.3절](/docs/07/)이 정한 규칙 —
   *"DB에는 `is_final: true`만 저장 — interim까지 저장하면 통화 1건에 수천 행이 쌓인다."*
   [V4 실측](/docs/05/)상 20초 발화에 interim 이 199건 온다. 화면은 `segment_id` 로 교체해 보여주고,
   DB 는 확정본만 남긴다.

**키는 `(call_id, segment_id)` 다** (`decisions/205`). `segment_id` 는 통화 안에서의 순번이라 통화를
넘어 유일하지 않다 — `segment_id` 하나로 UPSERT 하면 다른 통화의 같은 순번 발화를 덮어쓴다.
`masking_event` 도 같은 복합키로 `transcript_segment` 를 참조하므로 구간을 지우고 넣을 때도 둘을 함께 쓴다.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.transcript_dto import TranscriptEvent
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError, TranscriptIngestRecordPort

from .connection import ConnectionFactory

# PostgreSQL SQLSTATE `foreign_key_violation`. psycopg 를 import 하지 않고 코드로 가린다 —
# 리포지토리는 드라이버를 직접 알지 않는다(connection.py 주석).
_FOREIGN_KEY_VIOLATION = "23503"

# 식별자를 큰따옴표로 감싼다 — `call`·`rank` 처럼 예약어인 이름이 있다.
# UPSERT 는 PostgreSQL 의 ON CONFLICT 다 (MySQL 의 ON DUPLICATE KEY UPDATE 대응).
_UPSERT_SEGMENT = """
INSERT INTO "transcript_segment"
    ("segment_id", "call_id", "speaker", "text", "is_final", "utterance_end_ms", "created_at")
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT ("call_id", "segment_id") DO UPDATE SET
    "text" = EXCLUDED."text",
    "is_final" = EXCLUDED."is_final",
    "utterance_end_ms" = EXCLUDED."utterance_end_ms"
"""

_DELETE_SPANS = 'DELETE FROM "masking_event" WHERE "call_id" = %s AND "segment_id" = %s'

_INSERT_SPAN = """
INSERT INTO "masking_event" ("call_id", "segment_id", "pattern", "span_start", "span_end", "created_at")
VALUES (%s, %s, %s, %s, %s, %s)
"""


class PostgresTranscriptSegmentRepository(TranscriptIngestRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, event: TranscriptEvent) -> None:
        if not event.is_final:
            return  # interim 은 화면 갱신용 — 저장하지 않는다 (7.3절)

        now = datetime.now(timezone.utc)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        _UPSERT_SEGMENT,
                        (
                            event.segment_id,
                            event.call_id,
                            event.speaker,
                            event.text,  # 마스킹 완료본 (SEC-1)
                            event.is_final,
                            event.utterance_end_ms,
                            now,
                        ),
                    )
                except Exception as exc:
                    # 이 INSERT 가 참조하는 외래키는 call 하나뿐이다 — 통화 시작(POST /hub/calls)이 안 왔다
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise CallNotStartedError(event.call_id) from exc
                    raise
                # 같은 segment 를 다시 받으면 구간도 갈아끼운다 — 남아 있으면 이전 마스킹과 섞인다
                await cur.execute(_DELETE_SPANS, (event.call_id, event.segment_id))
                if event.masked:
                    await cur.executemany(
                        _INSERT_SPAN,
                        [
                            (event.call_id, event.segment_id, s.type, s.span[0], s.span[1], now)
                            for s in event.masked
                        ],
                    )
            await conn.commit()
