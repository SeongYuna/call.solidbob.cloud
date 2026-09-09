---
title: "상담원 대기화면"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 4
date: 2026-09-01
paths:
  - "apps/dashboard/src/components/AgentStandbyScreen.tsx"
  - "apps/dashboard/src/App.tsx"
  - "apps/dashboard/src/hooks/useGatewaySession.ts"
---

로그인 직후(앱 시작)는 대기화면. 통화 시작 후에만 2단 어시스트와 mock 게이트웨이를 연다.

## 완료 조건

- KPI 4장·시간대 그래프·상담기록 리스트·통화 시작 CTA
- 기록 클릭 → 요약, 돌아가면 대기화면
---
