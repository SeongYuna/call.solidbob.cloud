---
title: "상담원 대시보드를 call.solidbob.cloud 에 배포한다"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 3
priority: 3
date: 2026-09-03
depends_on:
  - "w3-vercel-account-migration"
paths:
  - "apps/dashboard/*"
---

## 무엇을

`apps/dashboard`(상담원 어시스트 화면)를 정성윤 Vercel 계정의 **두 번째 프로젝트**로 올리고
`decisions/104` 가 배정해 둔 **`call.solidbob.cloud`** 에 붙인다.

## 왜

랜딩(`apps/platform`)만 공개돼 있고 **제품 화면은 로컬에서만 볼 수 있었다.**
발표·중간 점검에서 화면을 보여주려면 주소가 있어야 한다. `104` 가 `call` 을 프론트 데모로
배정해 뒀는데 **레코드가 비어 있어 아무도 안 쓰는 이름**이 돼 있었다.

## 완료 조건

- [x] Root Directory `apps/dashboard` 로 프로젝트 생성 (Vite · `dist` · Production `main`)
- [x] **환경변수를 비워 둔다** — `VITE_GATEWAY_WS_URL` 이 비어야 `MockGatewayClient` 로 돈다
- [x] `call.solidbob.cloud` 부착 + 클라우드플레어 `call` CNAME 신설 (DNS only)
- [x] 라이브 번들이 로컬 프로덕션 빌드와 일치하는지 대조 — 243,906 bytes **완전 일치**
- [x] 임시로 썼던 `dashboard.solidbob.cloud` 제거 (Vercel · 클라우드플레어 양쪽)

## 남은 것

**게이트웨이·코어가 생기면 mock 을 끊는다.** `VITE_GATEWAY_WS_URL`·`VITE_CORE_API_URL` 을
Vercel 환경변수에 넣으면 `RealGatewayClient` 로 바뀐다 — `services/gateway`(코드 0줄)와
`server` AWS 배포([w3-aws-deploy](/backlog/w3-aws-deploy/))가 선행이다.
