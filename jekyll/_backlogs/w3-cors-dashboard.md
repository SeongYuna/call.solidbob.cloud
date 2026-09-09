---
title: "CORS 를 연다 — 대시보드가 브라우저에서 코어 API 를 부를 수 있게"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 3
priority: 1
date: 2026-09-09
requirement:
  - "SEC-2"
paths:
  - "server/main.py"
  - "server/core/config.py"
  - "server/tests/test_main_cors.py"
---

## 무엇을

`server/` 에 CORS 코드가 한 줄도 없어서, 백엔드가 떠 있어도 브라우저(`apps/dashboard`)가
`POST /hub/closure-checks` 같은 규칙 기반 엔드포인트조차 부를 수 없었다.
프론트 연동을 막는 세 겹(CORS → DB 스키마 → ES 적재) 중 **유일하게 `server/` 소관인 겹**이다.

## 어떻게

- `core/config.py` — `CORS_ALLOWED_ORIGINS`(쉼표 구분)를 읽는다. 비어 있으면 **로컬 Vite 둘**
  (`http://localhost:5173`·`http://127.0.0.1:5173`)만 허용. 운영 주소를 개발 기본값으로
  굳히지 않는다(`.claude/rules/dashboard.md` §5)
- `main.py` — `CORSMiddleware` 를 앱 구성 시점에 붙인다. Starlette 는 기동 뒤 `add_middleware` 를
  거부하므로 lifespan 의 settings 를 기다리지 못하고 여기서 한 번 더 `load_settings()` 를 부른다 —
  이 값 하나만이다
- `.env.example` 에 키 이름만 등록(SEC-2)

## 완료 조건

- [x] 로컬 Vite origin 의 preflight 가 200 + `access-control-allow-origin` 을 받는다
- [x] 목록에 없는 origin 에는 허용 헤더가 붙지 않는다
- [x] 환경변수 파싱(쉼표·공백)·기본값 테스트
- [x] `server` 327 통과 · 계약 4종 KEPT

## 남는 것 (인프라)

운영 origin 값은 **대시보드를 어디서 서빙할지**가 정해져야 채울 수 있다. 같은 도메인에서 Caddy 가
정적 파일로 내주면 CORS 자체가 필요 없고, 다른 도메인이면 배포 env 에 `CORS_ALLOWED_ORIGINS` 를 넣는다.
런북 16-1 의 주입 환경변수 목록에 이 키가 없다 — [미결 항목](/open-items/) 참조.
