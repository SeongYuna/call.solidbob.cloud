# 00 — AI 파트 범위 · 평가 하네스 실행법

> 2026-10-13 · 류준(Claude Code 대행) · 기준 커밋 `63c4d41`(main, 10-08 PR #171 머지) · 측정 기계: 로컬 맥북(Apple Silicon, **CPU 고정**)
> 이 묶음(`docs/ai-part-review/`)은 발표 「AI 파트」 초안(12장)을 심사 질문 34개로 검토하고 보강한 기록이다.

## 1. 파일 분류

### 수정 가능 (AI 파트) — 이번 작업에서는 **한 줄도 고치지 않았다**(측정만)

| 경로 | 내용 |
|---|---|
| `ai/apps/retrieval/` | 조항 검색 — KoE5 임베딩 · ES nori BM25 · RRF(비채택) · bge 리랭커(비탑재) · 결과 캐시 · 맞장구 억제 |
| `ai/apps/pii_ner/` | 마스킹 NER 겹(koelectra) — 규칙 결과에 **합집합으로만** 더한다 |
| `ai/apps/compliance/` | 상담원 발화 규칙 24개(C-1~C-4) |
| `ai/apps/call_guard/` | 고객 폭언 어휘 사전 59항목(C-6) |
| `ai/apps/postcall_summary/` | 통화 후 요약 모델 겹(kanana) · 출력 검사 |
| `ai/apps/customer_briefing/` | 고객 브리핑 모델 겹(F-3) |
| `ai/apps/generation/` | Ollama 호출(`OllamaChat`) · 카드 생성(운영 미사용) |
| `ai/apps/evaluation/` | 평가 하네스 · 지표 · STT 오류 주입기 |
| `golden-set/` | 골든셋 — **고치지 않는다**(이번 측정은 별도 폴더) |
| `scripts/run_eval.py` · `measure_*.py` · `compare_retrievers.py` · `eval_postcall.py` | 측정 스크립트 |
| `eval/review-2026-10/` | **이번에 새로 만든 측정 스크립트·결과**(숫자 요약만, 원문 없음) |

### 읽기 전용 (다른 팀원 파트)

| 경로 | 담당 | 이번에 읽은 이유 |
|---|---|---|
| `server/apps/hub/` 라우터·DTO·저장소 · `db/schema.sql` | 장민석 | 응답에 근거 조항이 실리는가(Q29) · 원문 저장 여부(Q11) |
| `server/apps/masking/`(규칙 마스킹) · `server/apps/closure_gate/`(필요서류 규칙표) · `server/apps/postcall/`(규칙 요약) | 장민석(규칙은 류준·장민석 공동 작성) | 측정 대상의 규칙 측 — **판정 규칙이라 server 에 있다** |
| `services/call-mediator/` | 정성윤 | STT 호출 경로(Q9) · 절차 채택 하한 0.635(Q5) · C-6 단계(Q28) |
| `infra/k8s/base/` | 정성윤 | 메모리 상한(Q20) |
| `apps/call/` | 조서희 | 경고 근거 표시(Q29) |

### 경계 파일 — 고치지 않고 이름만 적는다

- `server/apps/closure_gate/domain/value_objects/closure_rule.py` — 필요서류 **규칙표**. 판정 규칙이라 server 에 있지만 내용(조항별 서류)은 AI 파트 평가의 기준이다
- `server/apps/masking/` — 규칙 마스킹(P1~P5). NER 겹(`ai/apps/pii_ner`)과 짝이다
- `services/call-mediator/src/app/call_registry.ts` 의 `PROCEDURE_SCORE_FLOOR = 0.635` — 검색 점수를 쓰는 판정 문턱
- `ai/apps/retrieval/adapter/outbound/koe5_embedder.py:76` — 동시 4부터 500 의 원인(토크나이저 공유, 10-08 정성윤 부하 시험). AI 파트 코드지만 **10-08 동결**(`decisions/138`)로 고치지 않았다 → `06_handoff_to_team.md`

## 2. 평가 하네스 — 한 명령으로 재현 (Q33)

```bash
export ELASTICSEARCH_URL=http://localhost:9200                       # nori 이미지 ES (infra/README.md)
.venv/bin/python scripts/index_knowledge_base.py --to-es --recreate   # 지식베이스 99조항 → 101청크, KoE5 임베딩 포함 · 11.6초
.venv/bin/python scripts/run_eval.py --retriever dense --runs 3       # 3회 실행 · 최저치 리포트 · 19.3초
```
- 필요한 것: `models/koe5` · `models/koelectra-ner`(합 2.5GB, `scripts/download_models.py`) · ES 9.x(nori) · Python 3.13 venv. GPU 불필요
- 2026-10-13 재현 결과: Recall@5 **0.971** · MRR **0.875**(n 102) · 마스킹 누락 **0**(n 40) · 필요서류 판정 **1.0**(n 99) — 10-01 운영 RDS run_id 1 과 **같다**(`01_number_check.md`)
- 운영 DB 에 기록: `--record`(운영 RDS 쓰기 — 이번에는 하지 않았다)
