# Requirement: E-1, SEC-1
"""E2E 판정 → JSON·마크다운 보고서. 순수 함수 — 파일은 `e2e_check.py` 가 쓴다.

보고서 머리에 «source: synthetic — STT 미경유 상한, 성능 수치로 인용 금지» 를 박는다(절대 원칙 2·10).
실패는 지우지 않는다(절대 원칙 8) — ❌ 는 원인 갈래와 함께 그대로 남고, ⚠ 는 알려진 미구현이다.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .judge import Verdict

DISCLAIMER = (
    "> ⚠ **`source: synthetic`** — 대본을 글자로 직접 흘렸다(STT 미경유). 여기 나온 탐지·마스킹 결과는 **상한**이고, "
    "지연 시각은 재생기가 지어낸 값이다. **성능 수치로 인용하지 않는다**(절대 원칙 2·10). "
    "이 표가 말하는 것은 «대본이 파이프라인을 왕복해 대시보드가 읽는 API 까지 돌아왔는가» 뿐이다."
)

CAUSE_LABEL = {"wiring": "배선", "rule": "규칙", "script": "대본", "known": "알려진 미구현", "": "—"}


def to_json(meta: dict[str, Any], verdicts: list[Verdict]) -> str:
    payload = {
        "source": "synthetic",
        "meta": meta,
        "summary": {
            "scripts": len(verdicts),
            "passed": sum(1 for v in verdicts if v.ok),
            "failed": sum(1 for v in verdicts if not v.ok),
        },
        "verdicts": [
            {"script_id": v.script_id, "call_id": v.call_id, "ok": v.ok, "checks": [asdict(c) for c in v.checks]}
            for v in verdicts
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=1)


def to_markdown(meta: dict[str, Any], verdicts: list[Verdict]) -> str:
    lines = [f"# 합성 통화 E2E 왕복 검사 — {meta.get('run_at', '')}", "", DISCLAIMER, ""]
    lines.append("| 항목 | 값 |")
    lines.append("|---|---|")
    for key in ("run_at", "commit", "branch", "core_url", "mediator_url", "server_health", "mediator_health", "scripts_dir", "command"):
        if key in meta:
            lines.append(f"| {key} | `{meta[key]}` |")
    passed = sum(1 for v in verdicts if v.ok)
    lines += ["", f"**{len(verdicts)}건 중 ✅ {passed} · ❌ {len(verdicts) - passed}** (⚠ 는 세지 않는다)", ""]

    lines.append("| 대본 | call_id | 결과 | 실패한 판정 (원인 갈래) | ⚠ |")
    lines.append("|---|---|---|---|---|")
    for v in verdicts:
        failed = " / ".join(f"{c.name} ({CAUSE_LABEL.get(c.cause, c.cause)})" for c in v.failed) or "—"
        warned = " / ".join(c.name for c in v.warned) or "—"
        lines.append(f"| {v.script_id} | `{v.call_id}` | {'✅' if v.ok else '❌'} | {failed} | {warned} |")

    lines += ["", "## 판정 상세", ""]
    for v in verdicts:
        lines.append(f"### {v.script_id} — {'✅' if v.ok else '❌'} `{v.call_id}`")
        lines.append("")
        for c in v.checks:
            mark = "✅" if c.ok else ("⚠" if c.warn_only else "❌")
            cause = f" _(원인 가설: {CAUSE_LABEL.get(c.cause, c.cause)})_" if not c.ok and c.cause else ""
            lines.append(f"- {mark} **{c.name}** — {c.detail}{cause}")
        lines.append("")

    causes: dict[str, list[str]] = {}
    for v in verdicts:
        for c in v.failed:
            causes.setdefault(c.cause or "", []).append(f"{v.script_id}: {c.name}")
    if causes:
        lines += ["## 실패 원인 갈래별", ""]
        for cause, items in sorted(causes.items()):
            lines.append(f"- **{CAUSE_LABEL.get(cause, cause)}** ({len(items)}) — " + " · ".join(items))
        lines.append("")
    return "\n".join(lines)
