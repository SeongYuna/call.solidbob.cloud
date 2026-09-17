---
title: "모노 녹음 화자 분리 — /ingest speaker=auto (첫 화자 = 상담원)"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 6
date: 2026-09-14
requirement:
  - "A-2"
paths:
  - "services/call-mediator/src/adapters/google_stt.ts"
  - "services/call-mediator/src/adapters/ws_server.ts"
  - "services/call-mediator/src/domain/diarization.ts"
---

## 무엇을

A-2 는 채널 분리만 한다. AI Hub 녹음이 전부 모노라 재생하면 두 사람이 한 화자로 찍힌다
([미결](/open-items/) 2026-09-11). 생산자가 `speaker=auto` 를 주면 구글 화자 분리(diarization, 2명)를 켜고
**먼저 말한 화자를 상담원**으로 친다 — 120 은 상담원이 먼저 인사한다. 규칙이 추측이라는 것은 `decisions/303` 에 남긴다.

## 완료 조건

- [x] `speaker=auto` 채널 — final 의 단어 화자 태그로 발화를 나눠 agent/customer 로 보낸다 (테스트, 가짜 구글 응답)
- [x] 기본(`agent`·`customer`)은 지금과 같다
- [x] `decisions/303` — 규칙·한계·되돌리는 법
- [ ] ⚠ 실제 구글 응답으로 확인 — **미검증**(2026-09-14, 이 머신에 키·음성 없음). 티켓은 코드 범위로 닫고 [미결](/open-items/)로 넘긴다
