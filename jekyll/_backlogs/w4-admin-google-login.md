---
title: "관리자 로그인 — 구글 OAuth, JWT(Redis)+refresh(RDS)"
assignee: "조서희"
role: "app"
status: "done"
sprint: 4
priority: 3
date: 2026-09-14
paths:
  - "apps/admin/src/lib/auth/*"
  - "apps/admin/src/components/AdminLoginScreen.tsx"
  - "server/apps/admin_auth/*"
---

무엇: `apps/admin`에 로그인을 만든다. 회원가입 화면은 없다 — 구글 계정으로만 들어오고,
`admin_account`(RDS) 허용 목록에 없으면 403. access token은 JWT+Redis 5분(테스트
스코프, 사용자 지시), refresh token은 RDS에 해시로 저장하고 10분마다 회전.

왜: `apps/admin`에 인증이 전혀 없었다 — `mock/adminAuth.ts`가 고정 문자열을 돌려주는
자리채움이었다. 누구나 URL만 알면 관리자 화면(블랙리스트 승인·해제 등)에 들어갈 수
있었다.

완료 조건:
- [x] `POST /admin/auth/google` — 구글 id_token 검증 → 허용 목록 확인 → 토큰 쌍 발급
- [x] `POST /admin/auth/refresh` — refresh token 회전
- [x] `POST /admin/auth/logout` — access 세션(Redis)·refresh 둘 다 무효화
- [x] `GET /admin/auth/me` — 다른 관리자 전용 라우트가 재사용할 수 있는 가드 포함
- [x] `admin_account`·`admin_refresh_token` 테이블 (`db/generate_schema_docs.py`)
- [x] 프론트 로그인 화면 + 세션 복원(새로고침 시 refresh token으로 조용히 재로그인)
- [x] `cd server && pytest` · `cd apps/admin && npm run typecheck && npm run build` 통과
- [ ] 실제 브라우저에서 구글 로그인 끝까지 확인 — Google Client ID·로컬 Redis·RDS가
      필요하다(이 세션 환경엔 셋 다 없었다)

근거: `_project/decisions/403`.

---

> **보드 최신화 (2026-09-21, 정성윤 — 사용자 지시로 전체 보드를 한 번에 맞췄다).** `in-progress` → `done`. 마지막 완료 조건(실제 브라우저에서 구글 로그인 끝까지)은 **운영에서 충족됐다** —
2026-09-15 `admin.solidbob.cloud` 에서 구글 로그인 → 관리자 화면 진입까지 완주(`_logs/2026-09-15-05-seongyun`,
[w4-admin-auth-runtime](/backlog/w4-admin-auth-runtime/)). 조서희 님 로컬 Redis 가 없어 **로컬에서는** 여전히 미확인이다.
> 남은 것은 다른 티켓으로 갔다 — 토큰 수명(5분·10분은 테스트 값) → [w7-demo-infra-readiness](/backlog/w7-demo-infra-readiness/) ·
> `admin_account.agent_id` NULL(승인·해제 409) → [w6-admin-agent-mapping](/backlog/w6-admin-agent-mapping/).
