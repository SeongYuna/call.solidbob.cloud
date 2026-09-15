---
title: "토큰 비용 측정 — 통화 1건이 얼마인가"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 7
priority: 73
date: 2026-09-15
requirement:
  - "COST-1"
depends_on:
  - "w6-card-generation"
paths:
  - "ai/apps/generation/*"
---

## 무엇을

**통화 1건당 토큰 수와 비용**을 잰다([8주 마일스톤](/docs/08/) 7주차).

## 우리 구성에서 「비용」이 무엇인가

생성은 **로컬 Ollama(EXAONE-4.0-1.2B)** 라 API 과금이 없다 —
**돈으로 나가는 것은 GPU 점유 시간**이고, 그것을 대신 재는 지표가 토큰 수와 생성 시간이다.
**API 요금표를 가져다 곱하지 않는다**(우리가 내지 않는 돈이다).

**실제로 돈이 나가는 것은 Google STT** 다(COST-1). 그쪽은 이미 이중 캡이 걸려 있다 —
GCP 쿼터 하드 리밋 + `STT_MAX_SECONDS_PER_DAY`/`_MONTH`([w1-stt-billing-quota](/backlog/w1-stt-billing-quota/)).

## 완료 조건

- [ ] 통화 1건당 **입력·출력 토큰 수**(카드 n장 기준)와 생성 시간
- [ ] STT 초 수도 함께 — **일·월 캡 대비 몇 %** 인지
- [ ] GPU 1장을 파드끼리 나눠 쓰는 구성(런북 11장)에서 **동시 통화 몇 건까지 버티는지** 추정 근거를 적는다
- [ ] 추정이면 **「추정」이라고 적는다**(절대 원칙 2·10)
