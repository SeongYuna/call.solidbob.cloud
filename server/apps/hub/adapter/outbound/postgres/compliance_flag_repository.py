# Requirement: C-1, C-2, C-3, C-4, D-4, SEC-1
"""ComplianceFlagRecordPort 의 PostgreSQL 구현 — `compliance_flag` 에 append 한다.

- `phrase` 는 **마스킹된 상담원 발화 기준**이다. 이 어댑터는 원문을 손에 넣을 경로가 없다
- `(call_id, segment_id)` 가 `transcript_segment` 를 참조한다 — 전사가 먼저 저장돼 있어야 한다.
  콜 미디에이터는 `POST /hub/transcripts` 응답을 받은 뒤에 검사를 부른다. 없으면 `CallNotStartedError`
  (23503) — 인터랙터가 잡아 로그로 남기고 응답은 그대로 내보낸다
- `rule_code` 는 `compliance_rule` 카탈로그(NOT NULL FK)를 참조하는데 **그 테이블을 채우는 경로가 없었다**
  (2026-09-18 확인 — 로컬 DB 0행, 시드 스크립트 없음). 그래서 저장 직전에 카탈로그 행을 **같은 트랜잭션에서
  UPSERT** 한다(`ON CONFLICT DO NOTHING` — 사람이 고친 label·suggestion 은 덮지 않는다).
  카탈로그 값의 출처는 `ai/apps/compliance/domain/value_objects/rules.py` 의 갈래표(MANUAL 조항)다.
  ⚠ `default_severity` 는 스키마가 NOT NULL 인데 기획서·매뉴얼 어디에도 등급 정의가 없다 — **네 코드 모두 같은 값**
  (`medium`)으로 두어 등급을 매기지 않는다는 뜻을 남긴다(부록 A-1 「위험도」 금지). 팀이 정하면 이 표만 고친다
"""

from __future__ import annotations

from datetime import datetime, timezone

from hub.app.dtos.compliance_finding_dto import ComplianceFinding
from hub.app.ports.output.compliance_flag_record_port import ComplianceFlagRecordPort
from hub.app.ports.output.transcript_ingest_record_port import CallNotStartedError

from .connection import ConnectionFactory

_FOREIGN_KEY_VIOLATION = "23503"

# rule_code → (label, default_severity, suggestion). label 은 rules.py 갈래표, suggestion 은 C-4 대체 표현의 근거 조항
# (ERD: 「도메인별 MANUAL 문서의 1.4절」). 등급은 위 머리말 — 전부 같은 값.
COMPLIANCE_RULE_CATALOG: dict[str, tuple[str, str, str]] = {
    "C-1": ("확정적 보장 · 금액·기간 단정", "medium", "DASAN-MANUAL-1.4"),
    "C-2": ("불필요한 개인정보 요구", "medium", "DASAN-MANUAL-1.2"),
    "C-3": ("근거 없는 안내 · 위임장 안내 누락 · 비공개 정보 전달 약속", "medium", "DASAN-MANUAL-1.4"),
    "C-4": ("의학적 안심 발언", "medium", "DASAN-MANUAL-4.1"),
}

_UPSERT_RULE = """
INSERT INTO "compliance_rule" ("rule_code", "label", "default_severity", "suggestion")
VALUES (%s, %s, %s, %s)
ON CONFLICT ("rule_code") DO NOTHING
"""

# `confidence` 는 NULL — 규칙 v1 은 확신도를 내지 않고, 지어내지 않는다(절대 원칙 2).
_INSERT = """
INSERT INTO "compliance_flag" ("call_id", "segment_id", "rule_code", "phrase", "confidence", "detected_at")
VALUES (%s, %s, %s, %s, NULL, %s)
"""

# `compliance_flag.phrase` VARCHAR(200). 넘치면 DB 가 거부해 위반 전체를 잃는다 — 잘라서라도 남긴다.
_PHRASE_MAX = 200


class PostgresComplianceFlagRepository(ComplianceFlagRecordPort):
    def __init__(self, connect: ConnectionFactory) -> None:
        self._connect = connect

    async def record(self, call_id: str, segment_id: int, findings: tuple[ComplianceFinding, ...]) -> None:
        unknown = sorted({f.rule_code for f in findings} - COMPLIANCE_RULE_CATALOG.keys())
        if unknown:
            # 스포크가 카탈로그 밖 코드를 냈다 — 카탈로그 행을 지어내지 않고 500 으로 드러낸다
            raise RuntimeError(f"compliance_rule 카탈로그에 없는 코드: {', '.join(unknown)}")
        now = datetime.now(timezone.utc)
        rules = sorted({f.rule_code for f in findings})
        rows = [(call_id, segment_id, f.rule_code, f.phrase[:_PHRASE_MAX], now) for f in findings]
        async with self._connect() as conn:
            async with conn.cursor() as cur:
                await cur.executemany(_UPSERT_RULE, [(code, *COMPLIANCE_RULE_CATALOG[code]) for code in rules])
                try:
                    await cur.executemany(_INSERT, rows)
                except Exception as exc:
                    # 카탈로그는 방금 넣었으니 남은 외래키는 transcript_segment 하나 — 전사가 먼저 오지 않았다
                    if getattr(exc, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                        raise CallNotStartedError(call_id) from exc
                    raise
            await conn.commit()
