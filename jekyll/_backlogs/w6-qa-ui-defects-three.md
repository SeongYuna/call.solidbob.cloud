---
title: "QA 화면 결함 셋 — 「미측정(null)」이 「0건」 · 위기 신호가 폭언 배지에 덮임 · 블랙컨슈머 카드가 mock 인데 「관리자에게 전송됨」"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 6
priority: 62
date: 2026-09-22
requirement:
  - "C-6"
  - "J-1"
paths:
  - "apps/call/src/*"
  - "apps/admin/src/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 최종 QA 미결 「대시보드 — 조서희」 ③·④·⑥:

1. 온도 이상 `null` 이 「0건」으로 보인다 — `decisions/316`(미측정은 미측정으로) 위반. 09-22 오전 수정이 상담원 화면엔 들어갔는데 관리자 요청 목록에 남았는지 확인
2. 위기 신호(자해·위협)가 같은 구간의 폭언 배지에 덮여 안 보인다 — 둘 다 보이거나 위기가 위
3. 블랙컨슈머 카드가 mock 인데 「관리자에게 전송됨」이라고 쓴다 — 실 API 가 붙기 전에는 「전송 안 됨(연동 전)」

## 완료 조건

- [ ] 셋 다 고치고 화면 캡처를 기록에
- [x] 위험도 점수·「안전합니다」류 문구 없음(부록 A-1)

## 2026-09-23 — 구현 (조서희)

1. **온도 `null`→"0건"** — 코드를 열어 보니 **이미 고쳐져 있었다.** `apps/call/BlacklistRequestButton.tsx:113-115`·
   `apps/admin/RequestsTab.tsx:124-126` 둘 다 `temperature_outliers === null`이면 "미측정"을
   먼저 본다. 09-22 오전 수정이 관리자 화면에도 이미 들어가 있었다(QA가 옛 번들을 봤을
   가능성). 코드 변경 없음.
2. **위기 신호가 폭언 배지에 덮임** — 확인대로 `callGuard`가 세그먼트당 **단일** 값이라
   두 번째 신호가 첫 번째를 지웠다. `callStore.ts`의 `callGuard`/`historyCallGuard`를
   `Record<string, CallGuardFlag[]>`로 바꾸고 `applyCallGuard`가 배열에 쌓는다(같은
   갈래 중복만 막는다). `TranscriptPanel.tsx`는 이제 세그먼트당 **모든** 신호를
   그리고, 위기 신호가 항상 위로 오도록 정렬한다. `BlacklistRequestButton.tsx`의
   증거 수집(`Object.values(callGuard)`)도 배열 평탄화로 맞췄다 — 부수 효과로
   블랙리스트 요청의 폭언·위협 집계도 더 정확해졌다(전엔 덮인 건수가 안 잡혔다).
3. **블랙컨슈머 카드 mock인데 "전송됨"** — `BlackConsumerAction.tsx`·`CustomerRiskBanner.tsx`
   전부 "관리자에게 전송됨"류 문구를 "관리자 알림 연동 전"으로 바꿨다(둘 다
   `console.info`뿐인 목업, `lib/customerRisk/supervisorAlert.ts`). 분류 자체는 화면에
   기록된다는 것과 알림 연동이 아직 없다는 것을 구분해서 적었다. `CustomerRiskBanner`의
   체크 아이콘(성공을 암시)은 지웠다.

검증: `tsc --noEmit`·`vite build`·`npm test`(vitest 11/11) 통과. **완료 조건 1번(화면
캡처)은 못 했다** — 로컬에 붙는 서버·브라우저가 없어 실제로 렌더된 화면을 못 봤다.
그래서 `done`이 아니라 `in-progress`로 둔다.
