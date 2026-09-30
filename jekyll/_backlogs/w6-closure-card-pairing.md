---
title: "필요서류 목록이 엉뚱한 카드 제목 밑에 붙는다 — 판정을 조항 번호로 짝짓지 않는다"
assignee: "정성윤"
role: "app"
status: "done"
sprint: 6
priority: 56
date: 2026-09-22
requirement:
  - "F-2"
  - "B-3"
paths:
  - "apps/call/src/store/callStore.ts"
  - "apps/call/src/components/TermsPanel.tsx"
---

> **정성윤이 09-22 수동 QA(`w5-manual-qa-full-stack` Q-43) 중 만든 티켓이다.** 담당은 «제안»이다.

## 무엇을

운영 QA 통화 `test-qa-05`: 서버가 판정한 절차는 `DASAN-TERM-4.3`(주민등록초본 발급)과 `DASAN-TERM-3.5`(수도 사용자 명의변경)다(`GET /hub/calls/test-qa-05/record` 의 `closures`).
그런데 화면의 필요서류 보기에는

- 「**3.4 수도요금 자동납부** 신청·해지」 제목 밑에 초본의 「신분증」
- 「**3.13 전자고지** 신청·해지」 제목 밑에 명의변경의 「신청서 · 신규 사용자 신분증 · 소유 또는 점유 관계 서류」

가 붙어 나온다. 아래 칩(절차 이름)은 맞아서, 칩과 카드 제목이 서로 다르다.

## 왜 — 코드

`apps/call/src/store/callStore.ts` 의 `attachIndex` 는 ① 같은 절차가 이미 붙은 카드 ② 없으면 **판정이 안 붙은 가장 최근 자동 카드** 순으로 고른다.
판정 이벤트의 조항(`source_doc_id`·`procedure`)과 카드의 `source.doc_id` 를 비교하지 않는다. 1순위 카드로 절차를 잡는 미디에이터 규칙(`w6-procedure-pick-rule`) 뒤에는 **그 1순위 카드가 이미 지나간 추천 묶음**에 있는 일이 흔하다.

## 왜 급한가

상담원이 「전자고지 신청에는 신청서·신분증·소유 증빙이 필요하다」고 잘못 안내한다 — B(필요서류 자동 제시)의 핵심 화면이 틀린 서류를 보여준다. 시연 전 필수.

## 완료 조건

- [x] 판정은 `source.doc_id` 가 판정의 조항과 같은 카드에 붙는다. 그런 카드가 없으면 **판정 전용 카드**(조항 제목)를 새로 만든다 — 남의 카드에 붙이지 않는다
- [x] 테스트 — 추천 두 묶음 뒤에 앞 묶음 1순위 조항의 판정이 와도 그 카드에 붙는다
- [x] 운영에서 같은 여섯 문장으로 재확인(칩 ↔ 카드 제목 일치)

근거: 진행 기록 `2026-09-22-18-seongyun` Q-43 · 캡처.

## 2026-09-23 — 구현 (조서희)

`callStore.ts`의 `attachIndex`를 고쳤다 — ① 같은 절차의 판정이 이미 붙은 카드(갱신용)
② **`item.card.source.doc_id === event.procedure`인 자동 카드**(신설) 순으로 찾는다.
"가장 최근의 판정 없는 자동 카드"로 떨어지던 세 번째·네 번째 우선순위는 뺐다 — 맞는 카드가
없으면 이제 `cardFromClosure()`로 판정 전용 카드를 새로 만든다(제목·문서는
`event.procedure_title`/`event.source`, 없으면 `event.procedure`로 대체).

**검증은 빌드·타입체크(`tsc --noEmit`·`vite build`)뿐이다** — `apps/call`에 테스트 실행기가
없어 완료 조건 2번(회귀 테스트)을 못 채웠고, 운영 재확인(3번)도 안 했다. `status`는
`in-progress`로 둔다.

## 2026-09-30 — 회귀 테스트 + 운영 확인 · done (정성윤)

**정성윤이 넘겨받았다**(`decisions/137` — 마감까지 `apps/` 도 정성윤이 고친다. §4 대로 `assignee` 를 옮기고 여기 적는다).
- **테스트** — `apps/call/test/closureCardPairing.test.ts` 3건: 추천 두 묶음 뒤 앞 묶음 1순위(4.3) 판정이 와도 4.3 카드에 붙고 뒤 묶음(3.5)에는 안 붙는다 ·
  같은 절차 판정은 같은 카드를 갱신한다(카드 수 불변) · 그 조항을 띄운 카드가 없으면 남의 카드가 아니라 판정 전용 카드. vitest 통과.
- **운영** — 수동 QA 2회차(`_logs/2026-09-30-01-seongyun`, 운영 server `0.1.43` · call-mediator `0.2.11` · call `index-sR-v0E8Y`) **Q-43 ✅**: 칩 전환 시 4.3 → 신분증 · 3.5 → 신청서/신규 사용자 신분증/소유·점유 서류, `closure_rule.py:90·105` 규칙표와 일치.
