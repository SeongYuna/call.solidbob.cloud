---
title: "하네스가 부르지 않는 지표 셋 — 「측정 불가」 줄이라도 찍는다"
assignee: "류준"
role: "ai"
status: "done"
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

## 2026-09-22 — 한 것

- **`call_temperature`(D-5)는 이 티켓을 쓴 09-21 에 이미 배선돼 있었다**(`f3f284b`) — `run_eval.py` 가 `WavVoiceOutlierAdapter` 를 꽂고 `NO_SAMPLES` 로 찍는다. 코드는 두고 회귀 테스트만 보탰다.
- **`generation`(B-4·B-5)** — `Ports.generation`(`GenerationPort`)을 맨 뒤에 붙였다. 하네스가 B 항목을 검색 → 생성 → `metrics/generation.score_shipped_cards` 로 센다(출처 표시율 · 화면 카드 환각 · 금지 표현). 포트는 모델 원출력을 돌려주지 않으므로 원출력 환각·결과 갈래는 **숫자 대신 사유**를 싣는다. 생성 포트가 없으면 「꽂지 않았다(Ollama 필요)」, 검색이 없으면 「근거 조항이 없다」, B 항목이 없으면 `NO_SAMPLES`. `run_eval.py --ollama-url` 로만 꽂는다(기본 꺼짐).
- **`asr`(A-5)** — 하네스에 STT 포트가 없고 골든셋에 음성이 없어 언제나 사유가 붙은 「측정 불가」다. 값은 `scripts/measure_a5_proficiency.py` 가 따로 잰다.
- 회귀: 새 섹션은 리포트 **맨 뒤**에만 붙는다. `run_eval.py`(ES 없음) 출력을 변경 전후로 `diff` 하면 두 섹션 추가뿐이다. `ai/apps/evaluation/tests/test_harness_silent_metrics.py` 가 섹션 순서·기존 값 불변을 지킨다.
- `eval_run_repository._MODULE_ID` 에 `generation → B-4` 를 보탰다.

## 남은 것

- `generation` 의 실제 값은 ES + Ollama 가 둘 다 있는 환경에서 `run_eval.py --ollama-url …` 로 **아직 한 번도 안 돌렸다.**
- A-5 를 하네스 안에서 재려면 hub 에 STT 포트 + 음성 골든셋이 필요하다 — 만들지는 팀 결정.
