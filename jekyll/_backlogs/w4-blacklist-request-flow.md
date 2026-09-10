---
title: "J-1·J-2·J-4 — 블랙리스트 전환 요청과 관리자 승인"
assignee: "류준"
role: "ai"
status: "in-progress"
sprint: 4
priority: 8
date: 2026-09-09
requirement:
  - "J-1"
  - "J-2"
  - "J-4"
paths:
  - "server/apps/blacklist/*"
  - "apps/dashboard/src/components/BlacklistRequestButton.tsx"
  - "apps/dashboard/src/components/AdminBlacklistPanel.tsx"
---

## 무엇을

통화 종료 화면의 **「블랙리스트 전환 요청」 버튼** → 관리자 대시보드의 **승인요청창** →
승인 시 **블랙리스트 관리창** 등록. 근거: `_project/decisions/204`.

## 왜

C-6 콜 가드는 통화 **중**에 경고한다. 그런데 `DASAN-MANUAL-5.3` 이 정한
*"반복 발생 시 상급자가 이어받는다"* 는 **다음 통화**의 문제이고 경로가 없었다.
실제 콜센터가 이미 하고 있는 운영을 시스템이 거드는 것이다.

## 완료 조건

- [x] **상담원은 `pending` 까지만** 만들 수 있다 — 승인은 관리자 몫
- [x] 요청에 **마스킹된 대화 맥락**이 실린다(원문 아님, `MANUAL-5.5`·C-5)
- [x] 근거는 전부 **셀 수 있는 건수** — 위험도 점수를 만들지 않는다(부록 A-1)
- [x] **`distress` 는 전환 근거에서 빠지고** 전문 기관 연결 안내를 대신 띄운다(`MANUAL-5.4`)
- [x] 해제해도 행을 지우지 않는다 — 「왜 풀렸는지」가 남아야 한다(절대 원칙 8)
- [x] 도메인 규칙 테스트 · `cd server && pytest` 통과
- [x] 대시보드 `tsc --noEmit` · `npm run build` 통과
- [ ] **서버 어댑터·라우터 미구현** — 지금은 대시보드 store 안의 mock 이다
- [ ] §7.3 계약에 J 이벤트 등록

## ⚠ 담당 경계를 넘었다

`server/apps/blacklist/`(장민석)·`apps/dashboard/`(조서희) 양쪽을 건드렸다.
`decisions/012`(디렉터리 경계 = 담당 경계)에 걸리는 일이라 **사용자 지시로 진행했고**
이 사실을 여기 적어 둔다. 두 분과 맞춰야 할 것:

- **장민석**: `BlacklistPort` 구현체(PostgreSQL 어댑터)와 라우터. 도메인 규칙
  (`transitions.py`·`routing.py`)은 만들어 뒀고 테스트 19건이 붙어 있다
- **조서희**: 프론트 `CallGuardFlag.category` 가 한글 3종(`폭언`·`욕설`·`위협`)인데
  백엔드는 4종(`insult`·`threat`·`sexual`·**`distress`**)이다. **`distress` 는 화면
  대응이 반대라(끊지 않고 연결) 그냥 매핑할 수 없다** — 계약을 맞춰야 한다
