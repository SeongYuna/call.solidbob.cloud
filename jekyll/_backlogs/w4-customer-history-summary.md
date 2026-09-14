---
title: "재상담 고객 이력 요약 카드 (필요서류 위)"
assignee: "조서희"
role: "app"
status: "done"
sprint: 4
priority: 4
date: 2026-09-14
paths:
  - "apps/call/src/components/CustomerHistorySummaryCard.tsx"
  - "apps/call/src/mock/customerHistory.ts"
---

무엇: 통화가 시작되면 이 고객이 재상담 고객일 경우, 우측 패널(필요서류 카드 위)에
지난 상담 이력 + 메모를 자동으로 보여준다. 접고 펼 수 있다.

왜: 상담원이 한두 번 본 고객에게 같은 정보를 다시 묻게 되는 문제 — 발화 시작 시점에
바로 맥락이 보이면 반복 설명을 줄일 수 있다(사용자 요청).

배치는 세 가지 안(자막 패널 위 배너 / 우측 패널 상단 배너 / 하단 독 탭) 중
사용자가 "우측 패널 상단, 필요서류 카드 위"를 선택했다.

⚠ **mock 전용이다.** 서버에 F-3(반복 문의 연결)이 없어 전화번호로 실제 과거 통화를
찾는 기능 자체가 없다 — `mock/customerHistory.ts`가 시나리오 ID에 고정으로 매단
가짜 이력이다. 실제 고객 매칭이 생기면 `getSelectedMockScenarioId()` 대신
`customer_id` 조회로 바꿔야 한다.

완료 조건:
- [x] `CustomerHistorySummaryCard.tsx` — 필요서류 탭/팝업창 탭 어느 쪽에서도 보임,
      상담기록(과거 통화 재생) 보는 중에는 안 보임
- [x] 이력 없는 고객(대부분 시나리오)은 카드 자체가 안 뜸 — "누구나 재상담"으로
      보이지 않게(절대 원칙 2)
- [x] `cd apps/call && npm run typecheck && npm run build` 통과
- [x] 사용자가 dev 서버에서 직접 확인(vi-deungbon 기본 시나리오로 재생)

근거: 사용자 요청(2026-09-14).
