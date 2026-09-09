---
title: "C-6 콜가드 자막 mock"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 4
date: 2026-08-31
paths:
  - "apps/dashboard/src/components/TranscriptPanel.tsx"
  - "apps/dashboard/src/types/contract.ts"
  - "apps/dashboard/src/mock/scenarios/callGuardKo.ts"
requirement:
  - "C-6"
---

`decisions/201` C-6 범위 축소. 고객 발화 텍스트만 보고 경고만 한다. 자동 차단·오디오 톤은 없다.

## 완료 조건

- `CallGuardFlag` 임시 타입. open-items에 §7.3 공백 등록
- 「🚫 콜가드」가 「⚠ 경고」와 구분됨. 통화는 끊기지 않음
---
