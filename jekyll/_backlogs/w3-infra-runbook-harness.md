---
title: "인프라 런북을 네 영역 하네스로 건다"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 3
priority: 4
date: 2026-09-04
paths:
  - "CLAUDE.md"
  - ".claude/scripts/*"
  - "infra/CLAUDE.md"
---

`docs/infra-runbook.md`(AWS 운영 환경 정본)가 저장소에 들어왔는데, **읽으라고 적힌 곳이 없어서**
아무도 안 읽는 문서가 될 상태였다. 로컬에서 도는 코드가 운영에서 안 뜨는 이유(주입되는 환경변수,
서비스 이름, GPU 공유 방식, 열려 있지 않은 포트)가 전부 여기에만 있다.

## 무엇을

- 루트 `CLAUDE.md` §0 에 **영역별로 읽을 절 표**를 넣었다 — server 12·16·19 / ai 11·14·15·22 /
  apps 16-2·18 / infra 전체. §3 구조에 `docs/infra-runbook.md` 와 `infra/` 를 올렸다
- 영역 규칙 네 곳에 「배포 전제」 절 — `server/CLAUDE.md` §6 · `ai/CLAUDE.md` §7 ·
  `.claude/rules/dashboard.md` §5 · **`infra/CLAUDE.md`(신규)**
- `.claude/scripts/infra_runbook_guard.py`(PreToolUse 훅) — 배포에 닿는 파일을 런북 없이 고치면
  차단하고 읽을 절을 알린다. 탈출구는 `CALLGUARD_SKIP_INFRA_CHECK=1`

## 완료 조건

- [x] 네 영역(프론트·server·ai·AWS) 전부에서 런북이 참조된다
- [x] 훅이 실제로 막는다 — 8가지 입력으로 확인(차단 4 · 통과 4)
- [x] 어긋난 곳은 고치지 않고 [미결 항목](/open-items/)에 올렸다(인프라 소관 4건)
