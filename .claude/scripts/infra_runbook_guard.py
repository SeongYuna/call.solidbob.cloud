#!/usr/bin/env python3
"""PreToolUse 훅 — 배포에 닿는 파일을 인프라 런북 없이 고치는 것을 막는다.

CLAUDE.md §0: "배포·런타임에 닿는 작업은 `docs/infra-runbook.md` 를 먼저 읽는다."
이번 세션의 트랜스크립트에 런북을 본 흔적이 없으면 **종료 코드 2 로 차단**하고,
어느 절을 읽어야 하는지 stderr 로 알린다(= Claude 에게 전달된다).

- 대상 도구: Write · Edit · NotebookEdit(`file_path`) · Bash(파일을 쓰는 명령)
- 통과: `CALLGUARD_SKIP_INFRA_CHECK=1`
- 트랜스크립트를 읽을 수 없으면 통과시킨다(막지 못할 뿐, 잘못 막지는 않는다)
"""
import json
import os
import re
import sys

RUNBOOK = "docs/infra-runbook.md"
SENTINEL = "[infra-runbook-guard]"  # 자기 경고문을 "읽은 흔적"으로 오인하지 않기 위한 표식

# 배포에 닿는 파일 → 그 파일을 고치기 전에 읽어야 하는 절
GUARDED = [
    (re.compile(r"(^|/)infra/"), "10~16장(k3s·이미지·Caddy) · 「만들지 말 것」"),
    (re.compile(r"(^|/)\.github/workflows/"), "13장(이미지 빌드) · 21~22장(자동 중지·측정 인스턴스)"),
    (re.compile(r"(^|/)server/core/config\.py$"), "12-2(DB 시크릿) · 16-1(주입되는 환경변수)"),
    (re.compile(r"(^|/)\.env\.example$"), "12-2 · 16-1(운영에서 주입되는 키 목록)"),
    (re.compile(r"(^|/)(Dockerfile\S*|Caddyfile|(docker-)?compose[^/]*\.ya?ml)$"), "13장(이미지 반입) · 16장 · 「되돌리기」"),
    (re.compile(r"(^|/)db/schema\.sql$"), "17장(RDS 에 스키마를 넣는 경로)"),
]

# Bash 로 파일을 쓸 때 쓰이는 형태. 읽기만 하는 명령(cat·grep·sed -n)은 막지 않는다.
WRITE_ISH = re.compile(r">|\btee\b|\bsed\b[^|;]*\s-i\b|\bcp\b|\bmv\b|\brm\b|\bpatch\b|\btruncate\b")


def guarded_hit(text):
    """text 안에서 보호 대상 경로를 찾으면 (경로조각, 읽을절) 을 돌려준다."""
    for token in re.findall(r"[\w./\\-]+", text or ""):
        for pattern, sections in GUARDED:
            if pattern.search(token):
                return token, sections
    return None, None


def runbook_seen(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return True  # 확인할 수 없으면 막지 않는다
    try:
        with open(transcript_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if SENTINEL in line:
                    continue
                if "infra-runbook" in line:
                    return True
    except OSError:
        return True
    return False


def main():
    if os.environ.get("CALLGUARD_SKIP_INFRA_CHECK"):
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if tool == "Bash":
        command = tool_input.get("command") or ""
        if not WRITE_ISH.search(command):
            return 0
        target, sections = guarded_hit(command)
    else:
        path = tool_input.get("file_path") or tool_input.get("path") or ""
        target, sections = guarded_hit(path)

    if not target:
        return 0
    if runbook_seen(payload.get("transcript_path")):
        return 0

    print(f"{SENTINEL} '{target}' 는 배포에 닿는 파일이다.", file=sys.stderr)
    print(f"이번 세션에서 {RUNBOOK} 를 아직 보지 않았다 — 먼저 읽고 다시 시도한다.", file=sys.stderr)
    print(f"  읽을 곳: {sections}", file=sys.stderr)
    print(f"  예) sed -n '/^## 16\\./,/^## 17\\./p' {RUNBOOK}", file=sys.stderr)
    print("근거: CLAUDE.md §0 · infra/CLAUDE.md. 판정이 틀렸으면 CALLGUARD_SKIP_INFRA_CHECK=1 로 통과시킨다.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
