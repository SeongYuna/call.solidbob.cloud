# 도메인 모델 — 유비쿼터스 언어 (도메인 4종)

> ⚠ **2026-08-28 다산콜센터 단일 도메인으로 전환**(`_project/decisions/201`).
> 아래 금융보험·쇼핑·질병관리본부 서술은 **그 시점의 사실**이라 남겨 두되, 지금은 적용되지 않는다.
> 지식베이스·골든셋·코드 분기에서 전부 삭제됐다(조항 102 → 20개).
> 새 기능(A-3 동시 통번역 · C-6 콜 가드 · B 필요서류 제시)은 `decisions/201` 을 본다.

> 도메인은 **실제로 확보한 데이터**가 정한다 — AI Hub 「민원(콜센터) 질의-응답」의 4개 도메인(금융보험·다산콜센터·쇼핑·질병관리본부),
> 근거 `_project/decisions/004`. 여기에는 `knowledge-base/`·`db/schema.sql`·7.3절 계약에 **이미 정의된 것만** 옮겨 적었다.
> 새 개념을 이 문서에서 만들지 않는다. 스포크 배치는 [architecture.md](architecture.md), 강제 수단은 [harness.md](harness.md).

**골든셋 재작성 완료 (2026-08-26)**: `golden-set/v1-10.json` 10건을 4개 도메인 기준으로 다시 썼다(finance 4 · shopping 3 · dasan 2 · health 1).
`expected_doc_ids`는 `knowledge-base/`의 실제 조항 ID(도메인 접두어 포함)를 가리키며 깨진 참조는 없다. `apps/evaluation/golden_set.py`가 `domain` 필드를 파싱한다.

---

## 1. 유비쿼터스 언어

코드·문서·대화에서 같은 말을 쓴다. 왼쪽 용어를 코드 식별자로 쓸 때는 오른쪽 열을 따른다.

| 용어 | 뜻 | 코드 식별자 (DDL·7.3절 기준) |
|---|---|---|
| 도메인 | 통화가 속한 업무 영역 4종 중 하나. 검색·F-2·컴플라이언스 규칙이 도메인별로 갈린다 | `domain: "finance" \| "dasan" \| "shopping" \| "health"` — 폴더명과 같게 |
| 통화 | 상담원과 고객 사이 세션 1건 | `call`, `call_id` |
| 화자 | 고객 또는 상담원 | `speaker: "customer" \| "agent"` |
| 발화 | 화자의 문장 단위 전사. 전사 세그먼트 1건 | `utterance`, `transcript_segment`, `segment_id` |
| 발화 종료 시각 | STT가 발화를 final로 확정한 시각(ms). 트리거 채점의 기준점 | `utterance_end_ms`, `is_final` |
| 트리거 | "지금 검색하라"는 판정. 발화 종료 후 **0~1,500ms** 안이면 적절 | `TriggerDecision(fire, at_ms)`, `ON_TIME_WINDOW_MS` |
| 문서 / 조항 | 지식베이스의 검색 단위. 조항 하나 = ES 청크 하나 | `document_id` (`FIN-TERM-3.2` 형식), `doc_type` |
| 추천 카드 | 검색 결과를 상담원 화면에 띄우는 단위. **출처 없는 카드는 존재하지 않는다**(B-5) | `RecommendationCards.cards[]`, `Source(doc_id, title)`, `score` |
| 관련 문서 없음 | 근거가 부족할 때 카드 대신 반환하는 상태(B-6) | `cards` 빈 튜플 (`no_relevant_document`) |
| 컴플라이언스 위반 | 상담원 발화가 응대매뉴얼 1장을 어긴 것. 유형 C-1~C-4, 4개 도메인 공통 | `ComplianceFinding(rule_code, phrase, alternative_source)`, `compliance_flag.rule_code` |
| 대체 표현 | 위반 표현 대신 권장하는 문구. 출처는 각 도메인 응대매뉴얼 1.4 | `alternative_source: Source("<DOM>-MANUAL-1.4", …)` |
| PII 패턴 | 마스킹 대상 개인정보 유형 P1~P7. 도메인 무관 | `MaskedSpan(type, span)`, `masking_event.pattern` |
| 처리유형 | 종결하려는 업무의 종류. **도메인별로 다르다** (§4.3) | `closure_type: str` — 값은 해당 도메인 `*-POLICY-*` 가 정의 |
| 근거 필드 | 처리유형별 필수 확인 항목. 내부처리규정이 정의 | `evidence: {필드명: bool}` — 필드명은 한글 그대로 |
| 판정 | F-2 게이트 결과. 규칙이 내고 LLM은 설명만 | `verdict: "approved" \| "blocked"`, `missing[]` |
| 공백 리포트 | 검색 실패·놓친 위반·사후 문제를 같은 루프로 모은 것(D-4). F-2 미적용 도메인의 대체 검증 수단 | `knowledge_gap.module: "B" \| "C" \| "F"` |

용어 사용 제약(부록 A-1): "안전합니다", "위험도 N%", "완벽히 차단", "불변 감사 로그"는 도메인 용어가 아니다. 코드·UI·문서 어디에도 쓰지 않는다.

---

## 2. 도메인 4종과 바운디드 컨텍스트

**바운디드 컨텍스트 = 스포크**(기능 축)이고, **도메인은 그 안을 가르는 데이터 축**이다. 스포크를 도메인마다 복제하지 않는다 —
`retrieval`은 하나이고 `domain` 필드로 인덱스를 나눠 검색하며, `closure_gate`는 하나이고 도메인별 `*-POLICY-*` 규칙표를 읽는다.

| 도메인 | 폴더 / 접두어 | 가상 주체 | 실측 카테고리 (AI Hub 라벨) | F-2 |
|---|---|---|---|---|
| 금융보험 | `finance/` · `FIN-` | 한별금융 | 사고 및 보상 문의 · 상품 가입 및 해지 · 이체출금대출서비스 · 잔고 및 거래내역 | ✅ 상품해지 · 사고보상 |
| 다산콜센터 | `dasan/` · `DASAN-` | 한별시 통합민원콜센터 | 대중교통 안내 · 생활하수도 · 일반행정 · 코로나19 상담 | ❌ 안내형 — `DASAN-POLICY-1`이 미적용 사유·대체 검증(D-4) 명시 |
| 쇼핑 | `shopping/` · `SHOP-` | 한별샵 | 주문 · 결제 · 배송 · 교환 · 반품 · AS · 업무처리 | ✅ 반품 · 교환 |
| 질병관리본부 | `health/` · `HLT-` | 한별헬스콜 | 건강질병 · 약품식품 · 온라인신고 · 요양기관 현황 · 증상징후 · 진료비정보 · 기타 | ❌ 안내형 — `HLT-POLICY-1` |

| 스포크 | 도메인 의존 | 도메인 무관 |
|---|---|---|
| `masking` (C-5) | — | P1~P7 규칙 전부 |
| `compliance` (C-1~C-4) | C-4 대체 표현 출처(`<DOM>-MANUAL-1.4`) | C-1~C-3 탐지 규칙 |
| `retrieval` (B-1~B-3) | 검색 대상 인덱스(`domain` 필드), **도메인 라우팅**(B-0 — 자동 분류로 확정, `_project/decisions/007`) | 트리거 판정, RRF |
| `generation` (B-4~B-6) | 출처 표기 | 카드 형태, 폴백 |
| `closure_gate` (F-2) | 처리유형·근거 필드·규칙표 전부 (finance·shopping만) | 판정 알고리즘("전부 true일 때만 approved") |
| `evaluation` (E) | 골든셋 항목의 `domain` 필드 (`golden_set.py` 파싱 완료) | 지표 계산 |

---

## 3. 지식베이스 — 문서 ID 체계

`<DOM>-<문서>-<장>.<절>` / `<DOM>-POLICY-<처리유형>-<n>`. 각 조항은 `<!-- id: ... -->` 주석으로 ID가 박혀 있고, 청킹 스크립트가 이 주석 기준으로 자른다.
`document` 테이블(`db/schema.sql`)이 ID를 PK로 갖는 메타데이터이고 본문은 ES에만 있다. 4 도메인 × 3 문서 = 12개.

| 하위 폴더 | 문서 | ID 예 | 역할 |
|---|---|---|---|
| `terms/` | 이용약관/안내지침 | `FIN-TERM-3.2`, `DASAN-TERM-5.1` | B 검색 대상. 화면 인용 "이용약관 N.N조" |
| `manual/` | 응대 매뉴얼 | `FIN-MANUAL-3.1`, `HLT-MANUAL-1.1` | B 검색 대상 + C-4 대체 표현 출처(1.4) + F-2 근거(해당 도메인만) |
| `policy/` | 내부 처리 규정 | `FIN-POLICY-CLOSE-1`, `SHOP-POLICY-RETURN-1`, `DASAN-POLICY-1`(미적용 선언) | **F-2 게이트가 직접 참조** |

ES 는 **단일 인덱스 `callguard-kb-single` + `domain` 필터**로 간다(2026-08-27, `_project/decisions/017`).
조항이 102개뿐이라 도메인별로 나누면 인덱스당 20~34건이 되어 BM25 IDF 가 불안정해지고,
얻는 이점(도메인별 독립 재적재)은 전체 재적재가 1초도 안 걸리는 지금 있으나 마나다.
⚠ 이건 **판단이지 실측이 아니다** — 점수를 내려면 검색 구현체가 있어야 하는데 아직 없다.

**도메인이 늘면 도메인별 인덱스로 전환한다.** 볼륨 증가만으로는 바꾸지 않는다(청크가 1000배
늘어도 40MB 다). 전환 조건은 ① 도메인이 4개를 넘어 크게 늘어남(필터 선택도가 떨어져 filtered
HNSW recall 이 무너진다) ② 단일 인덱스가 샤드 2개 이상 필요(BM25 점수는 **샤드 단위**라 그때
"전역 IDF" 장점이 사라진다) ③ 전체 재색인이 오래 걸림 ④ 도메인별 보존기간·권한 분리.
전환 방법은 **alias 를 앞에 세우는 것** — 쓰기는 도메인별 인덱스, 읽기는 `callguard-kb` alias.
코드는 이미 양쪽을 지원한다: `ai/apps/retrieval/adapter/outbound/es_index.py`,
`scripts/index_knowledge_base.py --to-es [--layout per-domain]`.
⚠ 양쪽을 동시에 적재해 두면 `callguard-kb-*` 와일드카드가 같은 조항을 두 번 센다.

---

## 4. 핵심 객체와 규칙

### 4.1 PII 패턴 (C-5) — `masking`, 도메인 무관

| 패턴 | 대상 | 방식 | 절대 규칙 범위 | 담당 |
|---|---|---|---|---|
| P1 | 주민등록번호 (13자리) | 정규식 | ✅ 누락 0건 | 정성윤 |
| P2 | 카드번호 (14~16자리) | 정규식 | ✅ | 정성윤 |
| P3 | 계좌번호 (10~14자리) | 정규식 | ✅ | 정성윤 |
| P4 | 휴대전화번호 | 정규식 | ✅ | 정성윤 |
| P5 | 인증번호 (4~6자리, 문맥 조건) | 정규식 + 문맥 | ✅ | 정성윤 |
| P6 | 인명 | NER | 여유 시 — 미구현 시 N/A | 류준·장민석 |
| P7 | 상세주소 | NER | 여유 시 — 미구현 시 N/A | 류준·장민석 |

판정 순서(기능 명세 2.4절): ① 구분자·공백 제거 후 연속 숫자열 판정 → ② 한글 수사→숫자(보조) → ③ 정규식 + NER → ④ 마스킹.
우선순위: **누락 0건 > 과잉 마스킹 억제**. 금융 도메인(카드·계좌)에서 P2·P3 빈도가 특히 높다.

### 4.2 컴플라이언스 위반 유형 (C-1~C-4) — `compliance`, 규칙은 공통

| 유형 | 정의 | 매뉴얼 근거 (각 도메인 동일 절) |
|---|---|---|
| C-1 | 확정적 보장 표현 ("무조건", "100% 환불") | `<DOM>-MANUAL-1.1` |
| C-2 | 불필요한 개인정보 구두 요구 | `<DOM>-MANUAL-1.2` |
| C-3 | 필수 안내 누락 (해지 시 수수료 고지 등) | `<DOM>-MANUAL-1.3` |
| C-4 | 권장 대체 표현 제시 | `<DOM>-MANUAL-1.4` |

지표는 재현율 ≥ 0.90 우선, 정밀도 ≥ 0.60.

### 4.3 종결 판정 (F-2) — `closure_gate`, 도메인별 규칙표

처리유형별 근거 필드는 `*-POLICY-*-1`이, 판정 규칙은 `*-POLICY-*-2`가 정의한다.

| 도메인 | 처리유형 | 필수 근거 필드 | 규칙 출처 |
|---|---|---|---|
| 금융보험 | 상품해지 | `중도해지수수료_안내` · `약정혜택소멸_안내` · `고객확인_기록` | `FIN-POLICY-CLOSE-1/-2` |
| 금융보험 | 사고보상 | `사고경위_확인` · `귀책여부_확인` | `FIN-POLICY-COMPENSATE-1/-2` |
| 쇼핑 | 반품 | `환불금액_안내` · `환불기간_안내` · `상품상태_확인` | `SHOP-POLICY-RETURN-1/-2` |
| 쇼핑 | 교환 | `교환가능_확인` · `재고_확인` | `SHOP-POLICY-EXCHANGE-1/-2` |
| 다산 · 질병관리본부 | (없음) | F-2 미적용 — D-4 공백 리포트로 대체 검증 | `DASAN-POLICY-1`, `HLT-POLICY-1` |

규칙: 해당 유형의 필드가 **전부** `true`일 때만 `approved`. 하나라도 `false`면 `blocked` + `missing`에 `false`인 필드명. 평균·부분 점수 없음.
이 규칙은 `closure_gate/domain/services`가 소유한다 — 허브 DTO(`ClosureVerdict`)는 나르기만 한다.
"팀이 만든 규정 안에서의 100%"임을 명시한다(순환 검증 — 규정 작성 / 게이트 구현 / 골든셋 라벨링 담당 분리는 4인 체제에서 재배정 필요).

`db/schema.sql`의 `closure` 테이블은 위 표 기준으로 정리됐다 (2026-08-26, `_project/decisions/006`) — `closure_type ENUM('상품해지','보상','반품','교환')`, evidence 컬럼도 금융보험·쇼핑 요건으로 교체. 통신 가정이던 `plan` 테이블은 삭제, `subscriber`는 `customer`로 정리(17→16개 테이블).

### 4.4 인터페이스 계약 3종 — `hub` DTO

7.3절 v2가 정본(`_project/decisions/003`). 허브 `app/dtos/`가 소유한다. **`domain` 필드는 아직 계약에 없다** — 도메인 라우팅 설계와 함께 v3로 추가해야 한다(미결).

| DTO | 핵심 필드 | 생산자 → 소비자 |
|---|---|---|
| `TranscriptEvent` | `call_id`, `segment_id`, `speaker`, `text`(마스킹 후), `masked[]`, `is_final`, `utterance_end_ms` | 게이트웨이 → `hub.transcript_ingest` → `masking` → 대시보드·DB |
| `RecommendationCards` | `call_id`, `trigger_at_ms`, `cards[]{title, summary, source{doc_id, title}, score}`, `internal_latency_ms`, `e2e_latency_ms` | `retrieval`→`generation` → 허브 → 대시보드 |
| `ClosureVerdict` | `call_id`, `closure_type`, `reason`, `evidence{…}`, `verdict`, `missing[]`, `source{doc_id, title}` | 대시보드 → 허브 → `closure_gate` → 대시보드·DB |

---

## 5. 골든셋 스키마 ↔ 코드

`apps/evaluation/golden_set.py`가 골든셋을 파싱한다. 재작성(2026-08-26)으로 항목마다 `domain`이 붙었고 `expected_doc_ids`는 도메인 접두어가 포함된 실제 ID(`FIN-TERM-3.2` 등)를 가리킨다. 로더의 `domain` 필드 파싱도 반영됐다.

규모는 1주차 10건 → 2주차 50건 → 3주차 150건(공식 기준선)으로 늘린다(5.3절). 현재 10건은 표본이 작으므로 여기서 나온 값은 **잠정치**로만 쓴다.

| 골든셋 필드 | `golden_set.py` | 도메인 배치 예정 |
|---|---|---|
| `compliance_violation` | `ComplianceViolation` | `compliance/domain/value_objects/` |
| `pii_patterns[]` | `PiiPattern` | `masking/domain/value_objects/` |
| `f2_case` | `F2Case` | `closure_gate/domain/` |
| `expected_doc_ids`, `distractor_doc_ids`, `utterance_end_ms` | `GoldenItem` | `retrieval/domain/` |

---

## 6. 한계 (지우지 않는다)

- ~~골든셋 v1-10은 **무효**(구 도메인). 4개 도메인 비율 팀 컨펌 후 재작성.~~ *(해소됨, 2026-08-26)* — 4개 도메인 기준 10건으로 재작성, 팀 리뷰 완료. 다만 **10건은 표본이 작아** 여기서 나오는 값은 잠정치다.
- ~~도메인 라우팅(통화 → 4개 중 하나)은 설계 전.~~ *(설계 확정, 2026-08-26 — `_project/decisions/007`)* — 자동 분류(B-0)로 정했고 라우팅 정확도를 지표로 편입했다(목표 ≥0.95, 6.1절). **실제 분류기는 아직 없다** — 골든셋 50건 확보 후 착수하므로 그때까지 B-0은 "측정 불가 — 모듈 미구현".
- ~~`db/schema.sql`은 통신 가정(`subscriber`/`plan`, `closure` 컬럼) — 재검토 대기.~~ *(해소됨, 2026-08-26 — `_project/decisions/006`)* — 다만 **실제 PostgreSQL 마이그레이션 적용은 아직 안 했다**(설계 문서 단계).
- P6·P7, F-1·G-1 탐지 성능은 측정 불가 범위(5.5절).
