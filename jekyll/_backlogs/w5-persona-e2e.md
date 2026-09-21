---
title: "합성 통화 E2E 왕복 검사 — 대본 → 콜 미디에이터 → 서버 → DB → 대시보드 API"
assignee: "류준"
role: "ai"
status: "done"
sprint: 5
priority: 59
date: 2026-09-18
requirement:
  - "C-5"
  - "C-6"
  - "B-1"
  - "SEC-1"
paths:
  - "scripts/persona_sim/e2e_check.py"
  - "scripts/persona_sim/e2e/*"
  - "scripts/persona_sim/E2E.md"
depends_on:
  - "w5-persona-sim-scripts"
---

## 무엇을

합성 대본 한 건이 실제 통화와 같은 길 — 재생기 → 콜 미디에이터 `/dev/text` → `POST /hub/calls`·`/hub/transcripts` →
마스킹·트리거·검색·콜 가드·컴플라이언스 → **PostgreSQL** → `/ws` → 통화 후 `POST …/close` → 대시보드가 읽는
`GET /hub/calls/{id}/transcript`·`/record` — 를 끝까지 갔다 오는지 **규칙으로** 판정하는 도구(`e2e_check.py`)와 보고서.

## 왜

09-17 로컬 E2E 는 사람이 눈으로 봤다(4건). 대본이 24건으로 늘면 눈으로는 못 본다. 대본에 라벨(`expected`)이 있으니
왕복·SEC-1·라벨 재현을 자동으로 대조할 수 있다.

## 판정 (전부 규칙)

- 왕복: 확정 자막 수 == 턴 수 · 화자 순서 · DB `transcript_segment` 행 수
- SEC-1: 대본의 가짜 PII 원문이 DB 본문·`/transcript` 응답에 한 글자도 없음
- 라벨 재현: 기대 콜 가드 갈래 · 컴플라이언스 seq · 필요서류가 `/record`·DB 에 있는지 — 누락·과잉 건별
- 통화 후: 요약 초안 존재

## 완료 조건

- [x] `e2e_check.py` + 순수 판정 함수 pytest(13)
- [x] 실행 보고서(`data/processed/persona-e2e/2026-09-18-1618.md`) — 실패는 원인 가설과 함께 그대로
- [x] 24건 실행 — ✅ 3 · ❌ 21(전부 시스템 쪽: 컴플라이언스 미배선 · 필요서류 규칙표 미등록/1순위 카드 의존 · SYN-020 이름 누출)
- [x] 대시보드 실화면 확인 — SYN-020(자막·마스킹·필요서류·통화 후 처리·상담기록 자막 보기, 09-18)
- [x] **결함 처리 후 재실행(09-18 2차) — ✅ 22 · ❌ 2**(남은 둘은 검색 순위 → `decisions/208`). 컴플라이언스 배선·저장, 규칙표 29, C-5 이름·P4, 대본 정합, `document` 시드

## 한계 (절대 원칙 10)

STT 미경유 — 인식 오류 0 이므로 여기서 나오는 통과·실패는 **배선·규칙의 동작 확인**이지 성능이 아니다. `source: synthetic`.

---

> **보드 최신화 (2026-09-21, 정성윤 — 사용자 지시로 전체 보드를 한 번에 맞췄다).** `in-progress` → `done`. 완료 조건 다섯이 전부 체크돼 있다(09-18 2차 실행 ✅22 · ❌2).
> 남은 ❌ 둘(SYN-011·021)은 검색 순위 문제라 **모델이 운영 경로에 붙어야 풀린다** — `208` 이 아니라 `decisions/121` 의 몫이 됐다 →
> [w6-gpu-model-instance](/backlog/w6-gpu-model-instance/). 판정이 틀렸으면 류준 님이 되돌린다.
