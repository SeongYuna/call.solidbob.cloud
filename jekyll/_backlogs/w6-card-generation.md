---
title: "근거 기반 카드 생성 — B-4~B-6"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 6
priority: 61
date: 2026-09-15
requirement:
  - "B-4"
  - "B-5"
  - "B-6"
paths:
  - "ai/apps/generation/*"
---

## 무엇을

검색한 조항으로 **요약 카드를 생성**하고 **출처를 붙인다**. `ai/apps/generation/` 이 아직 없다.

## 모델은 정해져 있다 — 호출 규약까지

`_project/decisions/010`: **EXAONE-4.0-1.2B**(250토큰 2.0~2.1초 실측).
런북 14장이 Ollama 호출 규약을 적어 두었다 — **`think:false` + `/api/chat` 이 필수**다.
안 지키면 응답에 사고 과정이 섞여 나온다.

## 왜 `ai/` 인가

모델을 로드한다. `server/.importlinter` 계약 2 가 `server/` 안에서 `transformers`·`langchain` import 를
막는다 — [요구사항표 3.1절 아래 「2026-08-26 위치 정정」](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/.claude/rules/rfp-harness.md)이
이 표를 `server/apps/generation/` → `ai/apps/generation/` 으로 옮겨 적은 이유가 그것이다.

## 절대 원칙 9 — 판정은 규칙이, 설명만 LLM이

카드는 **설명**이다. 어느 조항이 정답인지는 **검색이** 정하고, 생성은 그 조항을 읽기 좋게 옮긴다.
생성 모델이 조항을 고르거나 «이 절차는 불가능합니다» 같은 판정을 하면 그건 범위를 넘은 것이다.

## 완료 조건

- [ ] **출처 표시율 100%** — 카드마다 `doc_id`(문서명·조항)가 붙는다. 없으면 카드를 만들지 않는다
- [ ] **근거가 부족하면 「관련 문서 없음」을 반환한다** — 지어내지 않는다([2.3절](/docs/02/))
- [ ] [부록 A-1](/docs/12/) 금지 표현이 템플릿 어디에도 없다 — 「안전합니다」·「위험도 78%」·등급·점수
- [ ] 생성 지연을 재서 [4.1절](/docs/04/) 예산 안인지 본다

## 주의

**약관 원문을 그대로 싣지 않는다**(절대 원칙 6). 요약·해석 + 출처(문서명·조항)만 싣는다.
