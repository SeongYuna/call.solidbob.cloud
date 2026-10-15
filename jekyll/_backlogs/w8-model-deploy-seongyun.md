---
title: "학습 모델 운영 반영 + GPU 학습·측정 (집 PC)"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 8
priority: 1
date: 2026-10-15
requirement:
  - "C-6"
  - "C-5"
  - "A-1"
  - "B-3"
depends_on:
  - "w8-model-training"
---

## 무엇을

`decisions/223` 의 「정성윤 님 PC 로 넘기는 것」 + 운영 반영. 류준이 맥북에서 할 수 있는 것을 먼저 끝내고 넘긴다(`w8-model-training`).

### A. 운영 반영 (서버 이미지 `0.1.50`)

PR 이 머지되면 `release.yml` 이 `0.1.50` 을 굽는다. 그 뒤 노드(SSM)에서 —

1. 모델 받기 · 해시 대조 — 런북 11장 「실물 — CPU 노드에 모델 싣기」 ① 그대로. 해시 목록 `s3://assist-apne2/models/models-sha256.txt` 은 36줄로 갱신돼 있다
2. 시크릿에 경로 두 개 — 하나씩 켜고 `/health` `spokes` 를 본다
   - `PII_NER_MODEL_DIR=/models/korean-pii-ner-v3` → `pii_ner`
   - `CALL_GUARD_MODEL_DIR=/models/call-guard-kcelectra-v2` → `call_guard_model`
3. 파드 메모리 상한은 PR 에서 3Gi → 5Gi 로 올렸다(`server.yaml`) — `kubectl top pod` · `free -h` 로 여유 1GB 이상인지 본다

되돌리기: 해당 키만 빼고 재시작 — 옛 NER(`/models/koelectra-ner`)은 노드에 그대로 있다.

### B. GPU 학습·측정 (집 PC, 맥북으로 못 하는 것)

1. `nvidia-smi` 결과(GPU 이름 · VRAM) — 발표 자료 「학습 환경」 에 적는다
2. 리랭커(`bge-reranker-v2-m3`) GPU 지연 — 후보 20 · 102문항(CPU 는 1.7~1.8초/질의)
3. Whisper large-v3-turbo 실시간 처리 배율(GPU) — 같은 20건으로
4. (여유 시) 분류기·임베딩 학습을 시드 3개로 반복 — 기준선은 최저치(절대 원칙 4)

## 완료 조건

- 운영 `/health` 의 `spokes` 에 `pii_ner` · `call_guard_model` 이 있다
- B 의 숫자가 명령·표본 수와 함께 `jekyll/_logs/` 에 남는다
