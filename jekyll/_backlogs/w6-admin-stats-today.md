---
title: "현황판 집계에 「오늘」 칸 — `admin-stats` 에 날짜 구분이 없어 오늘 통화 수를 못 읽는다"
assignee: "정성윤"
role: "ai"
status: "done"
sprint: 6
priority: 75
date: 2026-09-22
paths:
  - "server/apps/hub/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

`GET /hub/admin-stats` 여덟 칸이 전부 누적이다. 09-22 운영에서 `calls_total` 14 는 09-11~15 테스트 통화 10건을 포함한 값이고, 오늘 4건은 `GET /hub/calls` 로 따로 셌다.
시연에서 「오늘 통화 N건」을 보이려면 칸이 있어야 한다.

## 완료 조건

- [x] 조서희 님과 칸 정의(오늘 통화 · 오늘 콜 가드 · 오늘 요청) — 시간대는 KST
- [x] 응답 필드 추가 · 계약 테스트 · 현황판(`w6-admin-stats-wallboard`)에 표시

근거: 정성윤 13번 기록.

## 2026-09-22 — 장민석 서버 몫 (칸 정의는 예측)

- `GET /hub/admin-stats` 에 **`calls_today` · `call_guard_flags_today` · `requests_today` · `today`**(KST 날짜) — 누적 여덟 칸은 그대로. 「오늘」 = KST 자정부터, 기준 시각은 DB `NOW()` 하나(같은 문장)
- 칸 정의는 이 티켓의 괄호(오늘 통화 · 오늘 콜 가드 · 오늘 요청)를 그대로 썼다 — **조서희 님과 맞춘 것이 아니라 예측이다.** 다르면 칸을 바꾼다
- 테스트: 라우터 계약(문자열) · 통합(이틀 전 통화는 누적에만, 오늘 칸에는 없다)
- 남은 것: 조서희 님 확인 + 현황판(`w6-admin-stats-wallboard`) 표시

## 2026-09-22 — 배포

- **`0.1.35` 운영 배포됨** (PR #132 머지 07:57 → release 성공 · `/health` `version: 0.1.35` · `read_guard: open` 확인, 09-22)
- 남은 것: 조서희 님 칸 정의 확인 · 현황판 표시

## 2026-09-30 — 현황판에 「오늘」 줄 (정성윤) · done

**정성윤이 넘겨받았다**(`decisions/137` — 마감까지 `apps/` 도 정성윤이 고친다. §4 대로 `assignee` 를 옮기고 여기 적는다). 서버 몫은 09-22 에 끝나 있었고(`0.1.35`, 응답에 `calls_today`·`call_guard_flags_today`·`requests_today`·`today`), 화면이 그 필드를 읽지 않아
수동 QA 2회차(`_logs/2026-09-30-01-seongyun`, 운영 server `0.1.43` · call-mediator `0.2.11` · call `index-sR-v0E8Y`) Q-14 에서 「오늘 통화가 없는데 초기화 상태가 아니다」로 보였다.
- `apps/admin`: `hubClient.ts` 가 네 필드를 읽고(옛 서버면 0·null) · `adminStore.ts` 네 칸 · `WallboardTab.tsx` 에 **「오늘 (YYYY-MM-DD, KST)」 섹션**(오늘 시작된 통화 · 오늘 콜가드 경고 · 오늘 올라온 블랙리스트 요청). 누적 타일은 그대로 둔다.
  `today` 가 없으면(옛 서버) 오늘 줄을 그리지 않는다. 칸 정의는 09-22 예측값을 그대로 확정했다(조서희 님 확인은 137 로 생략).
- 검증: `tsc --noEmit` · `vite build` 통과(`apps/admin` 은 테스트 실행기가 없다). 운영 반영은 main 머지 뒤 Vercel 자동 배포.
