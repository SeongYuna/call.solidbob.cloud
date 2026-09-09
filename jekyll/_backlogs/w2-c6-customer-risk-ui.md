---
title: "C-6 고객 위험 배너·PII 마스킹 mock"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 4
date: 2026-08-31
paths:
  - "apps/dashboard/src/lib/customerRisk/"
  - "apps/dashboard/src/components/CustomerRiskBanner.tsx"
  - "apps/dashboard/src/components/TranscriptPanel.tsx"
  - "apps/dashboard/src/mock/scenarios/dasan.ts"
requirement:
  - "C-6"
---

C-1~C-4 상담원 배너와 반대 방향. 고객 발화만 `detectCustomerRisk`로 본다.

## 완료 조건

- abuse/distress 배너 + 슈퍼바이저 알림 목업(`onSupervisorAlert`)
- pii는 배너 없이 인라인 마스킹 + 자물쇠
- 기본 시나리오(등본)에 세 유형 발화 포함
---
