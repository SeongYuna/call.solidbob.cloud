# Requirement: J-2, J-4
"""BlacklistPort 의 PostgreSQL 구현 — 요청(`blacklist_request`)과 등록 에피소드(`blacklist_entry`).

- **상태 전이는 도메인 규칙으로 확인한다**(`blacklist.domain.services.transitions`). 이 어댑터가 마음대로
  `approved` 로 올릴 수 있으면 «승인 없이 등록» 이 저장소마다 가능해진다(포트 주석)
- 결정은 `SELECT … FOR UPDATE` 로 잠그고 한 트랜잭션에서 요청 갱신 + 등록 생성을 한다 — 두 관리자가 동시에
  눌러도 등록이 둘이 되지 않는다. 같은 고객의 적용 중 등록이 이미 있으면 부분 유니크 인덱스가 막는다
- `distress_count` 는 저장하지 않는다(`decisions/205` ④) — 컬럼이 없다
- 해제는 행을 지우지 않고 `released_at`·`released_by`·`release_reason` 을 찍는다
- **만료 변경(연장·단축)은 `blacklist_entry_expiry_change` 에 쌓는다**(`decisions/309`) — `expires_at` 만 덮으면 누가 왜 늘렸는지가 사라진다
- **보존 기간 정리**(`decisions/312`) — 끝난 지 180일이 지난 만료 변경 사유 · 반려 요청의 사유·자막을 표시로 바꾼다. 행은 지우지 않는다
- 승인할 때 같은 고객의 **만료됐지만 해제되지 않은** 등록을 먼저 «만료» 로 닫는다 — 부분 유니크(`released_at IS NULL`)가
  만료된 행도 자리로 세서, 만료 뒤 새 승인이 늘 23505 였다(2026-09-15 발견)
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.adapter.outbound.postgres.connection import ConnectionFactory
from hub.app.dtos.blacklist_retention_dto import RetentionPurgeResult
from hub.app.dtos.blacklist_dto import (
    STATUS_APPROVED,
    STATUS_REJECTED,
    BlacklistEntry,
    BlacklistRequest,
    ExpiryChange,
    RequestEvidence,
)
from hub.app.ports.output.blacklist_port import (
    BlacklistConflict,
    BlacklistNotFound,
    BlacklistPort,
    ExpiryBeyondCap,
    UnknownAgent,
)

from ...domain.services.expiry import latest_allowed_expiry, within_cap
from ...domain.services.retention import PURGED_TEXT, RETENTION_DAYS, purge_cutoff
from ...domain.services.transitions import ROLE_ADMIN, TransitionNotAllowed, transition

_UNIQUE_VIOLATION = "23505"
_FOREIGN_KEY_VIOLATION = "23503"

_REQUEST_COLUMNS = """
"request_id", "call_id", "customer_ref", "requested_by", "reason", "context_excerpt", "call_duration_s",
"insult_count", "threat_count", "sexual_count", "temperature_outliers", "status", "requested_at",
"decided_by", "decided_at", "evidence_snapshot_at", "decision_note"
"""
_INSERT_REQUEST = f"""
INSERT INTO "blacklist_request"
    ("call_id", "customer_ref", "requested_by", "reason", "context_excerpt", "call_duration_s", "insult_count",
     "threat_count", "sexual_count", "temperature_outliers", "status", "requested_at", "evidence_snapshot_at")
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
RETURNING {_REQUEST_COLUMNS}
"""
_LIST_REQUESTS = f'SELECT {_REQUEST_COLUMNS} FROM "blacklist_request"'
_LOCK_REQUEST = f'SELECT {_REQUEST_COLUMNS} FROM "blacklist_request" WHERE "request_id" = %s FOR UPDATE'
_UPDATE_DECISION = f"""
UPDATE "blacklist_request" SET "status" = %s, "decided_by" = %s, "decided_at" = %s, "decision_note" = %s
WHERE "request_id" = %s RETURNING {_REQUEST_COLUMNS}
"""
_ENTRY_COLUMNS = """
"entry_id", "customer_ref", "request_id", "approved_at", "expires_at", "released_at", "released_by",
"release_reason", "note"
"""
_INSERT_ENTRY = """
INSERT INTO "blacklist_entry" ("customer_ref", "request_id", "approved_at", "expires_at", "note")
VALUES (%s, %s, %s, %s, %s)
"""
_ACTIVE = ' WHERE "released_at" IS NULL AND "expires_at" > %s'
_FIND_ACTIVE = f'SELECT {_ENTRY_COLUMNS} FROM "blacklist_entry" WHERE "customer_ref" = %s AND "released_at" IS NULL AND "expires_at" > %s'
_RELEASE = f"""
UPDATE "blacklist_entry" SET "released_at" = %s, "released_by" = %s, "release_reason" = %s
WHERE "entry_id" = %s AND "released_at" IS NULL RETURNING {_ENTRY_COLUMNS}
"""
_ENTRY_EXISTS = 'SELECT 1 FROM "blacklist_entry" WHERE "entry_id" = %s'
EXPIRED_RELEASE_REASON = "만료 — 같은 고객의 새 승인으로 닫음"
# 해제자는 비운다 — 사람이 푼 것이 아니다. 해제 시각은 실제로 끝난 시각(만료 시각)이다
_CLOSE_EXPIRED = """
UPDATE "blacklist_entry" SET "released_at" = "expires_at", "release_reason" = %s
WHERE "customer_ref" = %s AND "released_at" IS NULL AND "expires_at" <= %s
"""
_LOCK_ENTRY = f'SELECT {_ENTRY_COLUMNS} FROM "blacklist_entry" WHERE "entry_id" = %s FOR UPDATE'
_UPDATE_EXPIRY = f'UPDATE "blacklist_entry" SET "expires_at" = %s WHERE "entry_id" = %s RETURNING {_ENTRY_COLUMNS}'
_CHANGE_COLUMNS = '"change_id", "entry_id", "previous_expires_at", "new_expires_at", "changed_by", "reason", "changed_at"'
_INSERT_CHANGE = f"""
INSERT INTO "blacklist_entry_expiry_change" ("entry_id", "previous_expires_at", "new_expires_at", "changed_by", "reason", "changed_at")
VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_CHANGE_COLUMNS}
"""
# 등록이 «끝난» 시각 = 해제 시각, 해제가 없으면 만료 시각. 그 시각이 기준선보다 앞이면 비운다
_PURGE_CHANGE_REASONS = """
UPDATE "blacklist_entry_expiry_change" c SET "reason" = %s
FROM "blacklist_entry" e
WHERE c."entry_id" = e."entry_id" AND c."reason" <> %s AND COALESCE(e."released_at", e."expires_at") <= %s
RETURNING c."change_id"
"""
_PURGE_REJECTED_REQUESTS = """
UPDATE "blacklist_request" SET "reason" = %s, "context_excerpt" = %s,
    "decision_note" = CASE WHEN "decision_note" IS NULL THEN NULL ELSE %s END
WHERE "status" = 'rejected' AND "decided_at" <= %s
  AND ("reason" <> %s OR "context_excerpt" <> %s OR "decision_note" <> %s)
RETURNING "request_id"
"""
_LIST_CHANGES = f'SELECT {_CHANGE_COLUMNS} FROM "blacklist_entry_expiry_change" WHERE "entry_id" = %s ORDER BY "changed_at", "change_id"'
# 감사 로그용 — 등록을 가리지 않고 최근 것부터. `changed_at` 이 같으면 나중에 들어온 행이 위다
_LIST_RECENT_CHANGES = f'SELECT {_CHANGE_COLUMNS} FROM "blacklist_entry_expiry_change" ORDER BY "changed_at" DESC, "change_id" DESC LIMIT %s'


def _request(row) -> BlacklistRequest:
    return BlacklistRequest(
        request_id=str(row[0]), call_id=row[1], customer_ref=row[2], requested_by=row[3], reason=row[4],
        context_excerpt=row[5],
        evidence=RequestEvidence(
            call_duration_s=row[6], insult_count=row[7], threat_count=row[8], sexual_count=row[9],
            temperature_outliers=row[10],
        ),
        status=row[11], requested_at=row[12], decided_by=row[13], decided_at=row[14], evidence_snapshot_at=row[15],
        decision_note=row[16],
    )


def _entry(row) -> BlacklistEntry:
    return BlacklistEntry(
        entry_id=int(row[0]), customer_ref=row[1], request_id=str(row[2]), approved_at=row[3], expires_at=row[4],
        released_at=row[5], released_by=row[6], release_reason=row[7], note=row[8],
    )


def _change(row) -> ExpiryChange:
    return ExpiryChange(change_id=int(row[0]), entry_id=int(row[1]), previous_expires_at=row[2], new_expires_at=row[3],
                        changed_by=row[4], reason=row[5], changed_at=row[6])


def _request_id(value: str) -> int:
    try:
        return int(value)
    except ValueError as exc:
        raise BlacklistNotFound(f"요청 번호가 아닙니다: {value}") from exc


class PostgresBlacklistRepository(BlacklistPort):
    def __init__(self, connect: ConnectionFactory, now=lambda: datetime.now(timezone.utc)) -> None:
        self._connect = connect
        self._now = now

    async def save_request(self, request: BlacklistRequest) -> BlacklistRequest:
        now = self._now()
        e = request.evidence
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(_INSERT_REQUEST, (
                        request.call_id, request.customer_ref, request.requested_by, request.reason,
                        request.context_excerpt, e.call_duration_s, e.insult_count, e.threat_count, e.sexual_count,
                        e.temperature_outliers, request.requested_at or now, request.evidence_snapshot_at or now,
                    ))
                except Exception as exc:
                    # 외래키는 call·requested_by 둘인데 call 은 인터랙터가 근거를 모으며 이미 확인했다
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise UnknownAgent(f"상담원 마스터에 없는 요청자입니다: {request.requested_by}") from exc
                    raise
                row = await cur.fetchone()
            await conn.commit()
        return _request(row)

    async def list_requests(self, status: str | None = None, requested_by: str | None = None) -> list[BlacklistRequest]:
        clauses, params = [], []
        if status is not None:
            clauses.append('"status" = %s')
            params.append(status)
        if requested_by is not None:
            clauses.append('"requested_by" = %s')
            params.append(requested_by)
        sql = _LIST_REQUESTS + (" WHERE " + " AND ".join(clauses) if clauses else "")
        args = tuple(params)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql + ' ORDER BY "requested_at" DESC, "request_id" DESC', args)
                rows = await cur.fetchall()
        return [_request(r) for r in rows]

    async def decide(
        self, request_id: str, *, approve: bool, decided_by: str, expires_at: datetime | None, note: str | None
    ) -> BlacklistRequest:
        if approve and expires_at is None:
            raise BlacklistConflict("승인에는 만료 시각이 필요합니다")
        rid = _request_id(request_id)
        now = self._now()
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LOCK_REQUEST, (rid,))
                row = await cur.fetchone()
                if row is None:
                    raise BlacklistNotFound(f"요청이 없습니다: {request_id}")
                try:
                    moved = transition(_request(row), STATUS_APPROVED if approve else STATUS_REJECTED,
                                       role=ROLE_ADMIN, actor=decided_by)
                except TransitionNotAllowed as exc:
                    raise BlacklistConflict(str(exc)) from exc
                # 메모는 승인이면 등록(`blacklist_entry.note`)에, 반려면 요청(`decision_note`)에 — 한 벌만 남긴다(`decisions/316`)
                await cur.execute(_UPDATE_DECISION, (moved.status, decided_by, now, None if approve else note, rid))
                updated = await cur.fetchone()
                if approve:
                    await cur.execute(_CLOSE_EXPIRED, (EXPIRED_RELEASE_REASON, moved.customer_ref, now))
                    try:
                        await cur.execute(_INSERT_ENTRY, (moved.customer_ref, rid, now, expires_at, note))
                    except Exception as exc:
                        if getattr(exc, "sqlstate", None) == _UNIQUE_VIOLATION:
                            raise BlacklistConflict("이 고객은 이미 적용 중인 등록이 있습니다 — 해제하거나 만료를 기다리거나, 만료를 연장합니다") from exc
                        raise
            await conn.commit()
        return _request(updated)

    async def find_entry(self, customer_ref: str) -> BlacklistEntry | None:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_FIND_ACTIVE, (customer_ref, self._now()))
                row = await cur.fetchone()
        return _entry(row) if row else None

    async def list_entries(self, active_only: bool = False) -> list[BlacklistEntry]:
        sql = f'SELECT {_ENTRY_COLUMNS} FROM "blacklist_entry"'
        args: tuple = ()
        if active_only:
            sql, args = sql + _ACTIVE, (self._now(),)
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql + ' ORDER BY "approved_at" DESC, "entry_id" DESC', args)
                rows = await cur.fetchall()
        return [_entry(r) for r in rows]

    async def release_entry(self, entry_id: int, *, released_by: str, reason: str) -> BlacklistEntry:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_RELEASE, (self._now(), released_by, reason, entry_id))
                row = await cur.fetchone()
                if row is None:
                    await cur.execute(_ENTRY_EXISTS, (entry_id,))
                    exists = await cur.fetchone()
            await conn.commit()
        if row is None:
            if exists is None:
                raise BlacklistNotFound(f"등록이 없습니다: {entry_id}")
            raise BlacklistConflict("이미 해제된 등록입니다")
        return _entry(row)

    async def change_expiry(
        self, entry_id: int, *, changed_by: str, expires_at: datetime, reason: str
    ) -> tuple[BlacklistEntry, ExpiryChange]:
        now = self._now()
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LOCK_ENTRY, (entry_id,))
                row = await cur.fetchone()
                if row is None:
                    raise BlacklistNotFound(f"등록이 없습니다: {entry_id}")
                current = _entry(row)
                if current.released_at is not None:
                    raise BlacklistConflict("이미 해제된 등록입니다 — 만료를 바꿀 수 없습니다")
                if not within_cap(current.approved_at, expires_at):  # 판정은 도메인 규칙이 한다
                    raise ExpiryBeyondCap(latest_allowed_expiry(current.approved_at))
                await cur.execute(_UPDATE_EXPIRY, (expires_at, entry_id))
                updated = await cur.fetchone()
                try:
                    await cur.execute(_INSERT_CHANGE, (entry_id, current.expires_at, expires_at, changed_by, reason, now))
                except Exception as exc:
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise UnknownAgent(f"상담원 마스터에 없는 변경자입니다: {changed_by}") from exc
                    raise
                change = await cur.fetchone()
            await conn.commit()
        return _entry(updated), _change(change)

    async def list_expiry_changes(self, entry_id: int) -> list[ExpiryChange]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_ENTRY_EXISTS, (entry_id,))
                if await cur.fetchone() is None:
                    raise BlacklistNotFound(f"등록이 없습니다: {entry_id}")
                await cur.execute(_LIST_CHANGES, (entry_id,))
                rows = await cur.fetchall()
        return [_change(r) for r in rows]

    async def list_recent_expiry_changes(self, limit: int) -> list[ExpiryChange]:
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_LIST_RECENT_CHANGES, (limit,))
                rows = await cur.fetchall()
        return [_change(r) for r in rows]

    async def purge_retained_texts(self) -> RetentionPurgeResult:
        cutoff = purge_cutoff(self._now())  # 기준은 도메인 규칙이 정한다
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.execute(_PURGE_CHANGE_REASONS, (PURGED_TEXT, PURGED_TEXT, cutoff))
                changes = len(await cur.fetchall())
                await cur.execute(_PURGE_REJECTED_REQUESTS, (PURGED_TEXT, PURGED_TEXT, PURGED_TEXT, cutoff,
                                                             PURGED_TEXT, PURGED_TEXT, PURGED_TEXT))
                requests = len(await cur.fetchall())
            await conn.commit()
        return RetentionPurgeResult(retention_days=RETENTION_DAYS, cutoff=cutoff,
                                    expiry_change_reasons_purged=changes, rejected_requests_purged=requests)
