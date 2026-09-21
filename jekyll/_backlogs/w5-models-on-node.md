---
title: "모델을 운영 노드에 CPU 로 싣는다 — NER + 임베딩 (결정 124, 09-30 판정용)"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 5
priority: 61
date: 2026-09-22
requirement:
  - "B-2"
  - "C-5"
paths:
  - "infra/docker/server.Dockerfile"
  - "infra/k8s/base/server.yaml"
depends_on:
  - "w5-ingest-auth-fail-closed"
---

## 무엇을

`_project/decisions/124` 의 1~7단계. GPU 없는 `t3.large` 에 NER(0.45 GB)과 KoE5 임베딩(2.2 GB)만 싣는다. 리랭커는 뺀다.
09-30 까지 `/health` 의 `spokes` 에 `pii_ner`·`embedding` 이 보이면 모델 구성으로 판정하고, 아니면 `121` §5 대로 운영 구성으로 판정한다.

## 순서 (앞이 안 되면 뒤를 하지 않는다)

- [ ] ① 류준 님 — 모델 두 폴더를 `s3://assist-apne2/models/{koelectra-ner,koe5}/` 에 올리고 해시를 여기에 적는다
- [ ] ② PR — 서버 이미지 torch CPU 휠 · 파드 hostPath `/opt/callguard/models` · 메모리 상한 1 Gi → 3 Gi · 태그 올림 · 런북 11장 정정
- [ ] ③ 노드로 받기 — SSM `aws s3 sync` (디스크 여유 19 GB, 09-22)
- [ ] ④ 벡터 재적재 — 새 이미지의 서버 파드 안에서 `index_knowledge_base.py --to-es --recreate`. **임베딩 켜기 전에**
- [ ] ⑤ 하나씩 켜기 — `server-env` 백업 → `PII_NER_MODEL_DIR` → `spokes` 확인 → `RETRIEVAL_EMBED_MODEL_DIR` → 확인. 메모리·재시작 횟수
- [ ] ⑥ 검증 — SYN-010 합성 통화 1건, 검색 구간 p95 ≤ 1,000 ms, 이름만 넣은 발화 마스킹
- [ ] ⑦ 류준 님 — `run_eval.py --runs 3 --record` 로 모델 구성 값을 실행 ID 와 함께

## 왜 지금인가

성공 조건 둘(검색 품질 · STT 오류 내성) 모두 모델 구성에서만 목표를 넘는다. 사용자가 09-22 에 「모델 구성으로 시도」를 골랐다.

## 취소한 티켓

`w6-gpu-model-instance` · `w6-ai-model-http-surface` · `w6-server-remote-model-adapter` — 전용 GPU 와 원격 어댑터가 필요 없어졌다(`124`).
