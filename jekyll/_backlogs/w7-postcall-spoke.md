---
title: "통화 후 요약 스포크 — D-1·D-2·D-3 구현"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 7
priority: 74
date: 2026-09-15
requirement:
  - "D-1"
  - "D-2"
  - "D-3"
depends_on:
  - "w7-postcall-contract"
paths:
  - "ai/apps/postcall/*"
---

## 무엇을

`POST /hub/calls/{call_id}/close` 뒤에 붙는 **실제 요약·분류·후속조치 추출**을 만든다.
계약·배선·DTO 는 [w7-postcall-contract](/backlog/w7-postcall-contract/)에서 끝났고 **지금은 501** 이다.

## 경계

계약 티켓이 적어 둔 그대로다 — **요약·분류를 실제로 하는 것은 `ai/`** 이고,
`server/` 는 계약·배선·저장까지다. 이 티켓이 `ai/` 몫이다.

## 이미 타입에 박혀 있는 제약 둘

- **DTO 이름이 `CallSummaryDraft` 다.** D-2 유형 분류는 모델 판정이므로 **확정이 아니라 초안**이고,
  `confirmed` 는 **모델이 `True` 를 실어 보내도 서버가 `False` 로 덮는다.** 확정은 상담원이 화면에서 한다
- **인터랙터가 `summary_text` 에 손대지 않는다.** 손대면 모델 출력과 화면 표시가 달라져
  **환각 추적이 끊긴다** — [6주차 환각 건수 비교](/backlog/w6-hallucination-eval/)가 무의미해진다

절대 원칙 9(판정은 규칙이, 설명만 LLM이)를 계약 형태로 옮긴 것이므로 **스포크가 이것을 되돌리지 않는다.**

## SEC-1

받는 것도 돌려주는 것도 **마스킹 완료본뿐**이다. 통화 후 처리라고 원문을 다시 꺼내오지 않는다 —
애초에 저장돼 있지 않다.

## 완료 조건

- [ ] D-1 요약 · D-2 유형 분류 · D-3 후속조치 추출
- [ ] 501 이 사라지고 `/health` 스포크 목록에 뜬다
- [ ] D-2 분류 정확도를 잰다. **감정분석 기반 상담품질 평가는 사람을 점수 매기는 용도로 쓰지 않는다**([부록 A-1](/docs/12/))
