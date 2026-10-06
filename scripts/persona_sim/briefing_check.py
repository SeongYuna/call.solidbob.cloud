# Requirement: F-3, E-1
"""F-3 통화 수신 전 브리핑 왕복 검사 (`decisions/220` 6절).

고객마다: 지난 통화를 실제 파이프라인으로 재생(--close 로 요약까지) → 이번 통화를 --ring-seconds 로 재생하며
벨 시간 안에 GET /hub/calls/{id}/briefing 을 부른다 → 범주를 대본 라벨과 글자 비교(규칙 채점, 절대 원칙 1).

⚠ source: synthetic — 라벨은 대본 작성자가 쓴 **상한**이다. 일반 성능은 측정 불가.
반복(--repeat)마다 **발신 번호를 바꿔** 앞 회차 통화가 지난 통화로 섞이지 않게 한다.

  .venv/bin/python scripts/persona_sim/briefing_check.py --core-url http://localhost:8001 \
      --mediator-url ws://localhost:8081 --repeat 3 --ring-seconds 15
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "persona_sim" / "dasan-briefing"
REPLAY = ROOT / "services" / "call-mediator" / "scripts" / "replay_persona_call.ts"
OUT = ROOT / "data" / "processed" / "briefing"


def score(results: list[dict]) -> dict:
    by_source: dict[str, int] = defaultdict(int)
    cats: dict[str, set] = defaultdict(set)
    match = 0
    for r in results:
        by_source[r.get("source") or "none"] += 1
        cats[r["script"]].add(r.get("category"))
        if r.get("category") is not None and r.get("category") == r["expected"]:
            match += 1
    return {"n": len(results), "match": match,
            "timeouts": sum(1 for r in results if r.get("status") is None), "by_source": dict(by_source),
            "unstable": sorted(s for s, c in cats.items() if len(c) > 1)}


def phone_for(stamp_digits: str, run: int, k: int) -> str:
    """호출(invocation)마다 다른 11자리 가짜 번호 — 앞 호출의 통화가 지난 통화로 섞이지 않게 한다."""
    return f"010{int(stamp_digits) % 9973:04d}{run % 100:02d}{k % 100:02d}"


def _replay(path: Path, call_id: str, phone: str, args, ring: int = 0, close: bool = True) -> subprocess.Popen:
    cmd = ["node", "--experimental-strip-types", str(REPLAY), str(path), "--url", args.mediator_url,
           "--call-id", call_id, "--speed", str(args.speed)]
    if close:
        cmd += ["--close", "--core-url", args.core_url]
    if ring:
        cmd += ["--ring-seconds", str(ring)]
    env = {**os.environ, "CALLER_PHONE": phone}
    return subprocess.Popen(cmd, cwd=REPLAY.parents[1], env=env)


def _briefing(core_url: str, call_id: str, deadline: float, proc: subprocess.Popen | None = None) -> tuple[dict | None, float]:
    token = os.environ.get("INGEST_SERVICE_TOKEN", "").strip()
    headers = {"authorization": f"Bearer {token}"} if token else {}
    t0 = time.monotonic()
    while time.monotonic() < deadline:
        req = urllib.request.Request(f"{core_url}/hub/calls/{call_id}/briefing", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read()), (time.monotonic() - t0) * 1000
        except urllib.error.HTTPError as e:
            if e.code != 404:   # 404 = 통화가 아직 안 만들어졌다 — 다시 본다
                if proc is not None:
                    proc.terminate()
                raise SystemExit(f"브리핑 API {e.code} — 토큰(INGEST_SERVICE_TOKEN)·서버 주소를 확인하세요")
        time.sleep(0.3)
    return None, (time.monotonic() - t0) * 1000


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--core-url", default="http://localhost:8001")
    p.add_argument("--mediator-url", default="ws://localhost:8081")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--ring-seconds", type=int, default=15)
    p.add_argument("--speed", type=float, default=4.0)
    args = p.parse_args()

    loaded = {}
    for f in sorted(SCRIPTS.glob("SYN-*.json")):
        d = json.loads(f.read_text())
        loaded[d["id"]] = (f, d)
    currents = [(sid, s) for sid, (_, s) in loaded.items() if s.get("expected", {}).get("briefing", {}).get("role") == "current"]
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    results = []
    for run in range(1, args.repeat + 1):
        for k, (sid, script) in enumerate(currents):
            phone = phone_for(stamp.replace("T", ""), run, k)   # 호출·회차·고객마다 다른 가짜 번호
            for prior_id in script["expected"]["briefing"]["prior"]:
                proc = _replay(loaded[prior_id][0], f"brief-{prior_id.lower()}-{stamp}-r{run}", phone, args)
                if proc.wait() != 0:
                    raise SystemExit(f"{prior_id} 재생 실패")
            call_id = f"brief-{sid.lower()}-{stamp}-r{run}"
            proc = _replay(loaded[sid][0], call_id, phone, args, ring=args.ring_seconds, close=False)
            body, ms = _briefing(args.core_url, call_id, time.monotonic() + args.ring_seconds, proc)
            try:
                rc = proc.wait(timeout=600)
            except subprocess.TimeoutExpired:
                proc.kill()
                rc = -1
            if rc != 0:
                print(f"  ⚠ {sid} 재생 종료 코드 {rc}")
            purpose = (body or {}).get("purpose") or {}
            results.append({"script": sid, "run": run, "expected": script["expected"]["briefing"]["purpose_category"],
                            "status": (body or {}).get("status"), "category": purpose.get("category"),
                            "source": purpose.get("source"), "text": purpose.get("text"),
                            "lines": (body or {}).get("briefing_lines"), "ms_until_ready": round(ms), "replay_ok": rc == 0})
            print(f"  r{run} {sid}: {purpose.get('category')} ({purpose.get('source')}) · 기대 {results[-1]['expected']} · {round(ms)}ms")
    s = score(results)
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"briefing-check-{stamp}.json"
    out.write_text(json.dumps({"score": s, "results": results, "args": vars(args), "source": "synthetic"},
                              ensure_ascii=False, indent=1))
    print(f"\n{s['match']}/{s['n']} 일치 · 출처 {s['by_source']} · 흔들림 {s['unstable']} → {out}")


if __name__ == "__main__":
    main()
