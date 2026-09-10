# Requirement: J-5
"""베테랑 배정. **떨어뜨리는 경우를 세는 것**이 이 규칙의 절반이다."""

from __future__ import annotations

from blacklist.domain.services.routing import DEFAULT_VETERAN_YEARS, route
from hub.app.dtos.blacklist_dto import AgentProfile

NEWBIE = AgentProfile("a-new", "신입", tenure_years=0.5)
MID = AgentProfile("a-mid", "중견", tenure_years=2.0)
VET = AgentProfile("a-vet", "베테랑", tenure_years=5.0)
VET2 = AgentProfile("a-vet2", "베테랑2", tenure_years=8.0)


def test_블랙리스트가_아니면_아무것도_하지_않는다():
    """이 함수는 인입 경로에 얹는 **얇은 필터**이지 배정 규칙 자체가 아니다 —
    빼면 기존 배정이 그대로 돈다(`decisions/204` 되돌리는 법)."""
    d = route(customer_ref="x", is_blacklisted=False, candidates=[NEWBIE, VET])
    assert d.agent_id is None
    assert not d.fell_back


def test_블랙리스트면_베테랑에게_간다():
    d = route(customer_ref="x", is_blacklisted=True, candidates=[NEWBIE, MID, VET])
    assert d.agent_id == "a-vet"
    assert not d.fell_back


def test_베테랑이_여럿이면_근속이_긴_쪽():
    d = route(customer_ref="x", is_blacklisted=True, candidates=[VET, VET2])
    assert d.agent_id == "a-vet2"


def test_베테랑이_없으면_떨어뜨리되_기록을_남긴다():
    """전화를 못 받게 만드는 것이 더 나쁘다. 다만 「베테랑이 부족하다」를 셀 수 있어야 한다."""
    d = route(customer_ref="x", is_blacklisted=True, candidates=[NEWBIE, MID])
    assert d.agent_id == "a-mid"
    assert d.fell_back
    assert "일반 배정" in d.reason


def test_아무도_없으면_배정하지_않는다():
    d = route(customer_ref="x", is_blacklisted=True, candidates=[])
    assert d.agent_id is None
    assert d.fell_back


def test_자리에_없는_상담사는_후보가_아니다():
    busy = AgentProfile("a-vet", "베테랑", tenure_years=5.0, available=False)
    d = route(customer_ref="x", is_blacklisted=True, candidates=[busy, MID])
    assert d.agent_id == "a-mid"
    assert d.fell_back


def test_기준_연수를_바꿀_수_있다():
    """3년은 검토에서 나온 예시이지 우리가 재서 고른 값이 아니다(절대 원칙 2)."""
    assert DEFAULT_VETERAN_YEARS == 3.0
    d = route(customer_ref="x", is_blacklisted=True, candidates=[MID], veteran_years=1.0)
    assert d.agent_id == "a-mid"
    assert not d.fell_back


def test_같은_입력이면_같은_결과다():
    same = AgentProfile("b-vet", "동률", tenure_years=5.0)
    for _ in range(5):
        assert route(customer_ref="x", is_blacklisted=True,
                     candidates=[same, VET]).agent_id == "a-vet"
