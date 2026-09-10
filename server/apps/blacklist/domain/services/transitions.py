# Requirement: J-2, J-4
"""블랙리스트 상태 전이 — **누가 무엇을 할 수 있는가**를 규칙으로 고정한다.

근거: `_project/decisions/204`. 순수 파이썬이다(`.importlinter` 계약 4).

```
(없음) ──[상담원 요청 J-1]──▶ pending ──[관리자 승인 J-4]──▶ approved
                                 │
                                 └──[관리자 반려]──▶ rejected
```

**해제는 여기 없다**(2026-09-09, `_project/decisions/205` ②). 해제는 **등록의 상태**이지
요청의 상태가 아니다 — `blacklist_entry.released_at` 이 담는다. 두 곳에 두었더니
한쪽만 갱신돼 「요청은 해제인데 배정은 여전히 베테랑」이 되는 길이 열려 있었다.

**`pending` 을 반드시 거친다.** 상담원이 바로 `active` 로 올릴 수 있으면 그 자체가
사고다 — 기분 상한 통화 한 건으로 고객이 영구히 표시되고, 그 판단을 검토한 사람이
아무도 없게 된다.
"""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    BlacklistRequest,
    RequestEvidence,
)

# 관리자만 할 수 있는 전이. 상담원 역할로 요청하면 거부한다.
ROLE_AGENT = "agent"
ROLE_ADMIN = "admin"

_ALLOWED: dict[str, dict[str, str]] = {
    STATUS_PENDING: {STATUS_APPROVED: ROLE_ADMIN, STATUS_REJECTED: ROLE_ADMIN},
    # 승인·반려는 끝이다. 되살리려면 **새 요청**을 올린다 — 그래야 근거도 새로 붙는다.
    STATUS_APPROVED: {},
    STATUS_REJECTED: {},
}


class TransitionNotAllowed(ValueError):
    """규칙표에 없는 전이. **판정하지 않고 거절한다** — `UnknownClosureType` 과 같은 태도다."""


class RoleNotAllowed(PermissionError):
    """전이는 가능하지만 그 역할이 할 수 없다. 상담원의 직접 승인이 여기서 막힌다."""


def transition(request: BlacklistRequest, to: str, *, role: str, actor: str) -> BlacklistRequest:
    """상태를 옮긴 새 요청을 돌려준다. 원본은 바꾸지 않는다(frozen dataclass)."""
    allowed = _ALLOWED.get(request.status, {})
    if to not in allowed:
        raise TransitionNotAllowed(
            f"'{request.status}' 에서 '{to}' 로 옮길 수 없습니다 "
            f"(가능: {', '.join(allowed) or '없음'})"
        )
    if allowed[to] != role:
        raise RoleNotAllowed(
            f"'{to}' 로의 전이는 {allowed[to]} 만 할 수 있습니다 (요청 역할: {role})"
        )
    return BlacklistRequest(
        request_id=request.request_id,
        call_id=request.call_id,
        customer_ref=request.customer_ref,
        requested_by=request.requested_by,
        reason=request.reason,
        context_excerpt=request.context_excerpt,
        evidence=request.evidence,
        status=to,
        requested_at=request.requested_at,
        decided_by=actor,
        decided_at=None,  # 시각은 어댑터가 저장 시점에 넣는다 — 도메인은 시계를 모른다
    )


def should_warn_distress(evidence: RequestEvidence) -> bool:
    """위기 신호가 섞인 요청인가.

    `DASAN-MANUAL-5.4` — 자해·극단적 선택 암시는 폭언과 **다르게** 다룬다.
    도움이 필요한 사람을 차단 대상으로 올리는 것은 정반대 방향이라, 화면이 이 경우
    **전문 기관 연결 안내를 대신 띄워야** 한다. 요청 자체를 막지는 않는다 —
    폭언과 위기가 한 통화에 같이 있을 수 있고, 판단은 사람이 한다.
    """
    return evidence.has_distress
