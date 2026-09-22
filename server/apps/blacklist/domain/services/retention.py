# Requirement: J-4, SEC-1
"""블랙리스트 자유 입력의 **보존 기간** — 끝난 지 180일이 지나면 사람이 쓴 문장을 비운다(`decisions/312`, 사용자 선택).

대상 두 가지:
- 등록이 끝난(해제 또는 만료) 뒤 180일이 지난 **만료 변경 사유**(`blacklist_entry_expiry_change.reason`)
- 반려 결정 뒤 180일이 지난 요청의 **사유·자막 발췌·반려 사유**(`blacklist_request.reason`·`context_excerpt`·`decision_note` — 마지막은 `decisions/316`) — `decisions/205` ⑤ 「조치 대상이 아닌 사람이 가장 상세한 기록을 갖는 상태」

**행을 지우지 않는다** — 건수·시각·결정은 남고 문장만 표시로 바뀐다. 180 이라는 값의 근거는 없다(절대 원칙 2) — 조직이 정하면 이 상수를 바꾼다.
순수 파이썬이다(`.importlinter` 계약 4).
"""

from __future__ import annotations

from datetime import datetime, timedelta

RETENTION_DAYS = 180
PURGED_TEXT = "(보존 기간이 지나 비움)"  # NOT NULL 컬럼이라 NULL 대신 표시를 넣는다 — 「원래 비어 있었다」 와 구분된다


def purge_cutoff(now: datetime) -> datetime:
    """이 시각 이전에 끝난 것만 비운다. 경계(정확히 180일)는 비운다."""
    return now - timedelta(days=RETENTION_DAYS)
