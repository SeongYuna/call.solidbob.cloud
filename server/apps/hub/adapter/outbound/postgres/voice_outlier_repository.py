# Requirement: D-5
"""VoiceOutlierRecordPort 의 PostgreSQL 구현 — `voice_outlier` 에 쓴다.

**화자 단위로 갈아끼운다.** 기준선이 그 화자의 발화 전체로 만들어지므로, 발화가 늘어 다시 판정하면
앞 발화의 판정도 바뀐다. 한 건씩 덧붙이면 옛 기준선과 새 기준선의 판정이 섞인다.

⚠ `robust_z` 는 **여기까지만 간다.** 조회 응답에 싣지 않는다(부록 A-1) — 이 값을 읽는 것은
임계값을 바꿔 재판정할 때뿐이다. `hub/tests/adapter/test_voice_outlier_not_exposed.py` 가 고정한다.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from hub.app.dtos.transcript_dto import Speaker
from hub.app.dtos.voice_outlier_dto import VoiceOutlier
from hub.app.ports.output.voice_outlier_record_port import VoiceOutlierRecordPort

from .connection import ConnectionFactory

_DELETE = 'DELETE FROM "voice_outlier" WHERE "call_id" = %s AND "speaker" = %s'

_INSERT = """
INSERT INTO "voice_outlier" ("call_id", "segment_id", "speaker", "robust_z", "baseline_n", "detected_at")
VALUES (%s, %s, %s, %s, %s, %s)
"""


class PostgresVoiceOutlierRepository(VoiceOutlierRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def replace(self, call_id: str, speaker: Speaker, outliers: Sequence[VoiceOutlier]) -> None:
        other = [o.segment_id for o in outliers if o.speaker != speaker]
        if other:
            # 화자를 섞으면 DELETE 가 지운 것과 INSERT 가 넣는 것의 범위가 어긋난다
            raise ValueError(f"'{speaker}' 의 이상 구간에 다른 화자 발화가 섞였습니다: {other}")

        now = datetime.now(timezone.utc)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_DELETE, (call_id, speaker))
                if outliers:
                    await cur.executemany(
                        _INSERT,
                        [(call_id, o.segment_id, o.speaker, o.robust_z, o.baseline_n, now) for o in outliers],
                    )
            await conn.commit()
