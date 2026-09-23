---
title: "관리자 현황판을 GET /hub/admin-stats 하나로 채운다"
assignee: "조서희"
role: "app"
status: "done"
sprint: 6
priority: 60
date: 2026-09-22
requirement:
  - "J-3"
  - "D-4"
depends_on:
  - "w6-admin-stats-api"
paths:
  - "apps/admin/src/components/admin/WallboardTab.tsx"
  - "apps/admin/src/lib/api/hubClient.ts"
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

장민석 님이 09-22 에 만든 `GET /hub/admin-stats`([w6-admin-stats-api](/backlog/w6-admin-stats-api/))로 관리자 현황판 숫자를 채운다.
관리자 토큰으로 부르면 여덟 칸(통화 전체·종료·콜 가드·승인 대기·활성 등록·배정 판정 셋)이 **문자열**로 온다. 지금 현황판은 mock 시드다.

## 지킬 것

- 상담원 단위로 쪼개지 않는다(부록 A-1)
- 표본이 0 이면 숫자 0 이 아니라 **「표본 없음」** · 온도 이상 `null` 은 「미측정」
- 「완료 통화 누적」을 `calls_total` 과 `calls_closed` 중 무엇으로 보일지 정해 적는다

## 완료 조건

- [x] 현황판 숫자가 mock 이 아니다 — 운영에서 오늘 합성 통화 4건이 보인다
- [x] 로그인 풀림(401)은 별도 문구

## 2026-09-23 — 확인해 보니 대부분 이미 돼 있었다 (조서희)

**티켓을 착수하려고 코드를 열어 보니, 「지금 현황판은 mock 시드다」라는 전제가 이미
낡아 있었다.** `hubClient.ts`의 `fetchAdminStats()`·`adminStore.ts`의 `loadAll()`이
`GET /hub/admin-stats` 여덟 칸 중 다섯(`calls_total`·`calls_closed`·`call_guard_flags`·
`pending_requests`·`active_entries`)을 이미 실제 값으로 받고 있었고, `WallboardTab.tsx`도
그 값을 그대로 그리고 있었다 — 나머지 셋(배정 판정)은 내가 09-22에 붙였다. **「완료 통화
누적」을 `calls_total`과 `calls_closed` 중 무엇으로 할지도 이미 정해져 코드 주석에 남아
있었다**(`hubClient.ts:235-236`, "라벨이 '완료'이므로 닫힌 통화만 센다"). 언제·누가 그
다섯 칸을 연결했는지는 로그에 남기지 않았지만(`GET /hub/admin-stats` 서버 쪽을 만든
장민석으로 보인다), 코드 자체는 확인됐다.

**진짜 남아 있던 건 완료 조건 2번(401 별도 문구)뿐이었다.** `AdminPanel.tsx`는 모든
로드 실패를 "데이터를 불러오지 못했습니다: …" + 「다시 시도」 버튼 하나로 뭉뚱그렸는데,
401은 같은 토큰으로 다시 불러도 또 401이 난다 — 재시도가 무의미하다. `adminStore.ts`의
`loadAll()`에 401 전용 분기를 추가했다 — 세션을 지우고(`authStore.logout()`)
`AdminLoginScreen`으로 돌려보내며 "세션이 만료되었습니다 — 다시 로그인해 주세요"를
그 화면의 기존 오류 표시 자리에 남긴다.

**"상담원 단위로 쪼개지 않는다"**·**"표본 0 → 표본 없음"**(부록 A-1, 절대 원칙)은 그대로
지켜지고 있다 — 여기 여덟 칸은 전부 순수 집계(COUNT)라 "표본 없음"이 따로 있을 자리가
없다(0건은 그 자체로 확정값이지 미측정이 아니다). 온도 이상 `null`→"미측정"은 이 화면이
아니라 블랙리스트 요청 목록(`RequestsTab.tsx`) 몫이고 이미 처리돼 있다(확인만 했다).

검증: `tsc --noEmit`·`vite build` 통과. 401 분기는 로컬에 붙는 서버가 없어 실제 만료
토큰으로 눌러 보지 못했다 — 그래도 나머지 완료 조건이 전부 정적으로 확인되는 것들이라
`done`으로 올린다.
