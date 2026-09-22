---
title: "B-6 「관련 문서 없음」 문턱 값을 정한다 — 팀 결정"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 62
date: 2026-09-22
requirement:
  - "B-6"
depends_on:
  - "w5-b6-no-answer-threshold"
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

[w5-b6-no-answer-threshold](/backlog/w5-b6-no-answer-threshold/) 가 정답 없음 24건과 점수 분포, 문턱 후보(dense 0.67 안팎)까지 냈다.
**값을 코드에 넣지 않았다** — 팀 결정 뒤에 넣기로 했다. 이 티켓이 그 결정과 적용이다.

## 왜 지금

운영 SYN-010 재투입(09-22)에서 「이용해 주셔서 감사합니다」에도 추천이 발동해 무관한 조항 5장이 떴다. 문턱이 없어서다.

## 완료 조건

- [ ] 결정 기록(`2xx`) — 문턱을 둘지 · 어느 계열(dense)에 어느 값 · 근거는 24건 분포
- [ ] `fallback_retriever` 에 적용 · 정답 있는 96건 Recall 변동을 로그에 그대로
- [ ] 문턱 아래면 카드 0장 + 「관련 문서 없음」이 화면에 간다
