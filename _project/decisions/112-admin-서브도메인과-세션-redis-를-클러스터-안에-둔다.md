# 112 — `admin.solidbob.cloud` 를 배정하고, 세션 Redis 를 클러스터 안에 둔다

**작성일**: 2026-09-15
**작성**: 정성윤
**상태**: 진행 중 — 저장소 쪽(매니페스트·런북·시크릿 템플릿) 완료 / 계정 쪽(구글·Vercel·클러스터) 남음
**갱신 대상**: `infra/k8s/base/kustomization.yaml` · `redis.yaml`(신설) · `secret.example.yaml` ·
`docs/infra-runbook.md`(16-3 · 17-4) · `jekyll/_backlogs/w4-admin-auth-runtime` · `w4-admin-subdomain`
**관련**: `decisions/403`(관리자 로그인 방식 — 이 결정이 그 §5 의 «그때 별도로 정한다»를 채운다) ·
`104`(도메인 배정) · `105`(배포 단위 하나) · `103`(클라우드플레어 회색 구름)

## 맥락

`server/apps/admin_auth/`(구글 로그인 · JWT+Redis · refresh 회전)는 **코드가 운영에 이미 배포돼 있다** —
2026-09-15 확인: `/admin/auth/test` 가 `{"router":"admin_auth","marker":"0.1.7"}` 를 돌려주고
`/openapi.json` 에 `google`·`refresh`·`logout`·`me` 넷이 있다.
⚠ **`/admin/auth/test` 는 같은 날 걷어냈다** — 배포 확인용 임시 프로브였다(`w4-swagger-deploy-probe`).
위 문장은 **그때의 확인 기록이라 고치지 않는다.** 지금 같은 확인을 하려면 `/openapi.json` 의
`admin/auth` 넷을 본다. 관리자 화면(`apps/admin`)도 로그인 게이트까지
붙어 있다. **그런데 실제로 눌러 보면 안 된다** — 붙을 곳이 없기 때문이다:

- **Redis 가 없다.** `403` §5 가 "테스트 스코프 — 운영 매니페스트를 만들지 않았다"로 남겼다.
- **`server-env` 에 키 3종이 없다** — `GOOGLE_OAUTH_CLIENT_ID`·`ADMIN_JWT_SECRET`·`REDIS_URL`.
- ~~RDS 에 `admin_account`·`admin_refresh_token` 이 없다~~ → **2026-09-15 확인 결과 이미 있다**
  (`db/migrations/2026-09-14-…sql`, 26 테이블 일치). 남은 것은 **허용 목록 행 1건**이다.
- **관리자 화면이 배포돼 있지 않다** — `apps/admin` 은 도메인이 없다.
- **CORS 에 관리자 오리진이 없다.**

`403` §7 이 프로바이더를 요청 스코프로 만든 탓에 **앱 기동·`/health` 는 전부 정상**이다. 즉 이 다섯은
**눌러 보기 전에는 드러나지 않는다** — 그래서 한 번에 묶어 닫는다.

## 선택지

**주소를 어디에 둘 것인가**

| | 방법 | 좋은 점 | 나쁜 점 |
|---|---|---|---|
| **A** | **`admin.solidbob.cloud` 서브도메인** | 상담원 화면과 오리진이 갈려 토큰·`localStorage` 가 섞이지 않는다. 앞단 보호(암호·SSO)를 화면 단위로 건다 | Vercel 프로젝트가 하나 늘어 main 머지마다 빌드가 3벌 |
| B | `call.solidbob.cloud/admin` 경로 | 프로젝트를 안 늘린다 | **한 오리진을 공유한다** — 상담원 브라우저와 관리자 세션이 같은 저장소를 쓴다. 별도 Vite 앱이라 rewrite 도 필요하다 |

**세션 저장소를 어디에 둘 것인가**

| | 방법 | 좋은 점 | 나쁜 점 |
|---|---|---|---|
| **C** | **클러스터 안 Redis 파드(휘발)** | 비용 0. 이미 있는 배포 경로에 얹힌다 | 노드가 죽으면 세션도 죽는다(→ refresh 로 복구) |
| D | AWS ElastiCache | 관리형 | **`infra/CLAUDE.md` §1-2 금지 항목.** 5분짜리 세션에 과하다 |
| E | Redis 없이 JWT 만 | 파드 하나를 안 띄운다 | **로그아웃이 exp(5분) 전에 반영되지 않는다** — `403` §3 이 Redis 를 넣은 이유가 그것이다 |

## 결정

1. **`admin.solidbob.cloud` 를 관리자 화면(`apps/admin`)에 배정한다** — A. `decisions/104` 의 배정
   (`docs`=지킬 · `call`=상담원 · `www`/apex=소개)에 네 번째로 더한다. Vercel 프로젝트를 새로 만들고
   Root Directory 는 `apps/admin`, DNS 는 클라우드플레어 CNAME **회색 구름**(`103`).
2. **세션 Redis 를 클러스터 안에 둔다** — C. `infra/k8s/base/redis.yaml`(Deployment + ClusterIP Service).
   **볼륨 없음**(`--save "" --appendonly no`): 저장하는 것이 5분짜리 access token 세션뿐이고,
   영속이 필요한 refresh 는 이미 RDS 에 있다. 파드가 다시 떠도 사용자는 재로그인하지 않는다.
   `maxmemory-policy` 는 `noeviction` — 가득 차면 조용히 세션을 버리는 대신 **로그인이 눈에 띄게 깨지게** 한다.
3. **ElastiCache 는 만들지 않는다.** `infra/CLAUDE.md` §1-2 의 경계를 이 결정도 넘지 않는다.
4. **백엔드가 붙기 전까지 관리자 화면은 앞단을 잠그고 배포한다** — Vercel Deployment Protection.
   지금 그대로 공개하면 ① `VITE_API_BASE_URL` 이 없어 **로그인이 100% 실패**하고
   ② 로그인 게이트가 클라이언트 상태 한 줄이라 `AdminPanel` 과 mock 픽스처가 **번들에 그대로 실려**
   주소를 아는 사람이 내부 운영 화면을 본다. 보호를 켜면 둘 다 닫힌 채로 팀 공유가 된다.
5. **관리자 계정은 저장소에 넣지 않는다.** `admin_account` 는 허용 목록이고 행 추가는 DB 작업이다
   (`403` §1). 런북 17-4 에 절차만 남기고 이메일은 적지 않는다(§8 — 개인정보).

## 근거

- **오리진 분리가 이미 팀 결정이다.** 2026-09-10 에 관리자 앱을 상담원 대시보드에서 **일부러 갈랐고**
  (`apps/admin`, 포트 5174), 09-14 에 "상담 화면으로" 버튼까지 없앴다(`App.tsx` 주석). 경로로 합치면
  그 결정을 주소 층에서 되돌리는 셈이 된다.
- **휘발을 고른 근거는 데이터 성격이다.** `403` 이 access token 5분 / refresh 10분 회전으로 설계했고,
  refresh 는 이미 RDS 에 해시로 남는다. **잃을 것이 5분치 세션뿐**이라 PVC 를 붙일 이유가 없다.
- **`noeviction` 을 고른 근거는 이 저장소의 fail-closed 관행이다.** 128MB 는 5분 TTL 세션에 남아도는
  크기라, 가득 찬다면 용량 문제가 아니라 버그다. `allkeys-lru` 로 두면 그 버그가 «가끔 로그아웃됨» 으로
  조용히 흘러간다(`decisions/024` 가 경계한 «오류 없이 빠지는» 실패와 같은 모양).
- **앞단 보호를 고른 근거는 순서를 기다리지 않기 위해서다.** 백엔드 다섯 가지가 다 끝날 때까지
  화면 배포를 미루면 발표 준비가 그만큼 밀린다. 보호를 켜면 **노출 없이 지금 올릴 수 있다.**

## 되돌리는 법

- **서브도메인**: Vercel 프로젝트에서 도메인 제거 → 클라우드플레어 `admin` 레코드 삭제.
  `apps/admin` 은 그대로 남고 로컬 `npm run dev`(5174)로 계속 쓸 수 있다.
- **Redis**: `kustomization.yaml` 의 `- redis.yaml` 한 줄을 지우고 머지하면 다음 배포에서 빠진다
  (`kubectl delete deploy/redis svc/redis` 로 즉시 지울 수도 있다). `server-env` 의 `REDIS_URL` 도 함께
  비운다 — 남겨 두면 없는 주소로 붙으러 간다.
- **관리자 계정**: 허용 목록 행을 지우면(`DELETE FROM "admin_account" WHERE email=…`) 그 사람은 즉시 못 들어온다.
  테이블 자체는 09-14 마이그레이션 소관이라 이 결정으로 되돌리지 않는다.
- **보호 해제**: Vercel Deployment Protection 을 끄는 것이 곧 «공개» 다 — 4번의 두 조건
  (`VITE_API_BASE_URL` 주입 · 백엔드 실제 로그인 성공)을 확인한 뒤에 끈다.
