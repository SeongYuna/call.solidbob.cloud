---
title: "재연결하면 발화 번호가 1부터 다시 매겨져 저장된 전사를 덮어쓴다 — 화자도 틀린 채 남는다"
assignee: "정성윤"
role: "ai"
status: "done"
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

- [x] 재연결 테스트 — 닫고 다시 열어 보낸 줄이 새 번호로 붙는다(미디에이터 단위 테스트)
- [x] 서버 테스트 — 확정 segment 를 다른 화자로 덮으면 409
- [ ] 운영에서 위 1~3 재현 → 7건

근거: 진행 기록 `2026-09-22-18-seongyun` (데이터) 행.

## 2026-09-22 — 정성윤이 넘겨받아 고쳤다 (운영 확인 전)

**담당 이관 장민석 → 정성윤.** `todo` 라 보존할 수행 기록이 없다(`CLAUDE.md` §4). 원인의 절반이 콜 미디에이터(정성윤 주 담당)이고 `decisions/302` 로 `server/` 도 고칠 수 있다. 장민석 님 브랜치에 같은 파일 변경이 없음을 확인하고 시작했다.

- **서버** — `POST /hub/calls` 가 이미 있던 통화면 응답에 **`last_segment_id`**(저장된 가장 큰 발화 번호, 문자열)를 싣는다. 포트 `CallStartRecordPort.last_segment_id`(기본 0 — 저장 안 하는 로그 어댑터는 그대로) · PostgreSQL 은 `SELECT COALESCE(MAX(segment_id),0) … WHERE call_id` 로 그 통화 안에서만 센다
- **서버 방어선** — `transcript_segment` UPSERT 에 `WHERE speaker = EXCLUDED.speaker`. 화자가 다르면 0행 → **`SegmentSpeakerConflictError` → 409**, 커밋·마스킹 구간 지우기 없이 나간다. 같은 화자의 재전송(재시도·마스킹 갱신, `205`)은 그대로 덮는다. 콜 미디에이터는 4xx 를 다시 보내지 않고 로그만 남긴다
- **콜 미디에이터** — `HubPort.startCall` 이 `{ lastSegmentId }` 를 돌려주고, 통화 객체의 번호 카운터가 그 뒤에서 센다(`SegmentCounter.resumeAfter`). 채널은 `started` 를 기다린 뒤 첫 번호를 받으므로 순서가 보장된다. 필드가 없는 옛 서버면 0 — 지금처럼 1부터
- **검증** — server 1,434 passed · 계약 5 KEPT · call-mediator 157/157 · `tsc` 통과. 새 테스트: 서버 단위 9(포트·인터랙터·라우터·리포지토리) + integration 1(실 DB — CI) · 미디에이터 4. **이어 세는 한 줄을 끄면 미디에이터 새 테스트 2건이 실패**하는 것을 확인했다
- **태그** server `0.1.37` · call-mediator `0.2.7`(열린 브랜치·레지스트리 어디에도 없음 — `decisions/131`)

**안 고친 것** — 다시 연 통화의 `utterance_end_ms` 는 여전히 **새로 연 시각** 기준이다(통화 객체의 `startedAtMs` 가 메모리라 같이 버려진다). 순서가 뒤섞이지는 않지만 시각이 앞 발화보다 작아질 수 있다 — 화면은 번호순이라 보이지 않는다. 필요하면 `started_at` 을 응답에서 받아 쓰면 된다(별도).

**남은 것 → done 조건** — 배포 뒤 운영에서 티켓 위 「무엇을 봤나」 1~3 을 그대로 재현해 **7건**이 되는지(수동 QA 「(데이터)」 행 재확인).

## 2026-09-22 (밤) — 운영 확인 → done

PR #139 머지 → 릴리스 성공(server `0.1.37` · call-mediator `0.2.7`). 운영에서 QA 때와 같은 순서로 재현: `test-qa-reuse` 에 여섯 줄 → 채널 닫기 → 같은 통화 다시 열어 고객 한 줄 → **저장 7건, 새 줄은 segment 7**, 1번 상담원 인사 그대로. 오후 QA 에서는 같은 순서에서 1번이 덮였다.
