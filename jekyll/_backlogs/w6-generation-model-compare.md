---
title: "생성 모델 대조군 — kanana-1.5-2.1b vs EXAONE-4.0-1.2B"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 63
date: 2026-09-15
requirement:
  - "B-4"
depends_on:
  - "w6-card-generation"
paths:
  - "ai/apps/generation/*"
---

## 무엇을

`_project/decisions/010` 이 대조군으로 올려 둔 **`kanana-1.5-2.1b-instruct`** 를
**EXAONE-4.0-1.2B** 와 **환각 건수**로 붙인다.

## 왜 6주차인가

[미결 항목](/open-items/)이 **「6주차 환각 건수 비교에서 실측한다」**고 시점을 적어 뒀다.

## ⚠ 먼저 풀어야 할 것 — 모델을 아직 못 받았다

같은 미결 항목이 적고 있다: **Ollama 공식 라이브러리·`hf.co/kakaocorp/...` GGUF 둘 다 안 됐다.**
재시도가 먼저다. **못 받으면 이 티켓은 「대조군 확보 실패」로 닫고 그 사실을 적는다** —
비교하지 않은 것을 비교한 것처럼 쓰지 않는다(절대 원칙 10).

## 완료 조건

- [ ] 같은 문항·같은 검색 결과·같은 프롬프트에서 두 모델을 돌린다
- [ ] **환각 건수 · 출처 표시율 · 지연** 셋을 나란히 적는다 — 환각만 보면 느린 모델이 이긴다
- [ ] 바꾸기로 하면 **결정 기록(`2xx`)** 을 쓴다. `decisions/010` 을 조용히 덮지 않는다
