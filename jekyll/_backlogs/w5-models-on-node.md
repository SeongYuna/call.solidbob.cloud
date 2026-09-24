---
title: "모델을 운영 노드에 CPU 로 싣는다 — NER + 임베딩 (결정 124, 09-30 판정용)"
assignee: "정성윤"
role: "infra"
status: "done"
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

- [x] ① ~~류준 님~~ **정성윤(09-22)** — 류준 님 맥 자격증명 문제로 방향을 바꿔(류준 님 09-22 메시지) 이 머신(WSL)에서 HF 로 받아 올렸다. `koe5` 2.2GB · `koelectra-ner` 430MB · 파일 20개 · 해시 목록 `s3://assist-apne2/models/models-sha256.txt`. ⚠ **류준 님 로컬 폴더와의 해시 대조는 아직이다** — 류준 님이 `find koe5 koelectra-ner -type f | sort | xargs shasum -a 256` 결과를 보내면 대조한다 → **✅ 09-22 오후 대조 끝(정성윤)**: NER 은 HF 커밋까지 같다(`7fe2d32`). KoE5 는 커밋이 다르지만(운영 `237b580` 08-26 · 류준 `bc6d284` 2024-12) 두 커밋 사이 바뀐 파일은 **README.md 하나**다 — HF tree API 로 가중치·설정 파일 해시 전부 동일 확인. 운영 모델 = 류준 님 측정 모델
- [x] ② PR(09-22) — 서버 이미지 torch CPU 휠 · 파드 hostPath `/opt/callguard/models` · 메모리 상한 1 Gi → 3 Gi · 태그 `0.1.26` · 런북 11장 「실물 — CPU 노드에 모델 싣기」 · 머리말 다섯 번째 정정
- [x] ③(09-22 정성윤, HASH-OK) 노드로 받기 — SSM `aws s3 sync` (디스크 여유 19 GB, 09-22)
- [x] ④(09-22, 100청크·1024차원 벡터 확인) 벡터 재적재 — 새 이미지의 서버 파드 안에서 `index_knowledge_base.py --to-es --recreate`. **임베딩 켜기 전에**
- [x] ⑤(09-22 — `/health` spokes 에 `pii_ner`·`retrieval_dense`·`retrieval_cache`, 재시작 0, 노드 여유 3.2GB) 하나씩 켜기 — `server-env` 백업 → `PII_NER_MODEL_DIR` → `spokes` 확인 → `RETRIEVAL_EMBED_MODEL_DIR` → 확인. 메모리·재시작 횟수
- [x] ⑥(09-22, 류준 SYN-010·SYN-008 운영 투입 + 정성윤 수동 검색) 검증 — **마스킹 ✅**(이름만 답한 발화·주소·전화번호가 자막·DB 모두 가려짐) · **`/health` ✅** · **검색 구간**: SYN-008 추천 8건 394~778ms, SYN-010 첫 추천 2건 3,300·2,118ms(`internal_latency_ms` 상한). ⚠ 3,300 의 원인은 **미해결** — `0.1.31` 새 파드에서 정성윤이 `/hub/search` 로 첫 요청부터 재 보니 **0.58 / 0.58 / 0.62s, 같은 질문 반복 0.05s(캐시)** 라 단순 예열로 재현되지 않았다. 임베딩은 켜 둔다(124 ⑥ 의 「넘으면 끔」은 p95 기준이지 첫 요청 하나가 아니다)
- [x] ⑦(09-22 류준, 커밋 `e966b62`, 3회 최저, 로컬 기록 DB) — **운영 모델 구성(NER+KoE5, 리랭커 없음) run_id 3: Recall@5 0.969(93/96) · MRR 0.868** / 운영 구성 run_id 4: 0.812 · 0.635. C-5 누락 0(n 28) · F-2 1.0(n 99, 규칙표 상한). ⚠ `eval_run` 에 검색·NER 구성 컬럼이 없어 DB 만으로는 run 3·4 가 구분되지 않는다(류준 로그 09-22-05 · 내보내기 파일에 적힘)

## 왜 지금인가

성공 조건 둘(검색 품질 · STT 오류 내성) 모두 모델 구성에서만 목표를 넘는다. 사용자가 09-22 에 「모델 구성으로 시도」를 골랐다.

## 취소한 티켓

`w6-gpu-model-instance` · `w6-ai-model-http-surface` · `w6-server-remote-model-adapter` — 전용 GPU 와 원격 어댑터가 필요 없어졌다(`124`).

## 결과 (2026-09-22)

①~⑦ 전부 끝났다 — 운영 `/health` spokes 에 `pii_ner`·`retrieval_dense`, 해시 대조 일치, 공식 측정 run_id 3(0.969/0.868)·4(0.812/0.635, 커밋 `e966b62`, 로컬 기록 DB). 첫 검색 지연(SYN-010 3,300ms)은 이 티켓 밖 — `w7-latency-budget` 과 미결 「운영 첫 검색 요청이 3,300ms」에서 잇는다.
