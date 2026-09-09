---
layout: doc
title: 데이터베이스 ERD
permalink: /docs/16/
---

{% include pivot-201.html note="**이 페이지에서 바뀐 것**: `call.domain` 컬럼은 값이 `dasan` 하나뿐이라 사실상 상수가 됐다. **컬럼을 지우지는 않았다** — 되돌릴 때 마이그레이션이 더 비싸다. 새 기능(A-3 언어 코드 · C-6 폭언 · D 감정)에 필요한 스키마는 아직 설계되지 않았다." %}

[3장 시스템 아키텍처](/docs/03/)는 `call`·`transcript`·`recommendation`·`closure`·
`eval_result` 5개 테이블만 언급한다. 이건 아키텍처 다이어그램에 들어간 5개 큰 덩어리일
뿐, 기능 명세를 하나씩 대조해보면 1:N 관계로 쪼개야 할 하위 데이터와 원래 계획엔 없던
개체(고객·문서·후속조치·공백 리포트)가 더 필요하다. 그래서 실제로는 **16개 테이블**로
설계했다.

> 저장소 원본: `db/schema.sql`(DDL), `db/docs/erd.dot`(다이어그램 소스),
> `db/generate_schema_docs.py`(스키마 정의 — 여기만 고치면 SQL·ERD가 같이 갱신됨),
> `db/docs/ERD.md`(이 페이지의 상세 버전 + 팀 교차검증 체크리스트).

> **✅ 도메인 4종 정리 완료 (2026-08-26)**: 데모 도메인을 통신 단일에서 4종(금융보험·
> 다산콜센터·쇼핑·질병관리본부)으로 바꾸면서([`_project/decisions/004`](https://github.com/SeongYuna/call.solidbob.cloud)),
> 통신 전용이던 `plan`(요금제) 테이블을 제거하고 `subscriber`를 `customer`로 정리했다.
> `call`에 `domain` 컬럼을 추가해 도메인 라우팅 정보를 스키마에 명시했고, `closure`의
> `closure_type`·evidence 컬럼을 실제 F-2 적용 도메인(금융보험·쇼핑)의 처리 유형으로
> 교체했다. 17개 → 16개 테이블. 상세: `_project/decisions/006-db-스키마-도메인-정리.md`,
> [`db/docs/ERD.md`](https://github.com/SeongYuna/call.solidbob.cloud/blob/main/db/docs/ERD.md).

## ERD

<img src="/assets/erd/ERD.png" alt="CallGuard ERD" style="max-width:100%; border:1px solid #e5e7eb; border-radius:6px;">

## 왜 5개가 아니라 16개인가

| 원래 계획 | 실제로 필요해진 이유 | 여기서 생긴 테이블 |
|---|---|---|
| `call` | D-1(상담 요약)·D-2(문의 유형)는 통화당 값이 하나(1:1) — `call`에 병합 | `call` (요약·유형·**도메인** 컬럼 포함) |
| (없음) | F-3(반복 문의 연결)이 "동일 고객" 식별자 필요 | `customer` |
| `transcript` | 통화 하나에 발화가 여러 건(1:N) — 한 칸에 몰아넣으면 1NF 위반 | `transcript_segment` |
| (없음) | 발화 하나에 마스킹 스팬 여러 개(C-5), 위반 탐지 여러 개(C-1~C-4) | `masking_event`, `compliance_flag` |
| `recommendation` | 트리거 1건이 카드 여러 개를 냄([2.1절](/docs/02/) 화면도 배열) | `recommendation` + `recommendation_card` |
| (없음) | 카드·종결 판정이 인용하는 문서 출처가 참조 무결성 없이 문자열로만 떠다니면 안 됨 | `document` |
| `closure` | 그대로 두되 evidence 필드를 표로 역정규화(아래). **F-2 적용 도메인(금융보험·쇼핑)에만 행이 생김** | `closure` |
| (없음) | D-3(후속조치, 1:N), D-4(공백 리포트 — B/C/F 세 모듈 실패 누적) | `follow_up_action`, `knowledge_gap` |
| `eval_result` | [6.2절](/docs/06/) "여러 번 실행한 값 중 최저치 고정" — 실행 단위 없인 구분 불가 | `eval_run` + `eval_result` |
| (없음) | G-2([2.8절](/docs/02/), 조건부) 지역 자원 목록 — 스키마만 선반영 | `resource_center` |
| (없음) | 팀원 ERD 교차검증 — 상담원 식별자 필요 | `agent` |
| (없음) | 팀원 ERD 교차검증 — C-4(권장 대체 표현)가 저장될 곳이 없었음 | `compliance_rule` |

## 팀 교차검증 기록 (2026-08-25)

다른 팀원이 같은 기획서로 독립적으로 그린 ERD와 대조했다. 서로 다른 곳에서 약점이
나왔다.

**팀원 설계에서 가져온 것**: `eval_run.error_rate`([4.2절](/docs/04/) 오류율별 성능곡선에
필수인데 빠져 있었음), `compliance_rule`(C-4 권장 대체 표현이 저장될 곳이 없었음),
`agent`(상담원 식별자 없음) — 셋 다 명백한 누락이라 바로 반영했다.

**팀원에게 전달한 피드백**: 팀원 설계엔 고객 식별자(현재 `customer`)가 없어
[F-3](/docs/02/)(반복 문의 연결)을 구현할 수 없고, `follow_up_action`·`knowledge_gap`
(D-3·D-4)이 통째로 빠져 있으며, `eval_result`에 절대 규칙 위반 플래그가 없다.

**논의로 남긴 것**: F-2 근거를 `closure`에 넓게 둘지, 팀원처럼 `closure_requirement`
(요건 정의 테이블) + `closure_evidence`(EAV, 근거 세그먼트 추적) 구조로 갈지는 결정하지
않았다. 팀원 방식이 확장성·추적성 면에서 실질적 장점이 있어 F-2 구현 시 재검토한다.
상세 비교는 [`db/docs/ERD.md`](https://github.com/SeongYuna/call.solidbob.cloud) 참고.

## 관계선 표기법 — 실선(식별) vs 점선(비식별)

ERD.png 왼쪽 위 범례 참고. **실선**은 자식이 부모 없이는 존재 의미가 없는 약한 개체
관계(`call`→`transcript_segment`, `transcript_segment`→`masking_event` 등), **점선**은
부모가 참조·분류 대상일 뿐 자식이 독립적 정체성을 가지는 관계(`call`→`customer`,
`recommendation_card`→`document` 등)다.

> 이 스키마는 모든 테이블이 서로게이트 PK를 쓰므로, 교과서적 의미의 "진짜" 식별 관계
> (부모 PK가 자식 PK에 포함)는 하나도 없다. 실선은 물리적 PK 구조가 아니라 **개념적으로
> 약한 개체인지**를 표시한다. 상세 근거는 `db/docs/ERD.md` 참고.

## 정규화 (1NF/2NF/3NF)

- **1NF**: 발화·카드·마스킹 스팬·위반 탐지·후속조치·평가 지표 — "여러 개 나올 수 있는 것"은
  전부 부모 1건에 자식 여러 행으로 쪼갰다. 배열을 JSON 컬럼 하나에 몰아넣지 않았다.
- **2NF**: 모든 테이블이 단일 컬럼 서로게이트 PK를 쓴다. 복합 PK가 없어서 부분 함수
  종속(2NF 위반의 원인) 자체가 구조적으로 생기지 않는다.
- **3NF**: `recommendation_card`는 문서 제목을 복사하지 않고 `document_id`로 `document`를
  참조한다. (통신 도메인 시절엔 `subscriber`가 `plan_code`로 `plan`을 참조하는 예시였으나,
  `plan` 테이블은 2026-08-26 도메인 4종 정리로 제거됐다)

## 의도적으로 역정규화한 것

컬럼이 3~4개뿐인 "너무 좁은" 테이블은 두 곳에서 부모에 병합했다.

1. **`closure_evidence`를 안 만들고 `closure`에 evidence 컬럼 10개를 직접 뒀다.** 처리
   유형(금융보험 상품해지/보상, 쇼핑 반품/교환)마다 확인 항목이 달라 교과서적으로는
   `(closure_id, field_name, is_satisfied)` 3컬럼 EAV 테이블이 "더 정규화된" 형태지만,
   필드가 10개로 고정돼 있고 [F-2 게이트](/docs/02/)가 "이 필드들이 전부 true인가"를
   한 행에서 바로 봐야 한다. EAV로 쪼개면 매번 재조립해야 해서 실용성이 떨어진다.
2. **`call_summary`를 안 만들고 `call`에 `summary_text`·`inquiry_type`을 직접 뒀다.**
   D-1·D-2 결과는 통화당 정확히 1개(1:1)라 분리해도 정규화 이득이 없다.

`recommendation`/`recommendation_card`, `eval_run`/`eval_result`처럼 진짜 1:N인 것들은
컬럼 수와 무관하게 그대로 분리했다 — 좁아서가 아니라 구조적으로 필요한 분리다.

## 관계 브리핑 순서

1. **고객 → 통화**: `customer` 1명이 `call`을 여러 번. `call`은 **`domain`**(4개 데모
   도메인 중 하나)을 갖고, `agent`(상담원)도 FK로 참조 — 상담원별 통계 노출은 하지
   않는 걸 전제로 함([부록 B](/docs/13/)).
2. **통화 → 전사/마스킹/위반**: `call` 1건에 `transcript_segment` 여러 건, 발화 1건에
   `masking_event`(C-5)·`compliance_flag`(C-1~C-4) 각각 여러 건. `compliance_flag`는
   `compliance_rule`(위반유형 카탈로그, C-4 권장 대체 표현 포함)을 참조.
3. **통화 → 추천**: `call` 1건에 `recommendation` 여러 번, 트리거 1건에 `recommendation_card`
   여러 장. 카드는 `document`를 근거로 인용.
4. **통화 → 종결**: `call` 1건에 `closure` 시도가 여러 번(거절되면 재시도) —
   **UPDATE 없이 INSERT만 하는 append-only** ([F-4](/docs/02/)). `document` 근거 인용도
   동일. **F-2 적용 도메인(금융보험·쇼핑)의 통화에만 행이 생긴다** — 다산콜센터·
   질병관리본부는 안내형 업무라 종결 개념이 없다.
5. **통화 → 후속처리**: 종료 후 `follow_up_action` 여러 건, 실패 시 `knowledge_gap`에
   누적 — `call`·`transcript_segment`·`closure` 세 곳을 전부 (nullable) FK로 가리킴.
6. **평가는 별도 축**: `eval_run` 1건에 `eval_result` 여러 건. 통화 데이터와 직접 연결
   안 됨 — 골든셋 기반([golden-set/README.md](https://github.com/SeongYuna/call.solidbob.cloud)
   참고).
7. **`resource_center`는 고립 노드**: G-2 조건부라 지금은 FK 관계 없음.

## 팀 교차검증 체크리스트

- [ ] `customer_id`를 해시/난수로 할지, 실명 연동이 필요한지 (정성윤)
- [ ] `closure`의 evidence 10컬럼 vs 팀원 안(EAV+정의테이블) — F-2 구현 시 재검토 (류준·장민석)
- [ ] 팀원 ERD에 없는 `customer`·`follow_up_action`·`knowledge_gap` 병합 논의
- [ ] `resource_center`를 G-2 착수 확정 전까지 실제 마이그레이션에서 뺄지
- [ ] `document.document_id`(`FIN-TERM-3.2` 등)가 `knowledge-base/`의 `<!-- id: -->` 주석과
      전부 일치하는지

---

[← 개발목차로 돌아가기](/toc/)
