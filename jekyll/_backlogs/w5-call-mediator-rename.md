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
- [x] EC2 시크릿 `call-mediator-tokens` 를 옛 값 그대로 복사
- [x] Vercel `kxu6` 에 `VITE_CALL_MEDIATOR_WS_URL` · `VITE_CALL_MEDIATOR_DEMO_BASE_URL` 추가
- [x] PR 연 뒤 main 룰셋 필수 검사 `gateway` → `call-mediator`
- [x] 머지 · 배포 뒤 `/call-mediator/health` ok
- [ ] EC2 옛 Deployment·Service·시크릿 삭제 · Vercel 옛 변수 삭제 · 로컬 `.env` 키 변경
- [x] `STATE.md` 의 「문서는 새 이름, 운영은 옛 경로」 문장 걷기

옛 진행 기록·결정 기록·티켓 슬러그는 고치지 않는다(`decisions/115` 「바꾸지 않은 것」).
