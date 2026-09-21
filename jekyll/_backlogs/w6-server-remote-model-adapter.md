---
title: "서버 원격 모델 어댑터 — 안 붙으면 규칙·BM25 로 조용히 내려간다"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 69
date: 2026-09-21
requirement:
  - "C-5"
  - "B-2"
depends_on:
  - "w6-ai-model-http-surface"
paths:
  - "server/apps/*"
---

## 무엇을

`server/` 의 모델 의존 포트(검색·NER 마스킹·생성)에 **원격 호출 어댑터**를 단다.
상대는 [ai/ 모델 HTTP 표면](/backlog/w6-ai-model-http-surface/)이다.

## 핵심은 폴백이다

지금 설계는 「모델 설정이 없으면 규칙·BM25·스니펫으로 돈다」다. **원격이 안 붙을 때에도 똑같아야 한다** —
GPU 인스턴스는 비용 때문에 **꺼져 있는 시간이 더 길다**(`decisions/121` 3·4번).
GPU 가 꺼졌다고 자막·마스킹이 멈추면 안 된다.

**특히 C-5** — 마스킹은 자막·저장의 앞단이라 NER 을 원격으로 부르면 모든 발화가 그 왕복을 기다린다.
타임아웃을 짧게 잡고, 넘으면 **규칙만으로 가린다**(재현율 우선 — 애매하면 가린다).

## 완료 조건

- [ ] 어댑터 + 타임아웃 + 폴백. **폴백이 일어난 것이 응답·로그에서 구분된다**(조용한 품질 저하를 만들지 않는다)
- [ ] 테스트 — 원격 정상 / 타임아웃 / 연결 거부 / 5xx 각각에서 자막·마스킹이 나온다
- [ ] `server/.importlinter` 계약 2(torch·transformers import 금지) 그대로 KEPT
- [ ] `/health/ready` 가 원격 모델 연결 여부를 말한다
