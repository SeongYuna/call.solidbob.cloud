# Requirement: J-5
"""베테랑 배정 — 블랙리스트 고객의 전화를 숙련 상담사에게 보낸다.

근거: `_project/decisions/204`. 순수 파이썬이다(`.importlinter` 계약 4).

**C-6 과 목적은 같고 시점이 다르다.** C-6 은 통화 중에 경고해 상담원을 보호하고,
여기는 **애초에 배정하지 않아서** 보호한다. 가장 확실한 보호는 뒤쪽이다.
"""

from __future__ import annotations

from hub.app.dtos.blacklist_dto import AgentProfile, RoutingDecision

# 「베테랑」의 1차 기준. **코드에 굳히지 않고 설정으로 뺀다** — 조직마다 다르고,
# 우리에게 「3년이 옳다」는 근거가 없다(절대 원칙 2). 이 상수는 기본값일 뿐이다.
DEFAULT_VETERAN_YEARS = 3.0


def route(
    *,
    customer_ref: str,
    is_blacklisted: bool,
    candidates: list[AgentProfile],
    veteran_years: float = DEFAULT_VETERAN_YEARS,
) -> RoutingDecision:
    """배정할 상담사를 고른다.

    **블랙리스트가 아니면 아무것도 하지 않는다** — 기존 배정을 그대로 두고 `agent_id` 를
    비워 돌려준다. 이 함수는 인입 경로에 얹는 **얇은 필터**이지 배정 규칙 자체가 아니다
    (`decisions/204` 「되돌리는 법」 2).

    **베테랑이 없으면 일반 배정으로 떨어뜨린다.** 전화를 못 받게 만드는 것이 더 나쁘다.
    다만 `fell_back` 으로 남겨 「베테랑이 부족하다」를 셀 수 있게 한다.
    """
    available = [a for a in candidates if a.available]
    if not is_blacklisted:
        return RoutingDecision(
            agent_id=None, is_blacklisted=False, fell_back=False,
            reason="블랙리스트 아님 — 기존 배정 규칙을 따른다",
        )

    veterans = [a for a in available if a.tenure_years >= veteran_years]
    if veterans:
        # 근속이 긴 순, 같으면 ID 순 — **같은 입력이면 같은 결과**여야 테스트가 성립한다
        pick = sorted(veterans, key=lambda a: (-a.tenure_years, a.agent_id))[0]
        return RoutingDecision(
            agent_id=pick.agent_id, is_blacklisted=True, fell_back=False,
            reason=f"블랙리스트 고객 — 근속 {pick.tenure_years:.1f}년 상담사에게 배정",
        )

    if available:
        pick = sorted(available, key=lambda a: (-a.tenure_years, a.agent_id))[0]
        return RoutingDecision(
            agent_id=pick.agent_id, is_blacklisted=True, fell_back=True,
            reason=f"⚠ 근속 {veteran_years:.0f}년 이상 상담사가 없어 일반 배정으로 떨어졌다",
        )

    return RoutingDecision(
        agent_id=None, is_blacklisted=True, fell_back=True,
        reason="⚠ 배정 가능한 상담사가 없다",
    )
