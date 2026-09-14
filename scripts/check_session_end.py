#!/usr/bin/env python3
# Requirement: QUA-2 (기록 추적성)
"""세션 종료 검사 — Stop 훅에서 실행된다. CLAUDE.md §0.5 세션 종료 루틴의 자동화.

세 가지를 본다:
  ① 진행 기록 누락    파일을 고쳤는데 jekyll/_logs/ 에 내 오늘 기록이 없다      → 차단(exit 2)
  ② status 정합성     만진 파일이 어느 티켓 소관인데 그 티켓이 아직 todo      → 경고
  ③ 중복 티켓         슬러그가 겹치는 티켓이 둘 다 살아 있다                   → 경고

왜 ①만 차단하나
    ②③은 판정이 애매할 수 있다(파일 하나가 여러 티켓에 걸리거나, 의도된 분리일 수 있다).
    애매한 판정으로 세션을 막으면 회피가 생긴다. ① 은 "오늘 뭘 했는지 한 줄 남겼는가"라
    다툼의 여지가 없고, 실제로 이틀간 0건으로 뚫린 항목이다.

빠져나가는 법 (판정이 틀렸을 때)
    CALLGUARD_SKIP_SESSION_CHECK=1  환경변수를 주면 통과한다.
    Stop 훅이 이미 한 번 막았던 세션(stop_hook_active)은 다시 막지 않는다 — 무한 루프 방지.

사용법
    python3 scripts/check_session_end.py              # 사람이 직접 (경고만, exit 0)
    python3 scripts/check_session_end.py --hook       # Stop 훅용 (누락 시 exit 2)
"""

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "jekyll" / "_logs"
BACKLOGS = ROOT / "jekyll" / "_backlogs"

# 로그 파일명: YYYY-MM-DD-NN-사람.md  (2026-08-27 부터. 그 전에는 progress.markdown 한 파일)
LOG_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d+)-([a-z]+)\.md$")
SLUG_PREFIX = re.compile(r"^w\d+-")
IGNORED_SUBJECT = re.compile(r"^(Merge |merge:|Revert )")


def git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *args],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def front_matter(path: Path) -> dict[str, object]:
    """의존성 없이 티켓 front matter 를 읽는다 (PyYAML 미설치 환경 대비)."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    body = text.split("---", 2)[1]
    data: dict[str, object] = {}
    key = None
    for line in body.splitlines():
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and key:            # 리스트 항목
            data.setdefault(key, [])
            if isinstance(data[key], list):
                data[key].append(line.split("- ", 1)[1].strip().strip('"\''))
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.split("#", 1)[0].strip().strip('"\'')
        data[key] = val if val else []
    return data


def tickets() -> list[tuple[str, dict[str, object]]]:
    if not BACKLOGS.is_dir():
        return []
    return sorted((p.stem, front_matter(p)) for p in BACKLOGS.glob("*.md"))


# ─────────────────────────────────────────────── ① 진행 기록

LOGS_REL = "jekyll/_logs/"


def changed_today() -> tuple[list[str], list[str]]:
    """(작업 트리에서 바뀐 파일, 오늘 내가 만든 커밋 제목)"""
    # -uall: 미추적 디렉터리를 "apps/" 로 접지 않고 파일 단위로 펼친다.
    # 접힌 경로는 티켓의 paths 패턴(apps/call/*)에 걸리지 않는다.
    dirty = [ln[3:].strip() for ln in git("status", "--porcelain", "-uall").splitlines()
             if ln.strip()]

    me = git("config", "user.email").strip()
    today = date.today().isoformat()
    mine = []
    for ln in git("log", f"--since={today} 00:00", "--date=short",
                  "--pretty=format:%ae\t%s").splitlines():
        if "\t" not in ln:
            continue
        email, subject = ln.split("\t", 1)
        if me and email != me:
            continue
        if IGNORED_SUBJECT.match(subject):
            continue
        mine.append(subject)
    return dirty, mine


def i_wrote_the_log(dirty: list[str]) -> bool:
    """*내가* 오늘 진행 기록을 남겼는가.

    "오늘 날짜 기록이 있는가"로 보면 안 된다 — 팀원이 먼저 쓴 기록이 오늘 날짜라
    내 누락이 그대로 묻힌다(2026-08-26 에 실제로 이렇게 뚫렸다). 그래서
    jekyll/_logs/ 아래 파일을 이 세션에서 실제로 만들거나 고쳤는지를 본다.

    로그가 파일 1개 = 항목 1건으로 갈리면서(2026-08-27) 이 검사는 더 정확해졌다 —
    예전에는 네 명이 같은 progress.markdown 을 고쳐서, 남의 변경을 머지만 해도
    "내가 썼다"로 잡힐 수 있었다.
    """
    if any(f.startswith(LOGS_REL) for f in dirty):
        return True

    me = git("config", "user.email").strip()
    today = date.today().isoformat()
    for ln in git("log", f"--since={today} 00:00",
                  "--pretty=format:%H\t%ae").splitlines():
        if "\t" not in ln:
            continue
        sha, email = ln.split("\t", 1)
        if me and email != me:
            continue
        touched = git("show", "--name-only", "--pretty=format:", sha).splitlines()
        if any(f.startswith(LOGS_REL) for f in touched):
            return True
    return False


def progress_has_today() -> bool:
    """오늘 날짜 기록이 하나라도 있는가 (보조 확인 — 작성자는 따지지 않는다)."""
    if not LOGS.is_dir():
        return False
    today = date.today().isoformat()
    return any(m and m.group(1) == today
               for m in (LOG_NAME.match(p.name) for p in LOGS.glob("*.md")))


# ─────────────────────────────────────────────── ② status 정합성

def stale_status(changed: list[str]) -> list[tuple[str, str, list[str]]]:
    """(티켓, status, 걸린 파일들) — paths: 가 있는 티켓만 본다."""
    out = []
    for slug, fm in tickets():
        patterns = fm.get("paths")
        if not isinstance(patterns, list) or not patterns:
            continue
        if fm.get("status") != "todo":
            continue
        hit = [f for f in changed
               for pat in patterns
               if fnmatch.fnmatch(f, pat) or f.startswith(pat.rstrip("*"))]
        if hit:
            out.append((slug, str(fm.get("status")), sorted(set(hit))))
    return out


# ─────────────────────────────────────────────── ③ 중복 티켓

def duplicate_tickets() -> list[tuple[str, str]]:
    """슬러그(주차 접두어 제거)가 같거나 한쪽이 다른 쪽을 포함하는 쌍.

    걸러내는 경우
      - 둘 다 done: 이미 정리된 것으로 본다
      - 한쪽이 다른 쪽을 `depends_on:` 으로 선언: 일부러 나눈 단계다
        (예: w2-baseline 측정 → w2-baseline-gate CI 게이트)
    오탐이 잦으면 경고 자체를 무시하게 되므로, 의도적으로 나눈 티켓은 빠져나갈 길을 둔다.
    """
    data = tickets()
    items = [(slug, SLUG_PREFIX.sub("", slug), str(fm.get("status", "")),
              fm.get("depends_on") if isinstance(fm.get("depends_on"), list) else [])
             for slug, fm in data]
    pairs = []
    for i, (sa, na, ta, da) in enumerate(items):
        for sb, nb, tb, db in items[i + 1:]:
            if ta == "done" and tb == "done":
                continue
            if sb in da or sa in db:
                continue
            if na == nb or na.startswith(nb) or nb.startswith(na):
                pairs.append((sa, sb))
    return pairs


# ─────────────────────────────────────────────── 실행

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hook", action="store_true",
                    help="Stop 훅 모드 — 진행 기록 누락 시 exit 2")
    args = ap.parse_args()

    stop_hook_active = False
    if args.hook and not sys.stdin.isatty():
        try:
            stop_hook_active = bool(json.load(sys.stdin).get("stop_hook_active"))
        except Exception:
            pass

    if os.environ.get("CALLGUARD_SKIP_SESSION_CHECK"):
        return 0

    dirty, commits = changed_today()
    # 진행 기록 자체를 쓴 것은 "작업"으로 세지 않는다 (로그만 쓴 세션)
    substantive = [f for f in dirty
                   if not f.startswith(LOGS_REL) and not f.endswith("progress.markdown")]
    worked = bool(substantive or commits)
    lines: list[str] = []

    # ② ③ 은 항상 경고만
    for slug, st, hit in stale_status(substantive):
        lines.append(f"[티켓 상태] {slug} 가 아직 {st} 인데 소관 파일이 바뀌었습니다: "
                     f"{', '.join(hit[:3])}{' 외' if len(hit) > 3 else ''}")
    for a, b in duplicate_tickets():
        lines.append(f"[중복 티켓] {a} ↔ {b} — 같은 작업이 보드에 두 번 뜹니다. "
                     f"하나로 합치거나 범위를 나누세요")

    # ① 진행 기록
    missing_log = worked and not i_wrote_the_log(dirty)
    if missing_log:
        what = substantive[:4] if substantive else commits[:4]
        note = ("" if progress_has_today() else
                f"\n            (오늘 날짜 기록 자체가 없습니다 — jekyll/_logs/{date.today().isoformat()}-01-<사람>.md)")
        lines.insert(0, "[진행 기록] 이번 세션에서 파일을 고쳤는데 jekyll/_logs/ 에 "
                        "기록을 남기지 않았습니다" + note + "\n"
                        "            " + "\n            ".join(f"· {w}" for w in what))

    if not lines:
        if worked:
            print("세션 종료 검사: 통과 (진행 기록 있음)")
        return 0

    header = "세션 종료 검사 — CLAUDE.md §0.5"
    body = "\n".join(f"  {ln}" for ln in lines)

    if args.hook and missing_log and not stop_hook_active:
        print(f"{header}\n{body}\n\n"
              "  진행 기록을 남기고 끝내세요. `session-log` 스킬이 절차를 안내합니다.\n"
              "  판정이 틀렸다면: CALLGUARD_SKIP_SESSION_CHECK=1 로 통과시킬 수 있습니다.",
              file=sys.stderr)
        return 2

    print(f"{header}\n{body}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
