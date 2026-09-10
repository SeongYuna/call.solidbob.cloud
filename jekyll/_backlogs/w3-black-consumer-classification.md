---
title: "통화 종료 후 블랙컨슈머 수동 분류 카드"
assignee: "조서희"
role: "app"
status: "done"
sprint: 3
priority: 5
date: 2026-09-10
paths:
  - "apps/dashboard/src/components/BlackConsumerAction.tsx"
  - "apps/dashboard/src/lib/customerRisk/blackConsumerFlag.ts"
  - "apps/dashboard/src/store/callStore.ts"
  - "apps/dashboard/src/components/CallSummaryPanel.tsx"
requirement:
  - "C-6"
---

C-6 확장. 욕설·폭언으로 통화가 길어진 고객을 상담원이 통화 종료 시 **직접 판단**해
분류한다 — 자동 탐지가 아니다(부록 A-2, 판정은 사람이 한다). 확인 즉시 관리자에게
알림을 보낸다(현재 mock — `services/gateway` 알림 API 없음).

기존 `w2-c6-customer-risk-ui`(고객 위험 배너·PII 마스킹, 실시간)와는 다른 화면·다른
트리거다 — 이쪽은 **통화 종료 후** 상담원이 내리는 수동 판단.

## 완료 조건

- [x] 통화 요약 화면에 "고객 분류" 카드, 확인 다이얼로그 경유
- [x] 위험도 점수·"안전합니다" 류 표현 없음(부록 A-1)
- [ ] 관리자 알림 API 연동(services/gateway 쪽 미착수라 보류)
---
