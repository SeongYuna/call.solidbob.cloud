---
title: "재연결하면 발화 번호가 1부터 다시 매겨져 저장된 전사를 덮어쓴다 — 화자도 틀린 채 남는다"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 55
date: 2026-09-22
requirement:
  - "A-3"
  - "SEC-1"
  - "D-1"
paths:
  - "services/call-mediator/src/domain/segments.ts"
  - "services/call-mediator/src/app/call_registry.ts"
  - "server/apps/hub/adapter/outbound/postgres/transcript_segment_repository.py"
---

> **정성윤이 09-22 수동 QA(`w5-manual-qa-full-stack` Q-46) 중 만든 티켓이다.** 담당은 «제안»이다 — 미디에이터·서버 두 곳에 걸려 있다(`decisions/302`, 누구나 고친다).

## 무엇을 봤나

운영 QA 통화 `test-qa-05`:

1. 17:36 채널 둘(상담원·고객)로 여섯 줄 → segment 1~6 저장. 1번은 상담원 「안녕하세요 다산콜센터입니다」
2. 채널 둘을 닫고 17:44 같은 `call_id` 로 다시 열어 **고객** 한 줄 「서류 준비해서 오늘 안에 다 끝내고 싶어서요」
3. 결과: `GET /hub/calls/test-qa-05/transcript` 가 여전히 6건이고 **segment 1 = 상담원 · 「서류 준비해서…」** — 인사가 사라지고 고객 말이 상담원 말로 남았다. 화면도 첫 줄이 바뀌었다

## 왜

- 콜 미디에이터: 발화 번호 카운터가 **통화 객체(메모리)** 에 있다(`domain/segments.ts` `OpenSegment`). 채널이 모두 닫히면 객체가 버려지고, 다시 열면 1부터 센다
- 서버: `transcript_segment` UPSERT 가 `ON CONFLICT (call_id, segment_id) DO UPDATE SET text, is_final, utterance_end_ms` — **`speaker` 를 바꾸지 않고, 확정본을 덮어쓰는 것도 막지 않는다**

## 언제 실제로 나나

**콜 미디에이터 파드가 통화 중에 다시 뜰 때** — 09-22 에만 릴리스로 세 번(PR #131·#132·#135) 떴고 그때마다 진행 중 연결이 1006 으로 끊겼다. 재연결한 통화는 앞 대화를 뒤 대화로 덮는다. 장애 표시는 없다.

## 고치는 방향 (제안)

- 미디에이터: 통화를 다시 열 때 서버에서 그 통화의 최대 `segment_id` 를 받아 거기서 이어 센다(또는 번호에 연결 세대를 붙인다)
- 서버: 이미 `is_final = true` 인 segment 를 **다른 speaker** 로 덮는 요청은 409 로 거절하고 로그를 남긴다 — 조용히 덮지 않는다

## 완료 조건

- [ ] 재연결 테스트 — 닫고 다시 열어 보낸 줄이 새 번호로 붙는다(미디에이터 단위 테스트)
- [ ] 서버 테스트 — 확정 segment 를 다른 화자로 덮으면 409
- [ ] 운영에서 위 1~3 재현 → 7건

근거: 진행 기록 `2026-09-22-18-seongyun` (데이터) 행.
