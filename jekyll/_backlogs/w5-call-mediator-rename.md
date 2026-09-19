---
title: "gateway → call-mediator 개명 — 저장소 · CI · 배포 · 프론트"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 5
priority: 1
date: 2026-09-17
paths:
  - "services/call-mediator/*"
  - "infra/k8s/base/call-mediator.yaml"
  - ".github/workflows/release.yml"
---

## 무엇을

`services/gateway` 를 `call-mediator` 로 개명한다 — 디렉터리 · CI job · 이미지 · k8s 오브젝트 · 시크릿 ·
공개 경로 · 환경변수 · 프론트 식별자까지 전부. 근거·대응표: `_project/decisions/115`.

## 왜

「게이트웨이」가 보안 장치로 읽히는 오해가 반복됐다. 이 부품은 중계(GoF 메디에이터)이고 경계 장비는 Traefik 이다.

## 완료 조건

- [x] 저장소 개명 + 검증(call-mediator 101/101 · 프론트 2종 빌드 · server·ai pytest · 계약 · 사이트 링크)
- [x] Docker Hub 레포 `callguard-call-mediator` 생성 (없으면 `tag-check` 가 401 로 죽는다)
- [x] EC2 시크릿 `call-mediator-tokens` 를 옛 값 그대로 복사 — **09-19 밖에서 확인**: 번들에 구워진 뷰 토큰으로 `/call-mediator/ws` 가 **101**(토큰 없으면 401). 옛 값이 살아 있다는 뜻이다
- [x] Vercel `kxu6` 에 `VITE_CALL_MEDIATOR_WS_URL` · `VITE_CALL_MEDIATOR_DEMO_BASE_URL` 추가 — **09-19 확인**: 배포 번들(`index-Dwmrb6cW.js`)에 `wss://server.solidbob.cloud/call-mediator`·`…/ws?token=` 둘 다 구워져 있고 `gateway` 문자열은 0회
- [x] PR 연 뒤 main 룰셋 필수 검사 `gateway` → `call-mediator` — PR #101·#102 가 머지된 것이 곧 증거다(룰셋이 없는 검사를 기다렸다면 잠겼다). ⚠ 라이브 룰셋 직접 조회는 `gh` 있는 머신에서
- [x] 머지 · 배포 뒤 `/call-mediator/health` ok — **09-19 실측**: `status ok` + 넷 전부 true(`stt_credentials`·`stt_caps`·`ingest_token`·`view_token`), `/call-mediator/dev` 200 · `/call-mediator/ingest` 토큰 없이 401 · **옛 `/gateway/*` 는 404**
- [x] EC2 옛 Deployment·Service·시크릿 삭제 — **09-19 SSM 으로 확인: 지울 것이 없었다.** `deploy`·`svc`·`secret`·`ingress` 어디에도 `gateway` 이름이 없고(시크릿은 `call-mediator-tokens`·`callguard-server-tls`·`gcp-stt-credentials`·`server-env` 넷뿐), 파드도 넷 다 새 이름이다. 적용 스크립트에 prune 이 없어 남을 줄 알았는데 남지 않았다
- [x] 로컬 `.env` 키 변경 — `CALL_MEDIATOR_PORT`·`_INGEST_TOKEN`·`_VIEW_TOKEN` 만 있고 `GATEWAY_*` 는 0개(09-19 확인)
- [ ] **Vercel 옛 변수 `VITE_GATEWAY_WS_URL`·`VITE_GATEWAY_DEMO_BASE_URL` 삭제 — 이것 하나 남았다.** 콘솔에서만 보이고 CLI·토큰이 이 머신에 없다. 새 변수는 이미 번들에 구워져 도는 중이라 **지워도 화면에 영향 없다**
- [x] `STATE.md` 의 「문서는 새 이름, 운영은 옛 경로」 문장 걷기 — 09-19. 런북 19-1 머리말 경고·미결 항목도 같이

> **09-19 SSM 실측으로 거의 다 닫혔다.** 운영 이미지가 **`callguard-server:0.1.18` · `callguard-call-mediator:0.2.1`**
> 로 떠 있고(파드 생성 09-18 08:23 UTC), 옛 `gateway` 오브젝트는 **한 개도 없다.**
> **남은 것은 Vercel 옛 변수 둘 삭제뿐**이고 그것은 화면 동작에 영향이 없다.

옛 진행 기록·결정 기록·티켓 슬러그는 고치지 않는다(`decisions/115` 「바꾸지 않은 것」).
