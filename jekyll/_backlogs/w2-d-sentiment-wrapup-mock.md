---
title: "D 상담 분위기 랩업 mock"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 4
date: 2026-08-31
paths:
  - "apps/dashboard/src/components/WrapUpPanel.tsx"
  - "apps/dashboard/src/types/contract.ts"
  - "apps/dashboard/src/mock/sentiment.ts"
requirement:
  - "D"
---

감정분석 모델은 `ai/` 몫. 화면은 정성 라벨과 C-6 건수만 보여 준다. 점수는 없다.

## 완료 조건

- `SentimentSummary` 임시 타입. open-items에 §7.3 공백 등록
- 콜가드 있는 통화는 「주의 필요」, 없는 통화는 「양호」
---
