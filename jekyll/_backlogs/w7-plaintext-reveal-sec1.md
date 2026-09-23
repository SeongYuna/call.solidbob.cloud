---
title: "원문 열람(plain_text)이 SEC-1 과 모순이다 — 기능을 정리한다"
assignee: "조서희"
role: "app"
status: "done"
sprint: 7
priority: 81
date: 2026-09-21
requirement:
  - "C-5"
  - "SEC-1"
paths:
  - "apps/call/src/*"
---

## 무엇을

상담원 화면의 **마스킹 스팬 클릭 → 원문 토글**([w3-dashboard-mask-reveal](/backlog/w3-dashboard-mask-reveal/)·[w3-demo-mask-span-toggle](/backlog/w3-demo-mask-span-toggle/))을 정리한다.

## 왜

SEC-1 은 **「마스킹 전 원문이 DB·로그 어디에도 남지 않는다」**다. 원문을 보여 주려면 원문이 어딘가에 있어야 한다 —
**둘은 동시에 성립하지 않는다**([미결 항목](/open-items/)). mock 에서는 시나리오 파일에 원문이 있어 토글이 되지만, 실서버는 원문을 주지 않는다(줄 수 없다).
시연에서 mock 화면의 토글을 보이면 **「운영에서도 원문을 볼 수 있다」로 읽힌다.**

## 선택지 — 권고는 앞쪽

- **기능을 걷는다** — 라이브 모드에서는 이미 동작할 재료가 없다. mock 에서도 걷어 화면이 말하는 것과 시스템이 하는 것을 맞춘다
- mock 전용으로 남기고 화면에 「데모 데이터」를 적는다

## 완료 조건

- [x] 고른 쪽을 `4xx` 결정 기록으로 남긴다
- [ ] 서버 응답에 `plain_text` 류 필드가 **없음을 단언하는 테스트**는 장민석 님 몫 — 필요하면 티켓을 따로 연다(한 티켓에 두 사람 작업을 담지 않는다)

## 2026-09-23 — 구현 (조서희)

**권고안(기능을 걷는다)을 그대로 택했다** — `decisions/408`. mock 포함 전부 지웠다:

- `MaskedText.tsx` 대폭 단순화 — 원문 관련 prop(`plainText`·`authorized`·`revealAll`·
  `openedIds`·`onToggle`)과 `revealSpansFor`/`RevealSpan` 삭제. 마스킹 스팬은 이제 항상
  마스킹본만 보여주는 비대화형 `<mark>`다.
- `TranscriptPanel.tsx` — "권한 확인 (데모)"·"원문 보기" 버튼, `toggleSpan`·
  `toggleLineSpans`·`allRevealIds` 삭제. 「⚠ 경고」 배지는 `.claude/rules/call.md §2`가
  요구하는 정적 표시라 남기되, 이제 클릭해도 아무 일 없는 `<span>`이다.
- `plain_text` 필드를 `contract.ts`(`TranscriptEvent`·`TranscriptQuerySegment`)·
  `callStore.ts`(`Utterance`)에서 뺐다 — 실서버 계약엔 애초에 없던 필드였다.
- `maskSensitiveText.ts`의 `logPlainReveal`(열람 감사 로그 목업)·`SensitiveMaskResult.plain`
  삭제. mock 데이터 생성 쪽(`callHistory.ts`·`scenarios/helpers.ts`·`scenarios/dasan.ts`
  세 줄)도 같이 걷었다. 죽은 CSS 규칙(`.mask-auth-*`·`.masked-span.is-clickable`
  등)도 지웠다.

**완료 조건 2번은 그대로 남겼다** — 서버 쪽 단언 테스트는 장민석 몫이라 손대지 않았고,
필요하면 별도 티켓을 연다.

검증: `tsc --noEmit`·`vite build`(번들 JS 약 3.4KB 감소)·`npm test`(11/11) 통과.
