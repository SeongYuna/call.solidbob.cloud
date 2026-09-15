---
title: "관리자 화면 배포 — admin.solidbob.cloud"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 4
priority: 2
date: 2026-09-15
depends_on:
  - "w4-admin-auth-runtime"
paths:
  - "apps/admin/*"
---

## 무엇을

`apps/admin`(관리자 콘솔, Vite+React)에 도메인을 준다 — **`admin.solidbob.cloud`**.
Vercel 프로젝트를 하나 더 만들고(Root Directory `apps/admin`), 클라우드플레어에 CNAME 을 건다.
근거·선택지·되돌리는 법: `_project/decisions/112`.

## 왜 서브도메인인가

2026-09-10 에 관리자 앱을 상담원 대시보드에서 **일부러 갈랐다**(별도 Vite 앱, 포트 5174).
`call.solidbob.cloud/admin` 경로로 합치면 **한 오리진을 공유해** 두 앱의 토큰·`localStorage` 가 섞인다.
09-14 에 "상담 화면으로" 버튼까지 없앤 결정을 주소 층에서 되돌리는 셈이 된다.

## ⚠ 먼저 잠그고 올린다

지금 그대로 공개하면 두 가지가 동시에 일어난다 —

1. **로그인이 100% 실패한다.** `apps/admin/src/lib/auth/authApi.ts` 의 `apiBaseUrl()` 이
   운영 빌드에서 `VITE_API_BASE_URL` 이 없으면 **빈 문자열**을 돌려준다 → `POST /admin/auth/google` 이
   같은 오리진(Vercel)으로 가서 404. 빌드타임 변수라 나중에 넣으면 **재배포**가 필요하다.
2. **화면이 사실상 공개된다.** 로그인 게이트는 `App.tsx` 의 클라이언트 상태 한 줄이고,
   `AdminPanel` 과 mock 픽스처(`src/mock/adminFixtures.ts`·`qaReviewFixtures.ts`)는 **번들에 실린다.**
   실데이터는 아니지만 탭 구조·블랙리스트 워크플로·QA 리뷰 화면이 주소를 아는 사람에게 보인다.

→ **Vercel Deployment Protection**(Password 또는 Vercel Authentication)을 **켠 상태로 올린다.**
`w4-admin-auth-runtime` 이 끝나 실제 로그인이 되는 것을 확인한 뒤에 끈다.

## 할 것

- [x] `_project/decisions/112` 작성
- [ ] **Vercel 프로젝트 생성** — Root Directory `apps/admin` · Build `npm run build` · Output `dist` ·
      Production Branch `main`
- [ ] **Deployment Protection 켜기** (배포 전에)
- [ ] **환경변수(Production)** — `VITE_API_BASE_URL=https://server.solidbob.cloud` ·
      `VITE_GOOGLE_OAUTH_CLIENT_ID=<웹 클라이언트 ID>`. **둘 다 빌드타임이라 넣고 재배포한다**
- [ ] **클라우드플레어** — `admin` CNAME → Vercel, **회색 구름**(`decisions/103`)
- [ ] **Ignored Build Step** — `git diff --quiet HEAD^ HEAD -- apps/admin`.
      프로젝트가 셋이 되어 main 머지마다 빌드가 3벌 돈다
- [ ] 실제 로그인 한 번 → 되면 Deployment Protection 해제

## 완료 조건

`https://admin.solidbob.cloud` 에서 구글 로그인 → 관리자 화면 진입이 되고, 보호를 꺼도
**로그인 없이는 아무 화면도 안 보이는 상태**가 된다(= 백엔드 인증이 실제로 관문 역할을 한다).

## 안 하는 것

- **`call.solidbob.cloud` 의 Vercel 설정을 건드리지 않는다.** 별도 프로젝트다.
- **관리자 이메일을 저장소에 적지 않는다** — 허용 목록 행 추가는 `w4-admin-auth-runtime` 쪽 DB 작업이다.

## 완료 (2026-09-15)

`https://admin.solidbob.cloud` **200**, 구글 로그인 통과. 번들에 두 값이 들어간 것을 직접 확인했다
(`/assets/index-2GxCi4n7.js` 에 `server.solidbob.cloud` · 클라이언트 ID). 절차는 런북 **18-3**.

**Deployment Protection 은 켜지 않았다** — 켜려던 이유가 「로그인이 100% 실패하는 상태를 공개하지 않는다」였는데
백엔드가 붙어 **진짜 관문이 살아났다.** 남는 노출은 번들의 UI 구조와 mock 시드뿐이고, 시드는 전부 합성이다
(`req-seed-1`·`hmac_seed_1`·`****3841` — 실제 개인정보 0건). Hobby 플랜이라 Production 보호가 제약되는 것도 겹친다.
