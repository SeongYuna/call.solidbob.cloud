# Requirement: J-2, J-4
"""상태 전이 규칙. **상담원이 직접 등록하지 못한다**가 이 파일의 핵심이다."""

from __future__ import annotations

import pytest
from blacklist.domain.services.transitions import (
    ROLE_ADMIN,
    ROLE_AGENT,
    RoleNotAllowed,
    TransitionNotAllowed,
    should_warn_distress,
    transition,
)
from hub.app.dtos.blacklist_dto import (
    STATUS_APPROVED,
    STATUS_PENDING,
    STATUS_REJECTED,
    BlacklistRequest,
    RequestEvidence,
)


def make(status: str = STATUS_PENDING) -> BlacklistRequest:
    return BlacklistRequest(
        request_id="req-1", call_id="call-1", customer_ref="010-****-1234",
        requested_by="agent-7", reason="반복 폭언", context_excerpt="자막 ***",
        status=status,
    )


# ── 상담원은 승인할 수 없다 ──────────────────────────────────────────────
def test_상담원은_직접_승인할_수_없다():
    """기분 상한 통화 한 건으로 고객이 영구히 표시되고, 그 판단을 검토한 사람이
    아무도 없게 된다 — `decisions/204` 가 `pending` 을 반드시 거치게 한 이유다."""
    with pytest.raises(RoleNotAllowed):
        transition(make(), STATUS_APPROVED, role=ROLE_AGENT, actor="agent-7")


def test_관리자는_승인할_수_있다():
    out = transition(make(), STATUS_APPROVED, role=ROLE_ADMIN, actor="admin-1")
    assert out.status == STATUS_APPROVED
    assert out.decided_by == "admin-1"


def test_관리자는_반려할_수_있다():
    assert transition(make(), STATUS_REJECTED, role=ROLE_ADMIN,
                      actor="admin-1").status == STATUS_REJECTED


# ── 규칙표에 없는 전이는 거절한다 ────────────────────────────────────────
def test_반려된_요청은_되살릴_수_없다():
    """되살리려면 새 요청을 올린다 — 그래야 근거도 새로 붙는다."""
    with pytest.raises(TransitionNotAllowed):
        transition(make(STATUS_REJECTED), STATUS_APPROVED, role=ROLE_ADMIN, actor="admin-1")


def test_승인된_요청은_더_옮길_수_없다():
    """**해제는 요청의 상태가 아니라 등록의 상태다**(2026-09-09, `decisions/205` ②).
    두 곳에 두었더니 한쪽만 갱신돼 「요청은 해제인데 배정은 여전히 베테랑」이 되는
    길이 열려 있었다 — 해제는 `blacklist_entry.released_at` 이 담는다."""
    with pytest.raises(TransitionNotAllowed):
        transition(make(STATUS_APPROVED), STATUS_REJECTED, role=ROLE_ADMIN, actor="admin-1")


def test_요청_상태에_해제가_없다():
    """상태 집합 자체를 고정한다 — 나중에 누가 `released` 를 되넣으면 여기서 걸린다."""
    from hub.app.dtos.blacklist_dto import STATUSES
    assert STATUSES == ("pending", "approved", "rejected")


def test_원본을_바꾸지_않는다():
    original = make()
    transition(original, STATUS_APPROVED, role=ROLE_ADMIN, actor="admin-1")
    assert original.status == STATUS_PENDING


def test_모르는_상태는_만들_수_없다():
    with pytest.raises(ValueError):
        make("어쩌구")


# ── distress 는 사유가 아니다 ────────────────────────────────────────────
def test_폭언_합계에_위기_신호가_들어가지_않는다():
    """`DASAN-MANUAL-5.4` — 도움이 필요한 사람을 차단 대상으로 올리는 것은
    정반대 방향이다."""
    e = RequestEvidence(insult_count=2, threat_count=1, distress_count=5)
    assert e.abuse_total == 3


def test_위기_신호가_있으면_화면에_경고한다():
    assert should_warn_distress(RequestEvidence(distress_count=1))
    assert not should_warn_distress(RequestEvidence(insult_count=9))


def test_위기_신호가_있어도_요청_자체를_막지는_않는다():
    """폭언과 위기가 한 통화에 같이 있을 수 있다. 판단은 사람이 한다."""
    req = BlacklistRequest(
        request_id="r", call_id="c", customer_ref="x", requested_by="a",
        reason="", context_excerpt="",
        evidence=RequestEvidence(insult_count=3, distress_count=1),
    )
    assert transition(req, STATUS_APPROVED, role=ROLE_ADMIN, actor="admin-1").status == STATUS_APPROVED
