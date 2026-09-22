---
title: "최종 측정 — 발표·제출에 쓸 수치를 한 번에 고정한다"
assignee: "류준"
role: "ai"
status: "todo"
sprint: 8
priority: 86
date: 2026-09-21
requirement:
  - "E-1"
  - "E-3"
  - "QUA-2"
depends_on:
  - "w6-model-config-remeasure"
paths:
  - "scripts/run_eval.py"
---

## 무엇을

코드 동결 뒤 **하네스를 마지막으로 한 번** 돌려 발표·최종 문서에 쓸 수치를 고정한다.
검색(오류 없음 / 10%) · C-5 누락 · 오류 내성 곡선 · 환각 · 컴플라이언스 · 콜 가드 전부.

## 왜 따로 티켓인가

수치가 문서 여러 곳에 **서로 다른 날의 값**으로 흩어져 있다(09-09 · 09-15 로컬 · 09-21 운영 구성).
발표 자료가 그중 좋은 것을 골라 쓰면 **같은 슬라이드에 서로 다른 커밋의 값이 섞인다.**
한 커밋 · 한 명령 · 한 날로 고정하고, 그 밖의 값은 「그때의 값」으로만 인용한다.

## 완료 조건

- [ ] **동결 커밋**을 정하고 그 커밋에서 `--runs 3 --record` — 운영 구성과 모델 구성 **둘 다**
- [ ] 값마다 측정일 · 커밋 · 명령 · 표본 수(§5). `run_id` 가 남는다
- [ ] 「측정 불가」 목록을 함께 낸다 — F-2(채점 케이스 0건, `decisions/118`) · trigger(의도적 미배선) · A-5(데이터 미확보 시)
- [ ] 한계 넷을 값 옆에 붙인다 — C-5 「누락 0」은 **오류 없는 전사 한정** · 주입기가 실측 오류의 46.9% 를 못 흉내 낸다(곡선이 낙관 쪽) · 쌍둥이 조항 2건(`123`) · 컴플라이언스·콜 가드 1.0 은 **자기충족 상한**
- [ ] [발표 자료](/backlog/w8-presentation/)·[최종 문서](/backlog/w8-final-docs/)가 이 값만 쓴다

---

## 동결 때 그대로 돌릴 절차 (2026-09-22 준비 — **실행은 안 했다**)

> 09-22 에 같은 명령으로 운영·모델 두 구성을 이미 재 봤다(run_id 1·2, 커밋 `121157e`, [w6-model-config-remeasure](/backlog/w6-model-config-remeasure/)).
> **그 값은 동결 전 값이다** — 이 티켓의 값으로 쓰지 않는다. 동결 커밋에서 아래를 **한 번에** 다시 돌린다.

**0. 동결 커밋을 정한다** — `git rev-parse --short HEAD` 를 여기 적는다. **워킹트리가 깨끗해야 한다**
(09-22 에는 추적 안 되는 `.claude/worktrees/` 때문에 `-dirty` 가 찍혔다 — 지우거나 다른 클론에서 돌린다).

**1. 인프라** (`infra/README.md` 「로컬 개발」)
```bash
docker start callguard-elasticsearch callguard-postgres   # 없으면 README 의 docker run 두 줄
# ⚠ 5432 를 다른 프로젝트가 쓰면 Postgres 는 127.0.0.1:5434 로 띄운다(09-22 에 그랬다)
.venv/bin/python scripts/index_knowledge_base.py --to-es --recreate --embed-model models/koe5
export ELASTICSEARCH_URL=http://127.0.0.1:9200
export DATABASE_URL=postgresql://callguard:callguard-dev@127.0.0.1:5434/callguard   # 프로세스 환경변수로만. .env 를 고치지 않는다
```

**2. 두 구성 — 각 3회 최저, 기록** (절대 원칙 4)
```bash
.venv/bin/python scripts/run_eval.py --runs 3 --no-ner --retriever bm25 --record          # 운영 구성
.venv/bin/python scripts/run_eval.py --runs 3 --retriever rerank-dense --record           # 모델 구성
```

**3. 생성(B-4)** — Ollama 에 kanana 가 등록돼 있을 때만(`decisions/207`)
```bash
.venv/bin/python scripts/run_eval.py --runs 3 --retriever rerank-dense --record \
  --ollama-url http://localhost:11434 --generation-model kanana-1.5-2.1b-instruct:q4_k_m
.venv/bin/python scripts/eval_generation.py        # 원출력 환각은 하네스 밖에서만 잰다(포트가 원출력을 주지 않는다)
```

**4. 오류 내성 곡선** — `scripts/measure_error_tolerance.py` (시드 3개, 두 구성 한 번에)

**5. A-5** — 하네스로는 늘 측정 불가다. `scripts/measure_a5_proficiency.py` 결과를 **그 날짜·커밋 그대로** 따로 싣는다(STT 캡 확인).

### 체크리스트
- [ ] 값마다 측정일 · 커밋 · 명령 · 표본 수 · `run_id`
- [ ] 측정 불가 목록을 **리포트 문구 그대로**: trigger · domain_routing · call_temperature · asr (· generation 원출력 환각)
- [ ] 한계 넷을 값 옆에 — C-5 「누락 0」은 오류 없는 전사 한정 · 주입기 46.9% · 쌍둥이 조항(`123`) · 컴플라이언스·콜 가드·F-2 1.0 은 상한
- [ ] **골든셋 판**: `eval_run.golden_set_version` 은 파일 이름이라 `v1-150` 으로 찍힌다 — 발표 자료에는 `v1-150.1`(`decisions/212`)로 적는다
- [ ] 모델 구성은 **운영에 떠 있지 않으면 「로컬 참고치」** 로만 싣는다(`decisions/121` §5)
