# Requirement: J-2, J-4, J-5
"""블랙리스트 전환 요청·등록 계약. 근거: `_project/decisions/204`.

**시스템은 판정하지 않는다.** 상담원이 요청하고 관리자가 결정한다 — 여기 있는 것은
그 결정을 사람이 내릴 수 있게 **근거를 모아 나르는 형태**다. C-6 이 「탐지와 경고까지」인
것과 같은 선이다(`DASAN-MANUAL-5.2`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# 상태 기계 (`decisions/204`). 상담원은 `pending` 까지만 만들 수 있다 —
# 바로 `active` 로 올릴 수 있으면 통화 한 건으로 고객이 영구히 표시되고,
# 그 판단을 검토한 사람이 아무도 없게 된다.
# 2026-09-09 스키마 QA 로 좁혔다(`_project/decisions/205` ②) — **요청의 상태만** 담는다.
# `released` 는 등록(`BlacklistEntry`)의 상태이지 요청의 상태가 아니다. 두 곳에 두었더니
# 한쪽만 갱신돼 「요청은 released 인데 배정은 여전히 베테랑」이 되는 길이 열려 있었다.
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUSES = (STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED)


@dataclass(frozen=True)
class RequestEvidence:
    """관리자가 **통화를 다시 듣지 않고** 판단할 수 있게 싣는 근거.

    ⚠ **전부 셀 수 있는 건수다.** 위험도 점수를 만들지 않는다(부록 A-1). 「폭언 3건 ·
    통화 22분」은 사실이고 「위험도 78%」는 근거 없는 정밀함이다.

    ⚠ **`distress_count` 는 블랙리스트 사유가 아니다.** `DASAN-MANUAL-5.4` 가 위기 신호를
    폭언과 다르게 다루라고 정한다 — 도움이 필요한 사람을 차단 대상으로 올리는 것은
    정반대 방향이다. 세어서 **화면에 경고로 띄우기 위해** 싣는다(`abuse_total` 에서 빠진다).
    """

    call_duration_s: int = 0
    insult_count: int = 0
    threat_count: int = 0
    sexual_count: int = 0
    # ⚠ **저장되지 않는다.** 요청 화면의 경고를 띄우기 위한 **일회성 값**이고,
    # `blacklist_request` 테이블에 대응 컬럼이 없다(`decisions/205` ④).
    # 자해·극단적 선택 암시 건수는 정신건강에 관한 정보라, 고객 식별자와 같은 행에
    # 무기한 남기면 「이 사람이 자해를 N회 암시했다」는 레코드가 된다.
    # 화면에 필요한 것은 `has_distress` 불리언 하나다.
    distress_count: int = 0
    temperature_outliers: int = 0    # D-5 통화 온도 이상 구간 수(`decisions/203`)

    @property
    def abuse_total(self) -> int:
        """폭언 갈래 합계. **`distress` 를 넣지 않는다.**"""
        return self.insult_count + self.threat_count + self.sexual_count

    @property
    def has_distress(self) -> bool:
        return self.distress_count > 0


@dataclass(frozen=True)
class BlacklistRequest:
    """상담원이 올린 전환 요청 1건.

    `context_excerpt` 는 **마스킹된 자막**이다 — 원문이 아니다(`DASAN-MANUAL-5.5`·C-5).
    원문을 실으면 마스킹을 앞단에 둔 의미가 사라진다.
    """

    request_id: str
    call_id: str
    customer_ref: str            # ⚠ **전화번호의 HMAC.** 평문을 넣지 않는다(`decisions/205` ③)
    requested_by: str            # 상담원 식별자
    reason: str                  # 상담원이 적은 사유
    context_excerpt: str         # ⚠ 마스킹된 자막
    evidence: RequestEvidence = field(default_factory=RequestEvidence)
    status: str = STATUS_PENDING
    requested_at: datetime | None = None
    decided_by: str | None = None
    decided_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"'{self.status}' 는 블랙리스트 상태가 아닙니다 "
                             f"(가능: {', '.join(STATUSES)})")


@dataclass(frozen=True)
class BlacklistEntry:
    """등록 **에피소드** 1건. 배정(J-5)이 보는 것은 이쪽이다.

    ⚠ 「고객 1명 = 1행」이 아니다(`decisions/205` ②). 해제 후 재등록되면 행이 하나 더
    생기고 옛 행은 `released_at` 이 찍힌 채 남는다 — 고객을 키로 잡았더니 재등록이
    PK 위반이거나 첫 등록 이력을 덮어썼다.
    """

    entry_id: int | None
    customer_ref: str
    request_id: str
    approved_at: datetime | None = None
    # 만료가 없으면 영구 표시가 된다(`decisions/205` ⑤). 배정은
    # `released_at is None and expires_at > now` 만 본다.
    expires_at: datetime | None = None
    released_at: datetime | None = None
    released_by: str | None = None
    release_reason: str | None = None
    note: str | None = None          # **관리자 승인 메모.** 요청 사유의 사본이 아니다

    @property
    def is_active(self) -> bool:
        """지금 적용 중인가. **만료를 함께 본다** — 해제만 보면 만료된 등록이 계속 산다."""
        if self.released_at is not None:
            return False
        return self.expires_at is None or self.expires_at > datetime.now(self.expires_at.tzinfo)


@dataclass(frozen=True)
class AgentProfile:
    """배정 후보 상담사. **근속 연수만 본다** — 다른 평가 지표를 여기 넣지 않는다."""

    agent_id: str
    name: str
    tenure_years: float
    available: bool = True


@dataclass(frozen=True)
class RoutingDecision:
    """J-5 배정 결과.

    `fell_back` 이 True 면 **베테랑이 없어 일반 배정으로 떨어진 것**이다. 전화를 못 받게
    만드는 것이 더 나쁘므로 떨어뜨리되, **셀 수 있게 남긴다** — 「베테랑이 부족하다」가
    운영 지표가 된다(`decisions/204`).
    """

    agent_id: str | None
    is_blacklisted: bool
    fell_back: bool
    reason: str
