---
title: "최종 측정 — 발표·제출에 쓸 수치를 한 번에 고정한다"
assignee: "류준"
role: "ai"
status: "done"
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

- [x] **동결 커밋**을 정하고 그 커밋에서 `--runs 3 --record` — 운영 구성과 모델 구성 **둘 다**
- [x] 값마다 측정일 · 커밋 · 명령 · 표본 수(§5). `run_id` 가 남는다
- [x] 「측정 불가」 목록을 함께 낸다 — ~~F-2(채점 케이스 0건, `decisions/118`)~~ **F-2 는 빼라 — 이제 잰다**(`f2_case` 99건, `decisions/125` 가 `118` 을 되돌렸다. run_id 8·9 에서 `accuracy 1.0 · n 99`) · trigger(의도적 미배선) · A-5(데이터 미확보 시) · D-5 통화 온도(`NO_SAMPLES`) · 생성(포트 미장착) · **D-2 유형**(동결 커밋이 `decisions/323` 뒤라면 숫자가 나온다 — 나오면 「5종 중 3종 표본」 단서를 붙인다)
- [x] 한계 넷을 값 옆에 붙인다 — C-5 「누락 0」은 **오류 없는 전사 한정** · 주입기가 실측 오류의 46.9% 를 못 흉내 낸다(곡선이 낙관 쪽) · 쌍둥이 조항 2건(`123`) · 컴플라이언스·콜 가드 1.0 은 **자기충족 상한**
- [x] [발표 자료](/backlog/w8-presentation/)·[최종 문서](/backlog/w8-final-docs/)가 이 값만 쓴다

---

## 동결 때 그대로 돌릴 절차 (2026-09-22 준비 — **실행은 안 했다**)

> 09-22 에 두 구성을 이미 재 봤다 — **판정용 정본은 `run_id 8`(운영 실구성: 규칙+NER · KoE5 dense, **리랭커 없음**)·`run_id 9`(BM25 기준선)**,
> 커밋 `5b2b4c4` · 골든셋 `v1-150.2`(295건) · 내보내기 `data/processed/eval-export/2026-09-22-run-8-9.json`
> ([w6-model-config-remeasure](/backlog/w6-model-config-remeasure/)). 그 앞의 run_id 1·2(`121157e`)·3·4(`e966b62`)·5·6 은 옛 판이다.
> **run 8·9 도 동결 전 값이다** — 이 티켓의 값으로 쓰지 않는다. 동결 커밋에서 아래를 **한 번에** 다시 돌린다.
>
> ⚠ **이름을 가른다** — 「운영 구성」이라는 말을 쓰지 않는다. **BM25 기준선**(규칙 + BM25·nori, NER 끔)과
> **운영 실구성**(규칙+NER + KoE5 dense, 리랭커 없음, B-6 문턱 꺼짐 — 09-22 12:10 부터 운영, `decisions/124`) 둘로 부른다.

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
.venv/bin/python scripts/run_eval.py --runs 3 --no-ner --retriever bm25 --record          # BM25 기준선
.venv/bin/python scripts/run_eval.py --runs 3 --retriever dense --record                  # 운영 실구성 — ⚠ rerank-dense 가 아니다
```

> ⚠ **`--retriever rerank-dense` 를 쓰지 않는다.** 운영에는 **리랭커가 없다**(`decisions/124` — NER·KoE5 만 운영 노드 CPU 에 싣는다).
> 리랭커를 켠 값은 운영에 없는 구성의 값이라 「로컬 참고치」로만 실을 수 있다. 판정·발표에 쓰는 열은 `--retriever dense` 다.

**3. 생성(B-4)** — Ollama 에 kanana 가 등록돼 있을 때만(`decisions/207`)
```bash
.venv/bin/python scripts/run_eval.py --runs 3 --retriever dense --record \
  --ollama-url http://localhost:11434 --generation-model kanana-1.5-2.1b-instruct:q4_k_m
.venv/bin/python scripts/eval_generation.py        # 원출력 환각은 하네스 밖에서만 잰다(포트가 원출력을 주지 않는다)
```

**4. 오류 내성 곡선** — `scripts/measure_error_tolerance.py` (시드 3개, 두 구성 한 번에)

**5. A-5** — 하네스로는 늘 측정 불가다. `scripts/measure_a5_proficiency.py` 결과를 **그 날짜·커밋 그대로** 따로 싣는다(STT 캡 확인).

### 체크리스트
- [x] 값마다 측정일 · 커밋 · 명령 · 표본 수 · `run_id`
- [x] **명령줄을 리포트에 그대로 남긴다** — `--retriever` 와 `--no-ner` 가 어느 열인지는 `eval_run` 만 봐서는 알 수 없다
- [x] **`eval_run.components` 가 두 구성에서 다르게 찍혔는지 확인한다** — `db/schema.sql` `components` + `run_eval.py` `components_label()`(커밋 `759b3d4`). ⚠ **run 8·9 는 그보다 11분 앞선 커밋이라 NULL 이다** — 동결 run 에서는 채워져야 한다
- [x] **ES 가 안 떠 있으면 중단한다** — 검색 항목이 전부 「측정 불가」로 찍힌 run 을 `--record` 로 DB 에 남기지 않는다(지울 수 없다)
- [x] 측정 불가 목록을 **리포트 문구 그대로**: trigger · domain_routing · call_temperature · asr (· generation 원출력 환각)
- [x] 한계 넷을 값 옆에 — C-5 「누락 0」은 오류 없는 전사 한정 · 주입기 46.9% · 쌍둥이 조항(`123`) · 컴플라이언스·콜 가드·F-2 1.0 은 상한
- [x] **골든셋 판**: 발표 자료에는 **`v1-150.2`**(295건 — B 102 · B-6 23 · F-2 99 · C-5 항목 36/패턴 40 · C-6 15)로 적는다.
      ⚠ **`eval_run.golden_set_version` 은 파일 이름에서 와서 `v1-150` 으로만 찍힌다** — 판은 커밋으로 가른다(`decisions/212`·`217`)
- [x] **오류 내성 곡선도 동결 커밋에서 다시 잰다** — 지금 있는 곡선은 `e966b62`·`v1-150.1`·n 96 이라 본 표(n 102)와 세대가 다르다
- [x] 리랭커 값은 **운영에 없는 구성**이므로 싣는다면 「로컬 참고치」로만(`decisions/121` §5 · `124`)

## 2026-10-01 — 동결 커밋 기준 (정성윤)

동결 커밋은 발표 전 마지막 main 머지 커밋이다(`decisions/138`). 발표 전에 못 돌리면 run 8·9 를 그대로 인용한다 — 새 측정을 급히 만들어 네 조건을 못 채우는 쪽이 더 나쁘다. 곡선 재측정도 이 티켓에서 같이.

## 2026-10-01 — done — 발표 정본은 run 8·9 (정성윤, `decisions/138`)

발표 전에 동결 커밋에서 다시 돌리지 않는다. 류준 로컬 ES·기록 DB 가 이 머신에 없고, 급히 만든 새 측정은 §5 네 조건을 못 채운다. **인용 정본**: run_id 8·9 · 2026-09-22 · 커밋 `5b2b4c4` · 골든셋 `v1-150.2` 295건 · 3회 최저 · `--record`(⚠ 로컬 기록 DB). 곡선은 `e966b62`·n 96 을 「한 세대 앞 판」으로 밝히고 인용. 측정 불가 목록·한계 넷·문구 셋은 판정문(`_logs/2026-09-30-02`)과 `138` 에 있다.
발표 뒤 시간이 있으면 같은 명령으로 동결 커밋에서 한 번 더 돌리고 run_id 를 138 에 적는다 — 그건 이 티켓이 아니라 새 티켓이다.
