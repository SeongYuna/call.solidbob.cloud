---
title: "관리자 로그인 운영 배선 — Redis · 시크릿 키 3종 · RDS 테이블"
assignee: "정성윤"
role: "infra"
status: "todo"
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
앱 쪽 티켓([w4-admin-google-login](/backlog/w4-admin-google-login/), 조서희)과 **갈래가 다르다** —
여기는 클러스터·시크릿·DB 쪽 몫이다.

## 왜 지금 티켓으로

2026-09-14 릴리스(PR #74) 뒤 확인한 결과, **배포 판정은 정상이고 `/health` 도 정상이다.**
`admin_auth` 의 포트 배선이 요청 스코프라 앱 기동에 영향을 주지 않기 때문이다 —
**그래서 «되는 것처럼» 보이고, 실제로 눌러 보기 전에는 아무도 모른다.**

## 할 것

- [ ] **Redis** — `infra/k8s/base/` 에 매니페스트가 0건이다. 세션 토큰이라 휘발해도 되는 성격인지
      (Deployment + emptyDir) 아니면 PVC 를 붙일지 먼저 정한다. ES 처럼 StatefulSet 까지 갈 이유는 없어 보인다
- [ ] **`server-env` 시크릿에 키 3종** — `GOOGLE_OAUTH_CLIENT_ID` · `ADMIN_JWT_SECRET` · `REDIS_URL`.
      값은 SSM 세션 안에서 `--from-env-file` 로 넣는다(런북 12-2). **GitHub·로그·이 저장소 어디에도 값이 남지 않게 한다**(SEC-2)
- [ ] **RDS 에 `admin_account` · `admin_refresh_token`** — `db/schema.sql` 에는 있고 `callguard-pg` 에는 없다.
      운영 스키마를 손으로 따라가는 방식이 이번이 세 번째다 → 마이그레이션 절차를 런북에 한 줄로 남긴다
- [ ] `.env.example` 에 위 세 키 이름 추가 (값 없이)
- [ ] 붙인 뒤 실제 로그인 한 번 — 500 이 아닌 것까지 봐야 완료다

## 완료 조건

운영에서 구글 로그인 → 관리자 화면 진입이 실제로 되고, 파드를 재시작해도 같다.

## 안 하는 것

- **관리자 계정을 코드·저장소에 넣지 않는다.** `admin_account` 는 허용 목록이라 행 추가는 DB 쪽 작업이다
