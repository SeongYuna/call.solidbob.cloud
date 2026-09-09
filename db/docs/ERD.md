# CallGuard ERD — 브리핑 문서

> 이미지: [`ERD.png`](./ERD.png) · 소스: [`erd.dot`](./erd.dot) · DDL: [`../schema.sql`](../schema.sql)
> 생성 스크립트: [`../generate_schema_docs.py`](../generate_schema_docs.py) — 스키마를 고칠 땐 이 파일의
> `TABLES`만 고치고 재실행하면 SQL과 ERD가 항상 같은 정의를 가리킨다.

## 왜 5개가 아니라 16개인가

기획서 [3장 시스템 아키텍처](/docs/03/)는 `call`·`transcript`·`recommendation`·`closure`·
`eval_result` 5개만 이름을 언급한다. 이건 "필요한 테이블 전부"가 아니라 **아키텍처
다이어그램에 들어간 5개 큰 덩어리**다. 실제 기능 명세([2장](/docs/02/))·데이터 확보
계획([5장](/docs/05/))·평가 설계([6장](/docs/06/))를 하나씩 대조해보면, 그 5개 덩어리
안에 **1:N 관계로 반드시 쪼개야 하는 하위 데이터**가 있고, 원래 계획엔 아예 없던
개체(고객, 문서, 후속조치, 공백 리포트)도 필요하다는 게 드러난다. 아래 표가 그 대조
결과다.

> **2026-08-26 갱신**: 처음엔 17개였다. 데모 도메인을 통신 단일에서 4종(금융보험·
> 다산콜센터·쇼핑·질병관리본부)으로 바꾸면서, 통신 전용이던 `plan`(요금제) 테이블을
> 제거하고 `subscriber`를 도메인 중립적인 `customer`로 정리해 16개가 됐다. 상세는
> [아래 "2026-08-26 도메인 4종 정리"](#2026-08-26-도메인-4종-정리) 참고.

| 원래 계획 | 실제로 필요해진 이유 | 여기서 생긴 테이블 |
|---|---|---|
| `call` | D-1(상담 요약)·D-2(문의 유형)는 통화 1건당 값이 하나뿐이라 1:1 — 그대로 `call`에 병합 | `call` (요약·유형·**도메인** 컬럼 포함) |
| (없음) | F-3(반복 문의 연결)이 "동일 고객"을 판별하려면 안정적 식별자가 필요 | `customer` |
| `transcript` | 통화 하나에 발화가 여러 건(1:N) → 한 칸에 몰아넣으면 1NF 위반 | `transcript_segment` |
| (없음) | 발화 하나에 마스킹 스팬이 여러 개(1:N, C-5), 위반 탐지도 여러 개(1:N, C-1~C-4) | `masking_event`, `compliance_flag` |
| `recommendation` | 트리거 1건이 카드 여러 개를 냄(1:N, [2.1절](/docs/02/) 화면 예시도 배열) | `recommendation`(헤더) + `recommendation_card` |
| (없음) | 카드·종결 판정이 인용하는 "요금제약관 3.2조" 같은 출처가 실체 없이 문자열로만 떠다니면 참조 무결성이 없음 | `document` |
| `closure` | 그대로 두되, evidence 필드를 표 형태로 역정규화(아래 설명) | `closure` |
| (없음) | D-3(후속조치)은 통화 1건에 여러 항목(1:N). D-4(공백 리포트)는 B/C/F 세 모듈의 실패를 누적해야 함 | `follow_up_action`, `knowledge_gap` |
| `eval_result` | [6.2절 원칙 2] "여러 번 실행한 값 중 최저치 고정" — 실행(run) 단위가 없으면 어느 실행의 결과인지 구분 불가 | `eval_run`(헤더) + `eval_result`(상세) |
| (없음) | G-2([기능 명세 2.8절](/docs/02/), 조건부)의 지역 자원 목록 — 스키마만 선반영 | `resource_center` |
| (없음) | 다른 팀원 ERD 교차검증에서 발견 — 상담원 식별자 없이는 `call`의 "누가 응대했는지" 추적 불가 | `agent` |
| (없음) | 다른 팀원 ERD 교차검증에서 발견 — C-4(권장 대체 표현 제시)가 저장될 자리가 원래 없었음 | `compliance_rule` |

## 알아둘 것 — DDL 생성 순서

`schema.sql`은 `CREATE TABLE`이 나온 순서 그대로 실행돼야 하는 스크립트다. `document`를
`recommendation`/`recommendation_card`보다 뒤에 정의했더니 `recommendation_card.source_doc_id
→ document.document_id` FK가 아직 없는 테이블을 참조해서 **실제로 실행하면 에러가
나는 상태였다** — `generate_schema_docs.py`의 `TABLES` 순서를 고쳐서 해결했고,
FK 참조 테이블이 항상 먼저 나오는지 자동으로 검증하는 절차를 거쳤다. 앞으로 테이블을
추가할 때도 이 순서(참조 대상이 먼저)를 지켜야 한다.

## 팀 교차검증 기록 (2026-08-25, 팀원 ERD와 비교)

다른 팀원이 같은 기획서로 독립적으로 그린 ERD와 대조한 결과다. 서로 다른 곳에서
약점이 발견됐다 — **교차검증이 원래 하려던 일이 정확히 이거였다.**

**팀원 설계에서 가져온 것 (반영 완료)**

| 항목 | 문제였던 것 | 조치 |
|---|---|---|
| `eval_run.error_rate` | [4.2절](/docs/04/) 오류율별 성능 곡선 실험에 이 축이 없으면 어느 오류율 조건의 실행인지 구분 불가 — **명백한 누락** | 컬럼 추가 |
| `compliance_rule`(rule_code, label, default_severity, suggestion) | C-4(권장 대체 표현 제시) 요구사항이 저장될 곳이 없었음 | 테이블 추가, `compliance_flag.violation_type`을 `rule_code` FK로 교체 |
| `agent` | `transcript_segment.speaker='agent'`가 "어느 상담원인지" 알 방법이 없었음 | 테이블 추가, `call.agent_id` FK 추가 |

**이쪽 설계에만 있던 것 (팀원에게 전달할 피드백)**

| 항목 | 팀원 설계의 공백 |
|---|---|
| `subscriber`(현재 `customer`) | 고객 식별자가 아예 없어서 [F-3](/docs/02/)(반복 문의 자동 연결)을 구현할 방법이 없다 |
| `follow_up_action` / `knowledge_gap` | D-3(후속조치)·D-4(공백 리포트)가 스키마에 전혀 없다 — 통화 후 처리의 절반이 빠져있다 |
| `eval_result.passed_absolute_rule` | C-5·F-2 절대 규칙 위반 여부가 `metric_value`에 묻혀 있어, 조회할 때마다 임계값을 다시 계산해야 한다 |

**해결 안 하고 논의로 남긴 것**

F-2 근거 필드를 이 설계처럼 `closure`에 넓게 둘지, 팀원처럼 `closure_requirement`(처리
유형별 요건 정의 테이블) + `closure_evidence`(EAV, 어떤 전사 세그먼트를 근거로 충족
판단했는지 `evidence_ref`로 추적) 구조로 갈지는 **결정하지 않았다.** 팀원 방식이
① 요건 정의가 하드코딩된 컬럼이 아니라 데이터라 확장에 유리하고 ② 근거 추적성이
있다는 실질적 장점이 있어서, "컬럼이 적어서 역정규화한다"는 원래 판단보다 설득력
있는 반례다. F-2 게이트를 실제로 구현하면서 다시 정하기로 했다.

## 관계선 표기법 — 실선(식별) vs 점선(비식별)

ERD.png 왼쪽 위에 범례가 있다.

- **실선 = 식별 관계** — 자식이 부모 없이는 존재 의미가 없는 **약한 개체**다. `call`이
  없으면 `transcript_segment`·`recommendation`·`closure`·`follow_up_action`은 아무 의미가
  없고, `transcript_segment`가 없으면 `masking_event`·`compliance_flag`도 마찬가지다.
  (`transcript_segment`→`call`, `masking_event`→`transcript_segment`,
  `compliance_flag`→`transcript_segment`, `recommendation`→`call`,
  `recommendation_card`→`recommendation`, `closure`→`call`, `follow_up_action`→`call`,
  `eval_result`→`eval_run`)
- **점선 = 비식별 관계** — 부모는 **참조·분류 대상**일 뿐, 자식은 그것과 무관하게 독립적
  정체성을 가진다. `call`은 `customer`·`agent`가 누구든 통화 자체로 독립적 개체다.
  (`call`→`customer`, `call`→`agent`, `compliance_flag`→`compliance_rule`,
  `recommendation_card`→`document`, `closure`→`document`, `knowledge_gap`의 세 FK)

> **주의**: 이 스키마는 [3NF 원칙](#정규화-원칙-1nf--2nf--3nf)에 따라 **모든 테이블이
> 단일 컬럼 서로게이트 PK**를 쓴다. 그래서 교과서적 의미(부모 PK가 자식 PK의 일부로
> 들어가는 것)의 "진짜" 식별 관계는 이 스키마에 하나도 없다 — 위 실선 표시는 물리적
> PK 구조가 아니라 **개념적으로 약한 개체인지**를 보여주는 것이다. 실제로 이 관계들을
> 교과서대로 복합 PK(`transcript_segment(call_id, seq_no)` 같은)로 바꿀지는 팀 논의
> 대상이다 — 지금은 구현 단순성을 위해 서로게이트로 통일했다.

## 정규화 원칙 (1NF / 2NF / 3NF)

- **1NF (원자값, 반복 그룹 금지)**: "발화 여러 개", "카드 여러 개", "마스킹 스팬 여러 개",
  "위반 탐지 여러 개", "후속조치 여러 개", "평가 지표 여러 개" — 전부 부모 1건에 자식
  여러 행으로 쪼갰다. 배열을 JSON 컬럼 하나에 욱여넣지 않았다.
- **2NF (부분 함수 종속 제거)**: 모든 테이블이 단일 컬럼 서로게이트 PK(`*_id`)를 쓴다.
  복합 PK가 없으므로 2NF 위반(키의 일부에만 종속되는 컬럼) 자체가 구조적으로 생기지
  않는다.
- **3NF (이행적 종속 제거)**: `recommendation_card`에 문서 제목·조항 번호를 복사하지
  않고 `document_id`로 `document`를 참조한다. (통신 도메인 시절엔 `subscriber`가
  `plan_code`로 `plan`을 참조하는 예시였으나, `plan` 테이블은 2026-08-26 도메인 4종
  정리로 제거됐다 — [아래](#2026-08-26-도메인-4종-정리))

## 의도적으로 역정규화한 것 (컬럼이 너무 적은 테이블)

정규화 원칙만 기계적으로 따르면 아래 두 개는 "그럴듯하지만 너무 좁은" 테이블이 됐을
것이다. 실익이 없어서 부모 테이블에 병합했다.

1. **`closure_evidence`를 만들지 않고 `closure`에 컬럼 10개를 직접 뒀다.**
   금융보험 상품해지(3개)·금융보험 보상(2개)·쇼핑 반품(3개)·쇼핑 교환(2개), 처리
   유형(도메인×종결형)마다 확인 항목이 다르므로, 교과서적으로는
   `(closure_id, field_name, is_satisfied)` 3컬럼짜리 EAV 자식 테이블로 빼는 게 "더
   정규화된" 형태다. 하지만 필드 종류가 10개로 고정돼 있고 앞으로도 거의 안 늘어나며,
   `POLICY.md`([2.7절](/docs/02/))의 판정 로직이 "이 세 필드가 전부 true인가"를 한 행에서
   바로 확인해야 한다 — EAV로 쪼개면 매번 GROUP BY로 재조립해야 해서 F-2 게이트 코드가
   불필요하게 복잡해진다. **넓은 표 + NULL 허용**이 이 규모에서는 더 실용적이라고
   판단했다.
2. **`call_summary`를 만들지 않고 `call`에 `summary_text`·`inquiry_type`을 직접 뒀다.**
   D-1·D-2 결과는 통화당 정확히 1개(1:1 관계)라 별도 테이블로 분리해도 정규화 이득이
   없고, 조회할 때마다 JOIN만 늘어난다.

`recommendation`/`recommendation_card`, `eval_run`/`eval_result`처럼 진짜 1:N인 것들은
컬럼 수와 무관하게 그대로 분리해뒀다 — 이건 "좁아서 문제"가 아니라 구조적으로 필요한
분리다.

## 관계 한눈에 보기 (브리핑용 설명 순서)

ERD.png를 왼쪽 위 "고객"부터 시계방향으로 따라가면서 설명하면 된다.

1. **고객 → 통화**: `customer`(고객) 1명이 `call`(통화)을 여러 번 한다. `call`은
   **`domain`**(4개 데모 도메인 중 하나)을 갖고, `agent`(상담원)도 FK로 참조한다 —
   어느 상담원이 응대했는지 추적하되, 상담원별 누적 통계를 UI에 노출하지 않는 건
   애플리케이션 레벨의 책임이다([부록 B H-4·H-5 리스크](/docs/13/)).
2. **통화 → 전사/마스킹/위반**: `call` 1건에 `transcript_segment`(발화)가 여러 건 붙고,
   발화 1건에 `masking_event`(마스킹, C-5)와 `compliance_flag`(위반 탐지, C-1~C-4)가 각각
   여러 건 붙을 수 있다. `compliance_flag`는 `compliance_rule`(위반 유형 카탈로그 — 심각도,
   C-4 권장 대체 표현)을 참조한다. **여기가 대화가 실제로 기록되는 축이다.**
3. **통화 → 추천**: `call` 1건에 `recommendation`(트리거 이벤트)이 여러 번 발생하고,
   트리거 1건이 `recommendation_card`(카드)를 여러 장 낸다. 카드는 `document`(지식베이스
   조항)를 근거로 인용한다.
4. **통화 → 종결**: `call` 1건에 `closure`(종결 판정 시도)가 여러 번 있을 수 있다
   (거절되면 다시 시도하니까) — **UPDATE 없이 INSERT만 하는 append-only 테이블**이다
   ([F-4](/docs/02/) "추가 전용 이력"). `closure`도 `document`를 근거로 인용한다.
   **F-2가 적용되는 도메인(금융보험·쇼핑)의 `call`에만 행이 생긴다** — 다산콜센터·
   질병관리본부는 안내형 업무라 종결 개념 자체가 없다.
5. **통화 → 후속처리**: `call` 종료 후 `follow_up_action`(후속조치)이 여러 건 생기고,
   B/C/F 세 모듈 중 아무 데서나 실패가 나오면 `knowledge_gap`(공백 리포트)에 쌓인다 —
   그래서 `knowledge_gap`은 `call`·`transcript_segment`·`closure` 세 곳을 전부 (nullable)
   FK로 가리킨다.
6. **평가는 완전히 별도 축**: `eval_run`(하네스 실행 1회) 1건에 `eval_result`(지표별 결과)가
   여러 건 붙는다. 통화 데이터와는 직접 연결되지 않는다 — 골든셋 기반이라서다
   ([golden-set/README.md](/golden-set/) 참고).
7. **`resource_center`는 고립 노드**: G-2가 조건부라서 지금은 다른 테이블과 FK 관계가
   없다. G-2 착수가 확정되면 그때 연결한다.

## 2026-08-26 도메인 4종 정리

데모 도메인을 가상 통신사 "한별텔레콤" 단일 시나리오에서 실제 확보 데이터 4종(금융보험·
다산콜센터·쇼핑·질병관리본부)으로 한정하면서([`_project/decisions/004`](https://github.com/SeongYuna/call.solidbob.cloud)),
스키마에 남아 있던 통신 전용 내용을 정리했다. 근거·상세:
`_project/decisions/006-db-스키마-도메인-정리.md`.

| 변경 전 | 변경 후 | 이유 |
|---|---|---|
| `plan`(요금제) 테이블 | **제거** | 4개 도메인 중 "월정액 요금제" 개념이 있는 곳이 없다 |
| `subscriber`(가입자) — `plan_code` FK, `arrears_flag`(체납), `lost_report_flag`(분실신고) | **`customer`(고객)** — `customer_id`, `first_seen_at`, `status`만 남김 | 체납·분실신고 플래그는 통신 도메인의 "명의변경 제한"(TERM-5.3, 지금은 존재하지 않는 문서 ID)에만 쓰였다. 4개 도메인 어디에도 명의변경 F-2 유형이 없다 |
| `call.subscriber_id` | `call.customer_id` + **`call.domain`**(신규) | 도메인 라우팅 정보가 스키마에 아예 없었다 — [3.2절](/docs/03/)에서 지적된 공백을 이번에 메웠다 |
| `closure.closure_type`: `해지`/`명의변경`/`보상` | `상품해지`/`보상`/`반품`/`교환` | F-2가 실제로 적용되는 도메인(금융보험·쇼핑)의 처리 유형으로 교체 |
| `closure`의 evidence 7컬럼(위약금_안내 등) | evidence 10컬럼(중도해지수수료_안내 등, 도메인별 POLICY 문서와 1:1 대응) | 명의변경 관련 2컬럼(본인확인_수단·요청경위_확인) 제거, 반품·교환용 5컬럼 신설 |
| `document.document_id` 예시 `TERM-3.2` | `FIN-TERM-3.2` | 지식베이스 ID 체계가 도메인 접두어를 쓰도록 바뀜([knowledge-base/README.md](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/knowledge-base/README.md)) |

**F-3(반복 문의 연결)는 그대로 유지된다** — "동일 고객" 식별 자체는 도메인과 무관한
일반 기능이라 `customer` 테이블로 계속 지원한다. 17개 → **16개** 테이블로 줄었다(`plan`
제거, 순수 추가는 없음).

## 2026-08-27 첫 실제 적용에서 드러난 것 (설계 검증만으로는 안 잡혔다)

도커로 PostgreSQL 8.4 를 띄우고 `schema.sql` 을 **처음으로 실제 실행**했다. 두 가지가 걸렸다.

### ① 예약어 — 16개 중 2개만 생성됐다

```
ERROR 1064 (42000) at line 21: ... near 'call ('
```

`CALL` 은 PostgreSQL 예약어(스토어드 프로시저 호출)라 `CREATE TABLE call (` 에서 파싱이 멈추고
**뒤의 14개가 통째로 만들어지지 않았다.** `recommendation_card.rank` 도 예약어다(8.0 윈도우 함수).
`information_schema.KEYWORDS` 로 확인한 결과 우리 스키마에 걸리는 것은 `CALL`·`RANK` 둘이다.

→ `generate_schema_docs.py` 의 `to_sql()` 이 테이블·컬럼·FK 식별자를 **전부 백틱으로 감싸게** 했다.
예약어 목록은 버전마다 늘어나므로 개별 예외를 두지 않았다.

### ② 서로게이트 PK 에 AUTO_INCREMENT 가 없었다

```
(1364, "Field 'id' doesn't have a default value")
```

숫자 PK 11개 **전부** AUTO_INCREMENT 가 없어 INSERT 마다 ID 를 직접 넣어야 했다.
그런데 애플리케이션에 ID 를 만드는 코드가 어디에도 없다 — 설계 누락이다.

→ `Column` 에 `auto_increment` 를 추가하고 서로게이트 PK **10개**에 켰다.
**`transcript_segment.segment_id` 만 예외**다 — [7.3절](/docs/07/) 계약상 게이트웨이가 정해서
보내는 값이라(`transcript_segment.segment_id` 와 1:1) DB 가 채우면 안 된다.

> 두 결함 다 **ERD·정규화 검토로는 드러날 수 없었다.** 테이블 구성·관계·정규형은 전부 맞았고,
> 실행해봐야 나오는 종류였다. 앞으로 스키마를 고치면 `cd infra && docker compose down -v && up -d` 로
> **실제 적용까지 확인**한다.

---

## 팀 교차검증 체크리스트

- [ ] `customer_id`를 실제로 해시/난수로 만들 것인지, 실명 연동이 필요한지 (정성윤·인프라 결정)
- [ ] `closure`의 evidence 컬럼을 넓은 표로 둘지 vs 팀원 안(`closure_requirement`+`closure_evidence`
      EAV, evidence_ref 추적) — F-2 게이트 구현 시 재검토 (류준·장민석)
- [ ] 팀원 ERD에 `customer`, `follow_up_action`, `knowledge_gap`이 없다는 점
      전달하고 병합 여부 논의
- [ ] `resource_center`는 G-2 착수 확정 전까지 실제 마이그레이션에서 빼도 되는지
- [ ] `document.document_id` 네이밍(`FIN-TERM-3.2` 등)이 `knowledge-base/`의
      `<!-- id: -->` 주석과 정확히 일치하는지 (전체 조항 확인 필요)
