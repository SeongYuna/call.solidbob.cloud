---
title: "모델 구성 재측정 + 하네스 기록(--record) — 판정에 쓸 수 있는 값으로"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 70
date: 2026-09-21
requirement:
  - "E-1"
  - "E-3"
paths:
  - "scripts/run_eval.py"
---

## 무엇을

**dense · 리랭커 · 규칙+NER 구성**을 현재 코드로 하네스에 다시 돌리고, `--record` 로 `eval_run` 에 남긴다.
같은 구성으로 STT 오류 내성 곡선(0~20%)도 다시 그린다.

## 왜

6주차 판정([w6-core-baseline-check](/backlog/w6-core-baseline-check/))이 09-30 이다.
2026-09-21 재측정은 **운영 구성(규칙 + BM25)만** 쟀다 — 측정한 머신에 모델 파일이 없었고 기록 DB 도 없어 `run_id` 가 없다.
모델 구성의 0.979/0.919 와 「규칙+NER 누락 0/0/1/1/1」은 **09-15 로컬 측정 그대로**다.
§5 는 값 하나에 측정일·커밋·명령·표본 수 넷을 요구한다 — **지금 그 값은 넷 중 커밋이 낡았다.**

## 완료 조건

- [ ] `scripts/run_eval.py --runs 3 --record` — 모델 구성, **3회 중 최저치**(절대 원칙 4)
- [ ] `scripts/measure_error_tolerance.py` — 같은 구성, 시드 3개
- [ ] `NO_SAMPLES` 가 어디에 남는지 그대로 보고한다(F-2 는 0건이라 측정 불가 그대로일 것이다)
- [ ] 결과를 `STATE.md` 「실측값」에 **운영 구성 옆에 나란히** 적는다 — 「로컬 측정」 꼬리표를 떼지 않는다
