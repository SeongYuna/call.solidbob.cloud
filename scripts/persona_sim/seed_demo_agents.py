# Requirement: J-5
"""시연 상담원을 운영 `agent` 에 만든다 — 페르소나 A01~A06 을 실제 행으로, 근속은 입사일로(`decisions/321`).

J-5 판정은 `agent.hired_on` 으로 근속을 센다. 페르소나 상담원은 대본 배역일 뿐 `agent` 행이 없어서,
SYN-007(기대값 `routing: veteran`)이 돌 수 없었다. 이 스크립트가 —

1. `POST /admin/agent-tokens {agent_id: "demo-A03"}` 로 행을 만든다(없으면 만든다, `decisions/406`) —
   **발급된 토큰은 찍지 않고 곧바로 폐기한다.** 행을 만드는 길이 토큰 발급뿐이라서다. 쓰지 않는 자격증명을 남기지 않는다
2. `PUT /admin/agents/{id}/hired-on` 로 입사일 = 오늘 − 페르소나 `tenure_years`
3. 콜 미디에이터 `ROUTING_CANDIDATES` 에 넣을 값을 찍는다(미디에이터 시크릿·매니페스트는 사람이 넣는다 — 런북 12-2-b 옆)

⚠ 입사일은 **시연용 값**이다(페르소나 설정에서 계산) — 측정값도 인사 기록도 아니다(절대 원칙 2).

    ADMIN_ACCESS_TOKEN=… .venv/bin/python scripts/persona_sim/seed_demo_agents.py --core-url https://server.solidbob.cloud
    … --dry-run   # 무엇을 할지만 찍는다(요청 없음)

관리자 access token 은 관리자 화면에 구글로 로그인해 얻는다. 명령줄 인자로 받지 않는다(셸 기록에 남는다).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

PERSONAS_FILE = Path(__file__).resolve().parent / "dasan-v0" / "personas.json"
DAYS_PER_YEAR = 365.25  # 근속 계산과 같은 기준(`postgres_agent_routing_adapter.py`)


@dataclass(frozen=True)
class DemoAgent:
    agent_id: str
    label: str
    hired_on: date


def plan_demo_agents(personas: dict, today: date) -> list[DemoAgent]:
    agents = personas["agents"]
    return [
        DemoAgent(agent_id=f"demo-{key}", label=spec["label"],
                  hired_on=today - timedelta(days=round(float(spec["tenure_years"]) * DAYS_PER_YEAR)))
        for key, spec in sorted(agents.items())
    ]


def routing_candidates(plan: list[DemoAgent]) -> str:
    return ",".join(a.agent_id for a in plan)


def _request(method: str, url: str, token: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as res:
        return json.loads(res.read().decode("utf-8"))


def seed(core_url: str, token: str, plan: list[DemoAgent]) -> None:
    for a in plan:
        issued = _request("POST", f"{core_url}/admin/agent-tokens", token, {"agent_id": a.agent_id})
        _request("POST", f"{core_url}/admin/agent-tokens/{issued['item']['id']}/revoke", token)  # 토큰 값은 찍지 않는다
        saved = _request("PUT", f"{core_url}/admin/agents/{a.agent_id}/hired-on", token, {"hired_on": a.hired_on.isoformat()})
        print(f"  {saved['agent_id']:<10} {a.label:<16} 입사일 {saved['hired_on']}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--core-url", default=os.environ.get("CORE_API_URL", "http://localhost:8000"))
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    plan = plan_demo_agents(json.loads(PERSONAS_FILE.read_text(encoding="utf-8")), date.today())
    if args.dry_run:
        for a in plan:
            print(f"  {a.agent_id:<10} {a.label:<16} 입사일 {a.hired_on.isoformat()}")
    else:
        token = os.environ.get("ADMIN_ACCESS_TOKEN", "").strip()
        if not token:
            print("ADMIN_ACCESS_TOKEN 이 없다 — 관리자 화면에 로그인해 access token 을 환경변수로 준다", file=sys.stderr)
            return 2
        try:
            seed(args.core_url.rstrip("/"), token, plan)
        except urllib.error.HTTPError as exc:
            print(f"실패: {exc.code} {exc.url}", file=sys.stderr)  # 본문은 찍지 않는다
            return 1
    print(f"\nROUTING_CANDIDATES={routing_candidates(plan)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
