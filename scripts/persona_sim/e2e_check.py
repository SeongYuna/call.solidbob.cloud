#!/usr/bin/env python3
# Requirement: A-3, C-5, C-6, F-2, D-1, SEC-1
"""합성 통화 E2E 왕복 검사 — 대본 → 재생기 → 콜 미디에이터 → 서버 → PostgreSQL → `/ws` → 대시보드가 읽는 API 까지.

    .venv/bin/python scripts/persona_sim/e2e_check.py                       # dasan-v0 전 대본
    .venv/bin/python scripts/persona_sim/e2e_check.py --only SYN-004 SYN-006
    .venv/bin/python scripts/persona_sim/e2e_check.py --only SYN-004 --skip-replay --call-id syn-e2e-syn-004-20260918T1602
    .venv/bin/python scripts/persona_sim/e2e_check.py --dry-run             # 스택 없이 판정 로직만(대본 ↔ 빈 응답)

전제: 로컬 스택(서버 :8000 · 콜 미디에이터 :8080 · PostgreSQL · ES) — 띄우는 순서는 `E2E.md`.
출력: `data/processed/persona-e2e/<YYYY-MM-DD-HHMM>.json` + `.md` (gitignore — 커밋하지 않는다)

`--close`(통화 후 요약)는 상담원 토큰이 있어야 한다(`decisions/315`). 환경변수 `CALL_AGENT_TOKEN` 이 없으면 **로컬 검사 DB 에
임시 상담원 토큰을 만들어** 재생기 환경변수로만 넘기고, 끝나면 폐기한다(`e2e/agent_token.py`). DB·서버가 루프백이 아니면
만들지 않는다 — 운영 DB 에는 쓰지 않는다. 토큰 값은 어디에도 찍지 않는다.

판정은 `e2e/judge.py`(순수 함수)가 한다. 이 파일은 재생기를 subprocess 로 부르고, API·DB 를 읽어 넘길 뿐이다.
재생기 stdout 은 **파싱하지 않는다** — call_id 를 내가 정해 넘기고(`--call-id`) 나머지는 API·DB 로 본다.
⚠ 여기 나온 것은 `source: synthetic` 이다 — 성능 수치가 아니다(절대 원칙 10).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from e2e import agent_token  # noqa: E402
from e2e.judge import Verdict, judge  # noqa: E402
from e2e.report import to_json, to_markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts" / "persona_sim" / "dasan-v0"
REPLAYER = ROOT / "services" / "call-mediator" / "scripts" / "replay_persona_call.ts"
OUT_DIR = ROOT / "data" / "processed" / "persona-e2e"
# infra/README.md 「로컬 개발」의 개발용 값 — 비밀이 아니다. 다른 DB 면 --database-url 또는 E2E_DATABASE_URL.
DEFAULT_DATABASE_URL = "postgresql://callguard:callguard-dev@127.0.0.1:5432/callguard_e2e"


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", nargs="*", default=[], help="대본 ID (SYN-004 …). 비우면 전부")
    p.add_argument("--skip-replay", action="store_true", help="재생하지 않고 --call-id 의 통화를 다시 판정한다")
    p.add_argument("--call-id", default="", help="--skip-replay 와 함께. 대본이 여럿이면 순서대로 여러 개")
    p.add_argument("--core-url", default=os.environ.get("CORE_API_URL", "http://localhost:8000"))
    p.add_argument("--mediator-url", default=os.environ.get("CALL_MEDIATOR_URL", "ws://localhost:8080"))
    p.add_argument("--database-url", default=os.environ.get("E2E_DATABASE_URL", DEFAULT_DATABASE_URL))
    p.add_argument("--speed", type=float, default=4.0, help="재생 배속(재생기 --speed)")
    p.add_argument("--replay-timeout", type=int, default=600, help="대본 하나의 재생 상한(초)")
    p.add_argument("--settle", type=float, default=2.0, help="재생 뒤 저장이 끝나길 기다리는 시간(초)")
    p.add_argument("--dry-run", action="store_true", help="스택 없이 판정 로직만 돌린다(전부 ❌ 가 정상)")
    p.add_argument("--out-dir", default=str(OUT_DIR))
    p.add_argument("--no-agent-token", action="store_true",
                   help="검사 DB 에 임시 상담원 토큰을 만들지 않는다(그러면 --close 가 401 — D-1 판정이 ❌)")
    args = p.parse_args(argv)
    if args.skip_replay and not args.call_id:
        p.error("--skip-replay 는 --call-id 가 필요하다")
    return args


# ---------------------------------------------------------------- 입력

def list_script_ids() -> list[str]:
    return sorted(f.stem for f in SCRIPTS_DIR.glob("SYN-*.json"))


def load_script(script_id: str) -> dict[str, Any]:
    return json.loads((SCRIPTS_DIR / f"{script_id}.json").read_text(encoding="utf-8"))


def _read_headers() -> dict[str, str]:
    """서버 읽기 경로의 문(`decisions/322`) — 서비스 토큰이 있으면 싣는다. `READ_AUTH_REQUIRED` 가 켜지면 없을 때 401 이다."""
    token = os.environ.get("INGEST_SERVICE_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def http_get(url: str) -> Any:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=_read_headers()), timeout=15) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"_http_status": exc.code, "_body": exc.read().decode("utf-8", "ignore")[:300]}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"_error": str(exc)}


def fetch_transcript(core_url: str, call_id: str) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = http_get(f"{core_url}/hub/calls/{call_id}/transcript?limit=500&offset={offset}")
        if not isinstance(page, dict) or "segments" not in page:
            return segments
        segments += page["segments"]
        total = int(page.get("total", 0))
        offset += len(page["segments"])
        if offset >= total or not page["segments"]:
            return segments


def fetch_record(core_url: str, call_id: str) -> dict[str, Any]:
    body = http_get(f"{core_url}/hub/calls/{call_id}/record")
    return body if isinstance(body, dict) else {}


def fetch_db(database_url: str, call_id: str) -> dict[str, Any]:
    """DB 스냅샷 — psycopg 가 없거나 못 붙으면 빈 dict(그 판정은 건너뛴다)."""
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("  ⚠ psycopg 가 없다 — DB 판정을 건너뛴다(.venv/bin/python 으로 실행)", file=sys.stderr)
        return {}
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute("SELECT segment_id, text FROM transcript_segment WHERE call_id=%s AND is_final ORDER BY segment_id", (call_id,))
            final_texts = {int(seg): str(text) for seg, text in cur.fetchall()}
            cur.execute("SELECT segment_id, category FROM call_guard_flag WHERE call_id=%s", (call_id,))
            call_guard = [(int(seg), str(cat)) for seg, cat in cur.fetchall()]
            cur.execute("SELECT segment_id, rule_code FROM compliance_flag WHERE call_id=%s", (call_id,))
            compliance = [(int(seg), str(code)) for seg, code in cur.fetchall()]
            cur.execute("SELECT call_id, stt_engine, status, ended_at, customer_id, summary_text FROM call WHERE call_id=%s", (call_id,))
            row = cur.fetchone()
            call = None
            if row is not None:
                call = {"call_id": row[0], "stt_engine": row[1], "status": row[2], "ended_at": row[3], "customer_id": row[4],
                        "summary_text": row[5]}
        return {"final_texts": final_texts, "call_guard": call_guard, "compliance": compliance, "call": call}
    except Exception as exc:  # noqa: BLE001 — 붙지 못한 이유를 보고서에 남기고 계속 간다
        print(f"  ⚠ DB 에 붙지 못했다 — DB 판정을 건너뛴다: {type(exc).__name__}", file=sys.stderr)
        return {}


# ---------------------------------------------------------------- 상담원 토큰 (재생기 --close)

def issue_agent_token(database_url: str, core_url: str) -> tuple[str | None, int | None]:
    """로컬 검사 DB 에 임시 상담원 토큰을 만든다 — (원문, 행 id). 못 만들면 (None, None) 과 이유를 stderr 에.
    원문은 돌려주기만 한다 — 찍지 않는다."""
    reason = agent_token.refusal_reason(database_url, core_url)
    if reason:
        print(f"  ⚠ 상담원 토큰을 만들지 않는다: {reason}. --close 가 401 이면 {agent_token.ENV_AGENT_TOKEN} 를 직접 준다", file=sys.stderr)
        return None, None
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("  ⚠ psycopg 가 없어 상담원 토큰을 만들지 못했다(.venv/bin/python 으로 실행)", file=sys.stderr)
        return None, None
    token = agent_token.new_token()
    try:
        with psycopg.connect(database_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(agent_token.INSERT_AGENT, (agent_token.E2E_AGENT_ID, agent_token.E2E_AGENT_NAME, "e2e", "agent"))
            cur.execute(agent_token.INSERT_TOKEN, (agent_token.E2E_AGENT_ID, agent_token.hash_token(token)))
            row = cur.fetchone()
            conn.commit()
    except Exception as exc:  # noqa: BLE001 — 토큰 없이도 나머지 판정은 돈다
        print(f"  ⚠ 상담원 토큰을 만들지 못했다: {type(exc).__name__}", file=sys.stderr)
        return None, None
    print(f"  상담원 토큰: 검사 DB 에 임시 발급({agent_token.E2E_AGENT_ID}) — 재생기 환경변수로만 넘기고 끝나면 폐기한다")
    return token, int(row[0]) if row else None


def revoke_agent_token(database_url: str, token_id: int) -> None:
    try:
        import psycopg  # type: ignore
        with psycopg.connect(database_url, connect_timeout=5) as conn, conn.cursor() as cur:
            cur.execute(agent_token.REVOKE_TOKEN, (token_id,))
            conn.commit()
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ 임시 상담원 토큰(id={token_id})을 폐기하지 못했다: {type(exc).__name__} — agent_token 에서 직접 revoked_at 을 채운다", file=sys.stderr)


# ---------------------------------------------------------------- 재생

def replay(script_id: str, call_id: str, args: argparse.Namespace, agent_token_value: str | None = None) -> tuple[int, str]:
    cmd = ["node", str(REPLAYER), script_id, "--call-id", call_id, "--speed", str(args.speed), "--url", args.mediator_url,
           "--watch", "--close", "--core-url", args.core_url]
    env = {**os.environ}
    if agent_token_value:
        env[agent_token.ENV_AGENT_TOKEN] = agent_token_value  # 헤더로만 나간다(재생기 close_auth.ts). 명령줄에 싣지 않는다
    try:
        proc = subprocess.run(cmd, cwd=REPLAYER.parent.parent, capture_output=True, text=True, timeout=args.replay_timeout, env=env)
    except subprocess.TimeoutExpired:
        return 124, f"재생기가 {args.replay_timeout}초 안에 끝나지 않았다"
    tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-6:])
    return proc.returncode, tail


# ---------------------------------------------------------------- 실행

def read_commit() -> tuple[str, str]:
    """`git` 이 이 머신에서 막혀 있어도(Xcode 라이선스) 커밋을 읽는다 — `.git/HEAD` → ref 파일."""
    try:
        head = (ROOT / ".git" / "HEAD").read_text().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            path = ROOT / ".git" / ref
            if path.exists():
                return path.read_text().strip()[:12], ref.rsplit("/", 1)[-1]
            packed = ROOT / ".git" / "packed-refs"
            if packed.exists():
                for line in packed.read_text().splitlines():
                    if line.endswith(" " + ref):
                        return line.split(" ", 1)[0][:12], ref.rsplit("/", 1)[-1]
            return "?", ref.rsplit("/", 1)[-1]
        return head[:12], "detached"
    except OSError:
        return "?", "?"


def run_scripts(ids: list[str], call_ids: list[str], stamp: str, args: argparse.Namespace,
                agent_token_value: str | None) -> list[Verdict]:
    verdicts: list[Verdict] = []
    for i, script_id in enumerate(ids):
        script = load_script(script_id)
        call_id = call_ids[i] if args.skip_replay else f"syn-e2e-{script_id.lower()}-{stamp}"
        print(f"[{i + 1}/{len(ids)}] {script_id} {script.get('title', '')} → {call_id}")
        if args.dry_run:
            verdicts.append(judge(script, call_id, [], {}, {}))
            continue
        if not args.skip_replay:
            code, tail = replay(script_id, call_id, args, agent_token_value)
            print(f"  재생기 종료 {code}" + (f"\n    {tail.replace(chr(10), chr(10) + '    ')}" if code != 0 else ""))
            time.sleep(args.settle)
        segments = fetch_transcript(args.core_url, call_id)
        record = fetch_record(args.core_url, call_id)
        db = fetch_db(args.database_url, call_id)
        v = judge(script, call_id, segments, record, db)
        verdicts.append(v)
        for c in v.checks:
            if not c.ok:
                print(f"  {'⚠' if c.warn_only else '❌'} {c.name} — {c.detail}")
        print(f"  → {'✅' if v.ok else '❌'} ({len(v.failed)} 실패 · {len(v.warned)} 경고)")
    return verdicts


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    ids = [s.upper() for s in args.only] or list_script_ids()
    missing = [s for s in ids if not (SCRIPTS_DIR / f"{s}.json").exists()]
    if missing:
        print(f"대본이 없다: {missing}", file=sys.stderr)
        return 2
    stamp = datetime.now().strftime("%Y%m%dT%H%M")
    call_ids = args.call_id.split(",") if args.skip_replay else []
    if args.skip_replay and len(call_ids) != len(ids):
        print(f"--call-id 는 대본 수({len(ids)})만큼 쉼표로 준다", file=sys.stderr)
        return 2

    commit, branch = read_commit()
    meta: dict[str, Any] = {
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "commit": commit + ("-dirty?" if commit != "?" else ""),
        "branch": branch,
        "core_url": args.core_url,
        "mediator_url": args.mediator_url,
        "scripts_dir": str(SCRIPTS_DIR.relative_to(ROOT)),
        "command": " ".join(["e2e_check.py", *argv]),
        "speed": args.speed,
        "dry_run": args.dry_run,
    }
    if not args.dry_run:
        meta["server_health"] = json.dumps(http_get(f"{args.core_url}/health"), ensure_ascii=False)[:300]
        meta["mediator_health"] = json.dumps(http_get(args.mediator_url.replace("ws://", "http://").replace("wss://", "https://") + "/health"), ensure_ascii=False)[:300]

    token_value: str | None = None
    token_id: int | None = None
    if not args.dry_run and not args.skip_replay and not args.no_agent_token:
        if os.environ.get(agent_token.ENV_AGENT_TOKEN, "").strip():
            print(f"  상담원 토큰: 환경변수 {agent_token.ENV_AGENT_TOKEN} 를 쓴다")
        else:
            token_value, token_id = issue_agent_token(args.database_url, args.core_url)
    try:
        verdicts = run_scripts(ids, call_ids, stamp, args, token_value)
    finally:
        if token_id is not None:
            revoke_agent_token(args.database_url, token_id)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / datetime.now().strftime("%Y-%m-%d-%H%M")
    base.with_suffix(".json").write_text(to_json(meta, verdicts), encoding="utf-8")
    base.with_suffix(".md").write_text(to_markdown(meta, verdicts), encoding="utf-8")
    passed = sum(1 for v in verdicts if v.ok)
    shown = base.with_suffix(".md")
    shown = shown.relative_to(ROOT) if shown.is_relative_to(ROOT) else shown
    print(f"\n{len(verdicts)}건 중 ✅ {passed} · ❌ {len(verdicts) - passed} → {shown}")
    return 0 if passed == len(verdicts) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
