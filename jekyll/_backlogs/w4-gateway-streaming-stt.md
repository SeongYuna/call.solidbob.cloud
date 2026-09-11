---
title: "게이트웨이 — 오디오 중계 + Google STT 스트리밍 + 서버 전달"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 4
priority: 1
date: 2026-09-11
requirement:
  - "A-1"
  - "A-2"
  - "A-3"
  - "A-4"
  - "COST-1"
  - "SEC-1"
paths:
  - "services/gateway/*"
---

**「필수」 블록 A 인데 3주 동안 코드가 0줄이었다.** 기획서 역할표(`_project/plan.md` 7.1절)·
`decisions/019`("정성윤에게 남는 것: 게이트웨이(A-1·A-2)")가 정성윤 몫으로 적어 뒀는데 **티켓이
한 번도 없어서** 칸반에 안 보였다. STT 쪽 티켓은 [w1-stt-billing-quota](/backlog/w1-stt-billing-quota/)
(완료)·[w2-stt-batch](/backlog/w2-stt-batch/)(배치) 둘뿐이었다.

## 무엇을

```
[오디오 생산자] ──WS 바이너리(PCM16)──▶ services/gateway ──HTTP──▶ server (마스킹·저장·트리거)
                                          │  Google STT 스트리밍
                                          ▼
                              [대시보드] ◀──WS JSON── 마스킹된 전사·추천만
```

- **A-1** 스트리밍 STT — `ko-KR`, LINEAR16, interim 켬(V4 측정과 같은 설정). 5분 스트림 한도는 교대로 넘긴다
- **A-2** 화자 — V1 이 전부 모노라 **채널 분리**(연결 하나 = 화자 하나, 데모의 물리 2채널)
- **A-3** 브라우저 전달 — 대시보드가 이미 기다리는 `{type, payload}` 형식 그대로
- **A-4** 발화 구간 — Google 끝점 검출(`is_final`)에 맡긴다
- **COST-1** 2차 가드 — `data/processed/stt-usage.json` 을 배치 스크립트와 **같은 파일·같은 형식**으로 공유
- 통화를 처음 여는 순간 `POST /hub/calls` (미결 2026-09-10 항목)

## 지키는 것

- **SEC-1** — 원문은 게이트웨이 → 서버로만 간다. 대시보드는 서버가 마스킹해 돌려준 것만 받고,
  서버가 실패하면 **아무것도 보내지 않는다.** 로그에 전사 문자열을 남기지 않는다
- 브라우저 마이크 캡처(①)는 `apps/` 라 조서희 전담이다 — 여기서 만들지 않는다. 생산자 쪽 계약만 정한다

## 완료 조건

- [x] `services/gateway` 단위·통합 테스트 + 타입체크, CI `gateway` job — 53개 통과(2026-09-11).
  CI job 은 **아직 main 룰셋의 필수 통과 검사가 아니다**
- [x] 로컬에서 실제 Google STT → 로컬 server → 대시보드 WS 까지 한 번 관통 (2026-09-11) — AI Hub 음성 2.8초,
  모노·스테레오(채널 분리) 둘 다. COST-1 두 동작(캡 초과면 거절 · 도는 중 캡에 닿으면 끊기)도 실제 장부로 확인.
  ⚠ **추천 카드가 화면까지 가는 것은 못 봤다** — 이 머신에 ES 가 없어 서버 `/hub/recommendations` 가 500 이었다.
  ⚠ **DB 저장도 이 관통에서는 안 봤다** — Neon 이 09-09 이전 DDL 이라 final 저장이 실패해, 서버를 DB 없이(로그 어댑터) 띄웠다
- [x] **`/ws`·`/ingest` 접근 제어** — 배포보다 먼저였다(a5 세션 지적). 문마다 토큰, 루프백 밖은 토큰 없으면 401
  (fail-closed), 과금 문 비밀은 헤더로만. 테스트 65개 · 비루프백 주소로 실측(2026-09-11).
  **a5 세션이 따로 실측해 전 조합이 일치했다** — 토큰 미설정 바깥 8조합 401 · 설정 후 문마다 맞는 토큰만 101 · 로그에 토큰 0건.
  ⚠ 뷰 토큰은 브라우저가 내므로 비밀이 아니다 — **사람별 인증은 남았다**(서버와 같은 미결)
- [x] 배포(이미지·k8s·Ingress 경로·`release.yml`) — PR #68, 2026-09-11. 운영 `/gateway/health` 설정 넷 전부 true ·
  토큰 없는 `/gateway/ws`·`/gateway/ingest` 401(런북 19-1 12·13번). ⚠ 첫 시도는 Docker Hub 새 저장소가 **비공개**로 만들어져
  ImagePullBackOff — 공개로 바꾸고 재실행 두 번 만에 초록(두 번째는 Deployment 가 이미 «진행 기한 초과» 로 표시돼 있어서)
- [ ] `.env.example` 에 `GATEWAY_PORT`·`CORE_API_URL`·`GATEWAY_INGEST_TOKEN`·`GATEWAY_VIEW_TOKEN` — 보호 훅 때문에 사람이 넣는다
  (이 티켓 밖으로 옮긴다 — [미결](/open-items/) 「`.env.example` 키 넷」. 적용할 파일은 준비돼 있다)
