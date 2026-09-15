---
title: "관리자 로그인 운영 배선 — Redis · 시크릿 키 3종 · RDS 테이블"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 4
priority: 1
date: 2026-09-14
depends_on:
  - "w4-admin-google-login"
paths:
  - "infra/k8s/base/*"
---

## 무엇을

`server/apps/admin_auth/`(구글 로그인 · JWT(Redis) + refresh(RDS))가 **코드로는 main 에 올라갔는데
운영에는 붙을 곳이 없다.** 지금 배포된 파드에서 `/admin/auth/*` 를 부르면 500 이다.
앱 쪽 티켓(`w4-admin-google-login`, 조서희 — 이 브랜치에 없어 링크를 걸지 않았다)과 **갈래가 다르다** —
여기는 클러스터·시크릿·DB 쪽 몫이다.

## 왜 지금 티켓으로

2026-09-14 릴리스(PR #74) 뒤 확인한 결과, **배포 판정은 정상이고 `/health` 도 정상이다.**
`admin_auth` 의 포트 배선이 요청 스코프라 앱 기동에 영향을 주지 않기 때문이다 —
**그래서 «되는 것처럼» 보이고, 실제로 눌러 보기 전에는 아무도 모른다.**

## 할 것

- [x] **Redis** — `infra/k8s/base/redis.yaml` 신설(Deployment + ClusterIP Service), kustomize `resources` 에 추가.
      **휘발로 정했다** — 볼륨 없이 `--save "" --appendonly no`. 잃을 것이 5분짜리 access token 세션뿐이고
      refresh 는 RDS 에 있어 사용자는 재로그인 없이 복구된다(`decisions/112` §2). 다음 릴리스에 같이 적용된다
- [ ] **`server-env` 시크릿에 키 3종** ← 값이 필요해 남았다. 키 설명은 `secret.example.yaml` ① 에 적었다 — `GOOGLE_OAUTH_CLIENT_ID` · `ADMIN_JWT_SECRET` · `REDIS_URL`.
      값은 SSM 세션 안에서 `--from-env-file` 로 넣는다(런북 12-2). **GitHub·로그·이 저장소 어디에도 값이 남지 않게 한다**(SEC-2)
- [x] **RDS 에 `admin_account` · `admin_refresh_token`** — 이미 들어가 있다.
      `db/migrations/2026-09-14-customer-ref-admin-closure.sql` 이 만들었고 09-15 확인에서 **26 테이블 일치**
      (`_logs/2026-09-15-05-minseok.md`). 09-14 에 「없다」고 적은 것은 그 시점 사실이었고, 마이그레이션이 그 뒤에 들어갔다
- [ ] **허용 목록 행 1건** — `admin_account` 에 본인 구글 이메일(소문자). 이게 없으면 인증을 통과해도 403 이다.
      절차는 런북 **17-4**. **이메일은 저장소에 적지 않는다**(§8)
- [x] `.env.example` 에 위 세 키 이름 추가 (값 없이) — 이미 들어가 있었다(93·96·105행)
- [ ] **`CORS_ALLOWED_ORIGINS` 에 `https://admin.solidbob.cloud` 추가** — 관리자 화면은 상담원 화면과
      **다른 오리진**이다. 빠지면 브라우저가 프리플라이트에서 막고 **서버 로그에는 아무것도 안 남는다**
- [ ] **구글 클라우드 콘솔** — 웹 애플리케이션 OAuth 클라이언트 생성. 승인된 JavaScript 원본에
      `https://admin.solidbob.cloud` · `http://localhost:5174`. 리다이렉트 URI 는 필요 없다(GIS 는 id_token 방식)
- [ ] 붙인 뒤 실제 로그인 한 번 — 500 이 아닌 것까지 봐야 완료다

## 완료 조건

운영에서 구글 로그인 → 관리자 화면 진입이 실제로 되고, 파드를 재시작해도 같다.

## 안 하는 것

- **관리자 계정을 코드·저장소에 넣지 않는다.** `admin_account` 는 허용 목록이라 행 추가는 DB 쪽 작업이다

## 진행 (2026-09-15)

저장소 쪽은 닫았다 — `redis.yaml` · kustomization · `secret.example.yaml`(키 3종 + CORS 주의) ·
런북 **16-3**(세션 Redis) · **17-4**(첫 관리자 계정). 근거는 `_project/decisions/112`.

**남은 것은 전부 값·계정 작업이다**(저장소에 들어갈 수 없는 것들): 구글 OAuth 클라이언트 ID ·
`ADMIN_JWT_SECRET` 생성 · `server-env` patch · 허용 목록 행 1건(테이블은 이미 있다).
화면 배포는 `w4-admin-subdomain` 으로 갈랐다.

## 완료 (2026-09-15)

운영에서 **구글 로그인 → 관리자 화면 진입까지 실제로 됐다.** 닫은 것 —
Redis 파드(Running) · `server-env` 키 4종 patch + `rollout restart` · CORS 에 admin 오리진 추가
(실측: 프리플라이트 400 → **200 + allow-origin 에코**, `call` 오리진은 그대로 200) ·
`admin_account` 행 1건. 절차는 런북 **18-3** 에 남겼다(검증 뒤에 넣었다).

⚠ **남은 것 하나** — 그 행의 `agent_id` 가 `NULL` 이다. 로그인은 되지만 **블랙리스트 승인·해제는 409** 다
(`decisions/304`). 어느 상담원 마스터 ID 로 기록할지는 정해지지 않았다 → [미결](/open-items/).
