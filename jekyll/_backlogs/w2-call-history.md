---
title: "상담기록 mock 조회"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 5
date: 2026-08-28
paths:
  - "apps/dashboard/src/components/CallHistoryPanel.tsx"
  - "apps/dashboard/src/components/ArrowSelectChip.tsx"
  - "apps/dashboard/src/mock/callHistory.ts"
  - "apps/dashboard/src/types/contract.ts"
---

목록 API가 없어 mock으로 상담기록 칩·목록·자막 상세를 먼저 둔다.
자막 페이지 타입은 `GET /hub/calls/{call_id}/transcript` 스키마에 맞춘다.

## 완료 조건

- 칩 라벨은 항상 「상담기록」, 바깥 클릭·Escape 로 닫힘
- 목록 클릭 → 자막 상세 → 목록으로 돌아가기
- `typecheck` · `build` 통과
