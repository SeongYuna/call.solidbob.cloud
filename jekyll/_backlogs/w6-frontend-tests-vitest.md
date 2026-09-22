---
title: "프론트 테스트 도입 — vitest · WS 파서 4종부터"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 6
priority: 78
date: 2026-09-22
requirement:
  - "QUA-1"
paths:
  - "apps/call/src/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

프론트 테스트가 0 이다(09-22 최종 QA 「테스트·CI 위생」). `apps/call` 의 WS 파서(자막 · 추천 · 컴플라이언스 · 종료)는 서버 필드명이 바뀌면 조용히 깨지는 곳이라 여기부터.

## 완료 조건

- [ ] `vitest` 설정 · 파서 4종 테스트(실제 방송 JSON 표본으로)
- [ ] `npm test` 가 `package.json` 에 있다 — CI 잡·룰셋 추가는 정성윤(`test.yml` job + `ruleset-main.json`)

근거: `rfp-harness.md` QUA-1.
