---
title: "모델 학습 — C-6 폭언 분류기 · 조항 검색 임베딩 미세조정 · NER KLUE 교체 · 학습 전후 평가"
assignee: "류준"
role: "ai"
status: "done"
sprint: 8
priority: 1
date: 2026-10-15
requirement:
  - "C-6"
  - "B-2"
  - "C-5"
  - "E-1"
paths:
  - "scripts/train/*"
  - "ai/apps/call_guard/*"
  - "ai/apps/pii_ner/*"
  - "ai/provider.py"
---

## 무엇을

`decisions/223`(`210` 철회) — 맥북(M5 · MPS)에서 되는 학습을 오늘 끝내고 같은 하네스로 학습 전후를 잰다.

1. **C-6 폭언 분류기** — KcELECTRA-base 미세조정(kocohub 혐오표현 + AI Hub 상담 발화 정상 예시). 규칙 위에 얹는 2단(`ModelCallGuardAdapter`)
2. **조항 검색 임베딩 미세조정** — KoE5 를 doc2query 생성 질문 680건(골든셋과 겹침 0)으로 대조 학습
3. **NER 교체** — `korean-pii-ner-v3`(KLUE 기반, CC-BY-SA) — 라벨 대응만 바꿨다(`decisions/222`)
4. **다국어 질의** — KoE5 · bge-m3 · multilingual-e5 · ko-sroberta 를 en/vi/zh 40문항으로 비교

## 왜

발표 검토에서 「학습을 아예 안 했다 · GPU 가 없다」 가 가장 큰 허점이었다. GPU 가 없는 것은 운영 서버뿐이다.

## 완료 조건

- 학습 데이터와 평가 데이터가 갈려 있다(골든셋 미사용) — 생성 단계에서 같은 문장을 버린 기록이 있다
- 결과가 `docs/ai-part-review/10_training_results.md` 에 숫자·표본 수·명령과 함께 있다(실패한 것도)
- 운영 반영은 `w8-model-deploy-seongyun`(정성윤) — 모델은 S3 `assist-apne2/models/` 에 올리고 해시 목록을 갱신했다

## 결과 (2026-10-15)

`docs/ai-part-review/10_training_results.md` — 분류기·NER 교체는 올린다, KoE5 미세조정은 **실패**(다국어 나빠짐)라 안 올린다. 운영 반영은 `w8-model-deploy-seongyun`.
