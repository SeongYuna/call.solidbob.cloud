# Requirement: J-5, QUA-1
"""시연 상담원 시드 — 페르소나 근속으로 입사일을 계산하는 순수 함수만 본다(`decisions/321`). 실행: `.venv/bin/python -m pytest scripts/persona_sim/tests -q`"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from seed_demo_agents import plan_demo_agents, routing_candidates  # noqa: E402

PERSONAS = {"agents": {
    "A01": {"label": "신입 상담원", "tenure_years": 0.3},
    "A03": {"label": "베테랑 상담원", "tenure_years": 7},
}}
TODAY = date(2026, 9, 22)


def test_페르소나_근속으로_입사일을_거꾸로_계산한다():
    plan = {a.agent_id: a for a in plan_demo_agents(PERSONAS, TODAY)}
    assert plan["demo-A03"].hired_on == date(2019, 9, 22)   # 7년
    assert plan["demo-A01"].hired_on == date(2026, 6, 4)    # 0.3년 = 110일
    assert all(len(a.agent_id) <= 20 for a in plan.values())  # agent.agent_id VARCHAR(20)


def test_라우팅_후보는_쉼표로_잇는다():
    assert routing_candidates(plan_demo_agents(PERSONAS, TODAY)) == "demo-A01,demo-A03"
