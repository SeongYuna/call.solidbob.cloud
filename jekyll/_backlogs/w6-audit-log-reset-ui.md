---
title: "관리자 감사 로그 — 만료일 「재설정」 줄 (화면)"
assignee: "정성윤"
role: "app"
status: "done"
sprint: 6
priority: 67
date: 2026-09-28
requirement:
  - "J-4"
depends_on:
  - "w6-audit-log-blacklist-reset"
paths:
  - "apps/admin/src/components/admin/AuditLogTab.tsx"
---
## 무엇을

[w6-audit-log-blacklist-reset](/backlog/w6-audit-log-blacklist-reset/)(정성윤, QA Q-67)의 **화면 쪽**이다. 서버 문
`GET /hub/blacklist-expiry-changes?limit=50`(관리자 로그인 필요)은 정성윤 님이 열어 두었다. 티켓 하나에 두 사람 작업을
담지 않으려고 화면 몫을 따로 뗐다(`CLAUDE.md` §4).

- `hubClient.ts` 에 `fetchRecentBlacklistExpiryChanges()`
- `AuditLogTab.tsx` 가 승인·반려·해제에 **「재설정」**(만료 이전 → 새 날짜 · 마스킹된 사유 · 처리자)을 합쳐 최근 순으로 정렬.
  세 출처의 시각 표기가 달라도 되도록 문자열이 아니라 시각으로 비교한다.
- 불러오지 못하면 **조용히 빼지 않고** 「재설정 이력을 불러오지 못했습니다」 한 줄을 띄운다.

## 완료 조건

- [x] 화면: 감사 로그에 「재설정」 줄 — `apps/admin` `tsc` + `vite build` 통과
- [x] 운영에서 재설정 1회 → 감사 로그에 보임 (관리자 로그인으로 눈 확인)

⚠ `apps/admin` 에는 테스트 실행기가 없어 단위 테스트를 붙이지 못했다.

## 2026-09-30 — 운영 확인 · done (정성윤)

**정성윤이 넘겨받았다**(`decisions/137` — 마감까지 `apps/` 도 정성윤이 고친다. §4 대로 `assignee` 를 옮기고 여기 적는다). 수동 QA 2회차(`_logs/2026-09-30-01-seongyun`, 운영 server `0.1.43` · call-mediator `0.2.11` · call `index-sR-v0E8Y`) **Q-67 ✅** — 감사 로그에 「재설정」 줄(만료 2027.3.21 → 2026.12.29 · 사유)이 승인·반려·해제와 시간순으로 보였다.
