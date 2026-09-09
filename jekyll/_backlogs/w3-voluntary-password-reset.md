---
title: "대기화면 비밀번호 재설정(자발적 모드)"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 4
date: 2026-09-04
paths:
  - "apps/dashboard/src/components/ForcePasswordSetup.tsx"
  - "apps/dashboard/src/components/AgentStandbyScreen.tsx"
  - "apps/dashboard/src/App.tsx"
---

루트(`/`)는 대기화면. 비밀번호 화면은 「비밀번호 재설정」으로만 연다. 최초 로그인 강제는 없음.

## 완료 조건

- `/` 진입 시 `AgentStandbyScreen`. `mustChangePassword` 분기 없음
- `ForcePasswordSetup` 은 `mode="voluntary"` 만. 취소·완료 후 대기화면
- 통화 시작 → 어시스트, 요약 화면은 기존과 동일
---
