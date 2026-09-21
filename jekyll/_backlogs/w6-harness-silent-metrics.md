---
title: "하네스가 부르지 않는 지표 셋 — 「측정 불가」 줄이라도 찍는다"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 71
date: 2026-09-21
requirement:
  - "E-1"
paths:
  - "ai/apps/evaluation/*"
---

## 무엇을

`ai/apps/evaluation/metrics/` 의 **`generation`(B-4·B-5) · `asr`(A-5) · `call_temperature`(D-5)** 를
`run_eval` 리포트에 나타나게 한다.

## 왜

셋은 `harness.py`·`run_eval.py` 어디서도 import 되지 않고 별도 스크립트로만 돈다([미결 항목](/open-items/) 09-21 grep).
그래서 리포트에 **「측정 불가」로도 나오지 않는다 — 침묵 누락이다.** 절대 원칙 10 의 취지로는
잴 수 없으면 잴 수 없다고 찍혀야 한다. 빈칸은 읽는 사람이 「문제 없음」으로 읽는다.

## 완료 조건

- [ ] 셋이 리포트에 줄로 나온다 — 값이 있으면 값, 없으면 **사유가 붙은 「측정 불가」**
- [ ] 표본이 없는 경우 `NO_SAMPLES` 와 미구현을 구분한다(지금 하네스가 이미 하는 구분 그대로)
- [ ] 기존 지표 출력은 바뀌지 않는다(회귀 테스트)
