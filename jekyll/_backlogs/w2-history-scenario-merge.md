---
title: "상담기록·시나리오 칩 합치기"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 4
date: 2026-08-28
paths:
  - "apps/dashboard/src/components/CallHistoryPanel.tsx"
  - "apps/dashboard/src/components/TermsPanel.tsx"
  - "apps/dashboard/src/mock/callHistory.ts"
---

시나리오 칩과 상담기록이 같은 5통을 나눠 보여 주고 있었다. 상담기록만 남기고, 언어 배지와 행 단위 다시 재생으로 시나리오를 고른다.

## 완료 조건

- 시나리오 칩 없음. 목록 5건에 🇻🇳🇺🇸🇯🇵🇨🇳🇹🇭. 행 클릭=히스토리, 재생 아이콘=실시간 mock
---
