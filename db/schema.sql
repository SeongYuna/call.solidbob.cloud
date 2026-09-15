-- CallGuard PostgreSQL 스키마 — db/generate_schema_docs.py에서 자동 생성.
-- 이 파일을 직접 고치지 말고 generate_schema_docs.py의 TABLES를 고친 뒤 다시 생성할 것.

-- 고객 — F-3(반복 문의 연결)이 참조하는 안정적 식별자. 2026-08-26 도메인 4종 확정 이전엔 통신 전용 `subscriber`(+`plan`/체납·분실신고 플래그)였으나, 그 필드들은 폐기된 명의변경 처리유형(TERM-5.3, 지금은 존재하지 않는 문서 ID)에만 쓰였고 4개 도메인(금융보험·다산콜센터·쇼핑·질병관리본부) 중 어디에도 대응하는 개념이 없어 제거했다 (`_project/decisions/006-db-스키마-도메인-정리.md`)
CREATE TABLE "customer" (
    "customer_id" VARCHAR(64) NOT NULL,
    "first_seen_at" TIMESTAMPTZ NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    PRIMARY KEY ("customer_id")
);
COMMENT ON COLUMN "customer"."customer_id" IS '**전화번호의 HMAC-SHA256(hex 64자)** — `blacklist_request.customer_ref` 와 같은 체계다. 평문 번호·실명을 저장하지 않는다. 통화 시작(`POST /hub/calls` 의 caller_phone)에서 만든다 (`decisions/304`, 2026-09-14 VARCHAR(40)→(64) — 40 자로는 HMAC 이 안 들어갔다)';

-- 상담원 마스터 — 부록B H-4/H-5 리스크(감시 도구화)는 UI·집계 노출 문제이지 call.agent_id 존재 자체의 문제가 아니므로 최소 식별자만 둔다
CREATE TABLE "agent" (
    "agent_id" VARCHAR(20) NOT NULL,
    "display_name" VARCHAR(30) NOT NULL,
    "team" VARCHAR(30) NULL,
    "role" VARCHAR(30) NOT NULL,
    "hired_on" DATE NULL,
    PRIMARY KEY ("agent_id"),
    CHECK ("role" IN ('agent','admin'))
);
COMMENT ON COLUMN "agent"."role" IS 'J-4 는 관리자만 승인할 수 있는데(`decisions/204`) DB 가 그것을 식별할 방법이 없었다 — 요청 페이로드의 문자열에만 의존했다(`decisions/205` ⑦)';
COMMENT ON COLUMN "agent"."hired_on" IS 'J-5 베테랑 판정(기본 3년 이상, `_project/decisions/204`). 근속 「연수」가 아니라 **입사일**을 둔다 — 연수를 저장하면 매년 갱신해야 하고, 갱신을 잊으면 조용히 틀린 배정이 된다';

-- 통화 — D-1·D-2 결과(summary_text·inquiry_type)를 1:1이라 병합(역정규화)
CREATE TABLE "call" (
    "call_id" VARCHAR(40) NOT NULL,
    "domain" VARCHAR(30) NOT NULL,
    "customer_id" VARCHAR(64) NULL,
    "agent_id" VARCHAR(20) NULL,
    "started_at" TIMESTAMPTZ NOT NULL,
    "ended_at" TIMESTAMPTZ NULL,
    "channel_count" SMALLINT NOT NULL,
    "summary_confirmed_at" TIMESTAMPTZ NULL,
    "stt_engine" VARCHAR(30) NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    "summary_text" TEXT NULL,
    "inquiry_type" VARCHAR(30) NULL,
    PRIMARY KEY ("call_id"),
    CHECK ("domain" IN ('finance','dasan','shopping','health')),
    FOREIGN KEY ("customer_id") REFERENCES "customer"("customer_id"),
    FOREIGN KEY ("agent_id") REFERENCES "agent"("agent_id")
);
COMMENT ON COLUMN "call"."domain" IS '4개 데모 도메인 — 검색·F-2 라우팅 기준([1.4절](/docs/01/))';
COMMENT ON COLUMN "call"."customer_id" IS '게이트웨이가 발신 번호를 넘긴 통화만 채워진다(`decisions/304`). 재상담 이력·블랙리스트 요청의 연결 고리';
COMMENT ON COLUMN "call"."channel_count" IS 'V1 확인: 전부 1(모노)';
COMMENT ON COLUMN "call"."summary_confirmed_at" IS 'D-1~D-3 — **NULL 이면 초안이다**(`decisions/205` ⑧). `CallSummaryDraft.confirmed` 를 담을 자리가 없어서, 모델이 만든 초안과 상담원이 확정한 것을 DB 가 구분하지 못했다 — 부록 A-1 이 금지한 「모델이 정한 것을 확정한 것처럼」이 저장 계층에서 일어난다';
COMMENT ON COLUMN "call"."summary_text" IS 'D-1, 통화 후 생성';
COMMENT ON COLUMN "call"."inquiry_type" IS 'D-2, 통화 후 생성';

-- 전사 세그먼트 — 발화 1건 = 1행 (1NF: 통화 전체를 한 칸에 몰아넣지 않음). ⚠ **PK 는 `(call_id, segment_id)` 복합키다**(2026-09-09, `_project/decisions/205`) — `segment_id` 는 게이트웨이가 **통화 안에서** 매기는 순번이라(§7.3) 전역 유일하지 않다. 단독 PK 로 두었을 때 두 번째 통화의 1번 발화가 첫 통화의 1번 행을 덮어쓰는 것을 실제로 재현했다
CREATE TABLE "transcript_segment" (
    "segment_id" BIGINT NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "speaker" VARCHAR(30) NOT NULL,
    "text" TEXT NOT NULL,
    "is_final" BOOLEAN NOT NULL,
    "utterance_end_ms" INT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("call_id", "segment_id"),
    CHECK ("speaker" IN ('customer','agent')),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id")
);
COMMENT ON COLUMN "transcript_segment"."segment_id" IS '통화 안에서의 순번. **통화를 넘어 유일하지 않다** — call_id 와 함께 써야 한다';
COMMENT ON COLUMN "transcript_segment"."text" IS '마스킹 완료본만 — 원문 저장 금지 (SEC-1)';

-- C-5 마스킹 이벤트 — 세그먼트당 여러 개 가능해 분리 (1NF)
CREATE TABLE "masking_event" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "segment_id" BIGINT NOT NULL,
    "pattern" VARCHAR(4) NOT NULL,
    "span_start" INT NOT NULL,
    "span_end" INT NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("call_id", "segment_id") REFERENCES "transcript_segment"("call_id", "segment_id")
);
COMMENT ON COLUMN "masking_event"."call_id" IS 'transcript_segment 복합 FK 의 짝(`decisions/205`)';
COMMENT ON COLUMN "masking_event"."pattern" IS 'P1~P7';
CREATE INDEX "masking_event_idx0" ON "masking_event" ("call_id", "segment_id");

-- C-1~C-4 위반 유형 카탈로그 — 팀 교차검증(팀원 ERD)에서 반영: suggestion이 C-4(권장 대체 표현 제시) 요구사항의 실제 저장 위치
CREATE TABLE "compliance_rule" (
    "rule_code" VARCHAR(4) NOT NULL,
    "label" VARCHAR(50) NOT NULL,
    "default_severity" VARCHAR(30) NOT NULL,
    "suggestion" VARCHAR(200) NULL,
    PRIMARY KEY ("rule_code"),
    CHECK ("default_severity" IN ('high','medium','low'))
);
COMMENT ON COLUMN "compliance_rule"."rule_code" IS 'C-1~C-4';
COMMENT ON COLUMN "compliance_rule"."suggestion" IS '도메인별 MANUAL 문서의 1.4절(권장 대체 표현), 예: FIN-MANUAL-1.4';

-- C-1~C-4 위반 탐지 — D-4(놓친 위반 표현 누적)의 원천 데이터. ⚠ **C-6(고객 폭언)을 여기 담지 않는다** — `rule_code` 가 `compliance_rule`(C-1~C-4)에 FK 로 묶여 있고, 무엇보다 **화자가 반대라** 섞으면 D-4 재학습 데이터가 오염된다. C-6 은 `call_guard_flag` 다
CREATE TABLE "compliance_flag" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "segment_id" BIGINT NOT NULL,
    "rule_code" VARCHAR(4) NOT NULL,
    "phrase" VARCHAR(200) NOT NULL,
    "confidence" REAL NULL,
    "detected_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("rule_code") REFERENCES "compliance_rule"("rule_code"),
    FOREIGN KEY ("call_id", "segment_id") REFERENCES "transcript_segment"("call_id", "segment_id")
);
COMMENT ON COLUMN "compliance_flag"."call_id" IS 'transcript_segment 복합 FK 의 짝(`decisions/205`)';

-- 지식베이스 문서 조항 — 실제 본문은 Elasticsearch, 여기는 참조 무결성·관리용 메타데이터. recommendation_card·closure가 참조하므로 그 앞에 정의해야 FK 생성 순서가 맞는다
CREATE TABLE "document" (
    "document_id" VARCHAR(30) NOT NULL,
    "doc_type" VARCHAR(30) NOT NULL,
    "chapter" VARCHAR(20) NULL,
    "clause" VARCHAR(20) NULL,
    "title" VARCHAR(100) NOT NULL,
    "source_path" VARCHAR(200) NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("document_id"),
    CHECK ("doc_type" IN ('TERM','MANUAL','POLICY'))
);
COMMENT ON COLUMN "document"."document_id" IS '도메인 접두어 포함, 예: FIN-TERM-3.2';
COMMENT ON COLUMN "document"."source_path" IS 'knowledge-base/ 내 경로';

-- 추천 트리거 이벤트 — 카드 목록은 recommendation_card로 분리 (1NF)
CREATE TABLE "recommendation" (
    "recommendation_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "trigger_at_ms" INT NOT NULL,
    "internal_latency_ms" INT NULL,
    "e2e_latency_ms" INT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("recommendation_id"),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id")
);

-- 추천 카드 — 트리거 1건이 카드 여러 개를 낼 수 있어 분리 (1NF)
CREATE TABLE "recommendation_card" (
    "card_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "recommendation_id" BIGINT NOT NULL,
    "source_doc_id" VARCHAR(30) NULL,
    "title" VARCHAR(100) NOT NULL,
    "summary" TEXT NOT NULL,
    "similarity_score" REAL NULL,
    "rank" SMALLINT NOT NULL,
    PRIMARY KEY ("card_id"),
    FOREIGN KEY ("recommendation_id") REFERENCES "recommendation"("recommendation_id"),
    FOREIGN KEY ("source_doc_id") REFERENCES "document"("document_id")
);
COMMENT ON COLUMN "recommendation_card"."source_doc_id" IS 'B-6: 근거 없으면 NULL';
COMMENT ON COLUMN "recommendation_card"."title" IS '생성 모델 출력 — document.title과 다를 수 있음';

-- 카드 채택·무시 기록 (E-1) — 상담원이 추천을 실제로 썼는지. recommendation_card에 컬럼을 더하지 않고 분리한 이유: 피드백은 카드 내용과 다른 사실이고 자체 시각을 갖는다. 카드 하나에 이벤트가 여러 번 붙을 수 있어(채택→취소) 이력이 남아야 한다 — masking_event·compliance_flag와 같은 이벤트 테이블 패턴. ⚠ 상담원 단위로 집계해 점수·순위를 만들지 않는다(부록 A-1) — 카드 품질을 재는 데이터다
CREATE TABLE "card_feedback" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "card_id" BIGINT NOT NULL,
    "action" VARCHAR(30) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    CHECK ("action" IN ('adopted','ignored')),
    FOREIGN KEY ("card_id") REFERENCES "recommendation_card"("card_id")
);

-- F-2 필요서류 체크리스트 판정(헤더) — 2026-09-14 `decisions/305` 로 다산 절차에 맞춰 다시 만들었다. 전에는 금융보험·쇼핑 처리유형 4종 + 전용 BOOLEAN 10개였고, 다산 절차를 넣으면 CHECK 에 걸려 INSERT 가 거부됐다(`w4-schema-qa-followup` ③). 69종 서비스 × N종 서류를 컬럼으로 펼 수 없어 **헤더 + 항목(closure_item)** 2단이다. 테이블 이름을 유지한 이유: `knowledge_gap.closure_id` 가 참조한다
CREATE TABLE "closure" (
    "closure_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "procedure" VARCHAR(30) NOT NULL,
    "reason" VARCHAR(100) NULL,
    "detected" BOOLEAN NOT NULL,
    "verdict" VARCHAR(30) NOT NULL,
    "source_doc_id" VARCHAR(30) NULL,
    "decided_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("closure_id"),
    CHECK ("verdict" IN ('complete','incomplete')),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id")
);
COMMENT ON COLUMN "closure"."closure_id" IS 'append-only: UPDATE 없이 INSERT만 (F-4)';
COMMENT ON COLUMN "closure"."procedure" IS '절차 = 필요서류 조항 ID(예: DASAN-TERM-4.4). 규칙표 `closure_gate/domain/value_objects/closure_rule.py` 의 키';
COMMENT ON COLUMN "closure"."detected" IS 'true 면 서류 안내 여부를 **상담원 발화의 키워드로 자동 판정**했다(한계: 부정 문맥을 모른다). false 면 호출자가 체크리스트로 직접 넣었다';
COMMENT ON COLUMN "closure"."verdict" IS 'rev.5 — 차단(blocked)이 아니라 경고(incomplete)다. 다산에는 막을 종결 행위가 없다';
COMMENT ON COLUMN "closure"."source_doc_id" IS '판정 근거 조항. `document` 를 외래키로 잡지 않는다 — 그 테이블을 채우는 경로가 없다(2026-09-14 확인)';

-- F-2 체크리스트 항목 — 판정 1건의 서류별 안내 여부. 「해당 없음」은 행이 없는 것이라 NULL 의 이중 의미가 없다
CREATE TABLE "closure_item" (
    "closure_id" BIGINT NOT NULL,
    "rank" SMALLINT NOT NULL,
    "document_name" VARCHAR(60) NOT NULL,
    "informed" BOOLEAN NOT NULL,
    PRIMARY KEY ("closure_id", "rank"),
    FOREIGN KEY ("closure_id") REFERENCES "closure"("closure_id")
);
COMMENT ON COLUMN "closure_item"."rank" IS '규칙표의 서류 순서 — missing 출력 순서와 같다';

-- D-3 후속조치 항목 — 통화 1건에 여러 개 가능해 분리 (1NF)
CREATE TABLE "follow_up_action" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "action_text" VARCHAR(200) NOT NULL,
    "status" VARCHAR(20) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id")
);
COMMENT ON COLUMN "follow_up_action"."status" IS 'draft(규칙·모델 초안) · confirmed(상담원 확정, `decisions/310`) · superseded(재수정으로 대체 — 지우지 않는다, `decisions/311`)';

-- D-1~D-3 확정된 요약의 재수정 이력 — 고치기 **전** 값 한 벌 + 사유(`decisions/311`). 새 값은 `call` 에 있다. 누가 고쳤는지는 두지 않는다(부록 A-1 — 상담원 단위 집계 금지). 갱신·삭제하지 않는다
CREATE TABLE "call_summary_revision" (
    "revision_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "previous_summary_text" TEXT NOT NULL,
    "previous_inquiry_type" VARCHAR(30) NULL,
    "reason" VARCHAR(500) NOT NULL,
    "revised_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("revision_id"),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id")
);
COMMENT ON COLUMN "call_summary_revision"."previous_summary_text" IS '고치기 전 요약 — 마스킹본';
COMMENT ON COLUMN "call_summary_revision"."reason" IS '왜 고쳤는가 — 저장 전 마스킹';
CREATE INDEX "call_summary_revision_idx0" ON "call_summary_revision" ("call_id");

-- D-4 공백 리포트 — B/C/F 세 모듈의 실패 사례를 한 곳에 누적. ⚠ `description` 은 자유 입력이라 **저장 전에 마스킹을 통과시킨다**(`decisions/205` ⑤)
CREATE TABLE "knowledge_gap" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "module" VARCHAR(30) NOT NULL,
    "description" VARCHAR(300) NOT NULL,
    "call_id" VARCHAR(40) NULL,
    "call_id_seg" VARCHAR(40) NULL,
    "segment_id" BIGINT NULL,
    "closure_id" BIGINT NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    "status" VARCHAR(30) NOT NULL,
    PRIMARY KEY ("id"),
    CHECK ("module" IN ('B','C','F')),
    CHECK ("status" IN ('open','resolved')),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id"),
    FOREIGN KEY ("closure_id") REFERENCES "closure"("closure_id")
);
COMMENT ON COLUMN "knowledge_gap"."call_id_seg" IS 'transcript_segment 복합 FK 의 짝. call_id 와 같은 값이지만 이 표의 call_id 는 NULL 이 가능해 따로 둔다(`decisions/205`)';

-- 평가 실행 배치 — 6.2절 '여러 번 실행한 값 중 최저치 고정'을 위해 실행 단위로 분리
CREATE TABLE "eval_run" (
    "run_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "golden_set_version" VARCHAR(10) NOT NULL,
    "git_commit" VARCHAR(40) NULL,
    "error_rate" REAL NOT NULL,
    "executed_at" TIMESTAMPTZ NOT NULL,
    "executed_by" VARCHAR(30) NULL,
    PRIMARY KEY ("run_id")
);
COMMENT ON COLUMN "eval_run"."error_rate" IS '4.2절 STT 오류 주입률 0.00~0.20, 팀 교차검증 반영';

-- 평가 결과 상세 — 실행 1건이 지표 여러 개를 내므로 분리 (1NF)
CREATE TABLE "eval_result" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "run_id" BIGINT NOT NULL,
    "module" VARCHAR(10) NOT NULL,
    "metric_name" VARCHAR(40) NOT NULL,
    "metric_value" REAL NOT NULL,
    "passed_absolute_rule" BOOLEAN NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("run_id") REFERENCES "eval_run"("run_id")
);
COMMENT ON COLUMN "eval_result"."module" IS 'B/C/C-5/F-2 등';
COMMENT ON COLUMN "eval_result"."passed_absolute_rule" IS 'C-5·F-2만 해당, 그 외 NULL';

-- G-2 지역 자원 연계 — 조건부(여유 시) 모듈, 스키마만 선반영
CREATE TABLE "resource_center" (
    "center_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "category" VARCHAR(30) NOT NULL,
    "address" VARCHAR(200) NOT NULL,
    "region" VARCHAR(30) NOT NULL,
    "phone" VARCHAR(20) NULL,
    "operating_hours" VARCHAR(50) NULL,
    "is_active" BOOLEAN NOT NULL,
    PRIMARY KEY ("center_id"),
    CHECK ("category" IN ('정신건강복지센터','자살예방센터'))
);
COMMENT ON COLUMN "resource_center"."is_active" IS '폐지·이전 기관 반환 0건 검증용';

-- C-6 고객 폭언·위기 신호 탐지 이벤트(2026-09-09, `_project/decisions/205` ②). `compliance_flag` 와 **방향이 반대다** — 저쪽은 상담원 발화, 이쪽은 고객 발화다. 합치지 않는 이유 셋: ① `compliance_rule` 카탈로그가 C-1~C-4 뿐 ② 갈래 4종을 담을 컬럼이 없다 ③ 화자를 섞으면 D-4 재학습 데이터가 오염된다
CREATE TABLE "call_guard_flag" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "segment_id" BIGINT NOT NULL,
    "category" VARCHAR(30) NOT NULL,
    "phrase" VARCHAR(200) NOT NULL,
    "span_start" INT NOT NULL,
    "span_end" INT NOT NULL,
    "source_doc_id" VARCHAR(30) NULL,
    "detected_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    CHECK ("category" IN ('insult','threat','sexual','distress')),
    FOREIGN KEY ("source_doc_id") REFERENCES "document"("document_id"),
    FOREIGN KEY ("call_id", "segment_id") REFERENCES "transcript_segment"("call_id", "segment_id")
);
COMMENT ON COLUMN "call_guard_flag"."category" IS '⚠ `distress` 는 나머지 셋과 **대응이 정반대다**(MANUAL-5.4 — 통화를 끊지 않고 전문 기관 연결). 한 값으로 뭉치면 위기 상황에서 전화를 끊게 된다';
COMMENT ON COLUMN "call_guard_flag"."phrase" IS '⚠ **마스킹된 자막에서 잘라낸 구간**이다(MANUAL-5.5). 원문이 아니다';
COMMENT ON COLUMN "call_guard_flag"."span_start" IS '문자(코드포인트) 오프셋 — 7.3절';
COMMENT ON COLUMN "call_guard_flag"."source_doc_id" IS '근거 조항(DASAN-MANUAL-5.x). 갈래마다 다르다';

-- D-5 통화 온도 이상 구간(2026-09-09, `_project/decisions/203`·`205` ③). ⚠ **오디오를 보관하지 않으므로**(절대 원칙 7) 통화가 끝나면 재계산이 불가능하다 — 저장하지 않으면 통화 후 처리가 보여줄 것이 사라진다
CREATE TABLE "voice_outlier" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "segment_id" BIGINT NOT NULL,
    "speaker" VARCHAR(30) NOT NULL,
    "robust_z" REAL NOT NULL,
    "baseline_n" SMALLINT NOT NULL,
    "detected_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    CHECK ("speaker" IN ('customer','agent')),
    FOREIGN KEY ("call_id", "segment_id") REFERENCES "transcript_segment"("call_id", "segment_id")
);
COMMENT ON COLUMN "voice_outlier"."speaker" IS '기준선은 **화자별**로 만든다 — 절대 임계값을 쓰면 베테랑 상담사가 통화 내내 걸린다(2026-09-09 실측)';
COMMENT ON COLUMN "voice_outlier"."robust_z" IS '⚠ **화면에 내지 않는다**(부록 A-1). 저장하는 이유는 임계값 3.5 가 「재서 고른 값이 아니라」 나중에 바꿔 재판정해야 하기 때문이다 — 저장과 표시는 다르다';
COMMENT ON COLUMN "voice_outlier"."baseline_n" IS '기준선을 만든 발화 수. 8 미만이면 애초에 판정하지 않는다';

-- J-1·J-2 상담원이 올린 블랙리스트 전환 요청 (`_project/decisions/204`). ⚠ **시스템은 판정하지 않는다** — 상담원이 요청하고 관리자가 결정한다. 그래서 요청과 등록(blacklist_entry)이 별도 테이블이다: 한 테이블에 status 만 두면 「승인된 적 없는 등록」과 「반려된 요청」이 섞인다. 근거 컬럼(insult/threat/sexual/temperature)을 펼쳐 둔 것은 **역정규화**다 — 요청 1건에 각 1개뿐인 값이라 별도 테이블로 빼면 조인만 늘고 얻는 것이 없다
CREATE TABLE "blacklist_request" (
    "request_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "customer_ref" VARCHAR(64) NOT NULL,
    "display_hint" VARCHAR(8) NULL,
    "requested_by" VARCHAR(20) NOT NULL,
    "reason" VARCHAR(500) NOT NULL,
    "context_excerpt" TEXT NOT NULL,
    "call_duration_s" INT NOT NULL,
    "insult_count" SMALLINT NOT NULL,
    "threat_count" SMALLINT NOT NULL,
    "sexual_count" SMALLINT NOT NULL,
    "temperature_outliers" SMALLINT NOT NULL,
    "status" VARCHAR(30) NOT NULL,
    "requested_at" TIMESTAMPTZ NOT NULL,
    "decided_by" VARCHAR(20) NULL,
    "decided_at" TIMESTAMPTZ NULL,
    "evidence_snapshot_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("request_id"),
    CHECK ("status" IN ('pending','approved','rejected')),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id"),
    FOREIGN KEY ("requested_by") REFERENCES "agent"("agent_id"),
    FOREIGN KEY ("decided_by") REFERENCES "agent"("agent_id")
);
COMMENT ON COLUMN "blacklist_request"."customer_ref" IS '⚠ **전화번호의 HMAC-SHA256 이다. 평문을 넣지 않는다**(`decisions/205` ③) — 전화번호는 C-5 의 P4 이고, 자막에서 지운 값을 여기 평문으로 두면 마스킹을 앞단에 둔 의미가 사라진다. 키는 .env(SEC-2)';
COMMENT ON COLUMN "blacklist_request"."display_hint" IS '화면 표시 전용(뒤 4자리 등). 조회·배정은 customer_ref 로만 한다';
COMMENT ON COLUMN "blacklist_request"."reason" IS '상담원이 적은 사유';
COMMENT ON COLUMN "blacklist_request"."context_excerpt" IS '⚠ **마스킹된 자막**이다. 원문을 넣지 않는다 — MANUAL-5.5 · C-5 · SEC-1';
COMMENT ON COLUMN "blacklist_request"."temperature_outliers" IS 'D-5 통화 온도 이상 구간 수(`decisions/203`). 점수가 아니라 건수다 — 부록 A-1';
COMMENT ON COLUMN "blacklist_request"."status" IS '**요청의 상태만** 담는다(`decisions/205` ②). 해제(released)는 등록의 상태이지 요청의 상태가 아니다 — 두 곳에 두면 한쪽만 갱신돼 어긋난다. 상담원은 pending 까지만 만들 수 있다';
COMMENT ON COLUMN "blacklist_request"."evidence_snapshot_at" IS '위 *_count 를 집계한 시각. 원천은 call_guard_flag·voice_outlier 이고 여기 값은 **관리자가 본 시점의 스냅샷**이다(`decisions/205`)';
CREATE INDEX "blacklist_request_idx0" ON "blacklist_request" ("status", "requested_at" DESC);

-- J-4 등록 **에피소드**. 고객이 아니라 「이번 등록」이 한 행이다 — 해제 후 재등록되면 행이 하나 더 생기고 옛 행은 released_at 이 찍힌 채 남는다. ⚠ PK 를 customer_ref 로 두었더니 **재등록이 PK 위반이거나 첫 등록 이력을 덮어썼다**(`decisions/205` ②). ⚠ **차단 목록이 아니다** — 전화는 정상적으로 받고, 바뀌는 것은 누구에게 배정되는가뿐이다
CREATE TABLE "blacklist_entry" (
    "entry_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "customer_ref" VARCHAR(64) NOT NULL,
    "request_id" BIGINT NOT NULL,
    "approved_at" TIMESTAMPTZ NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "released_at" TIMESTAMPTZ NULL,
    "released_by" VARCHAR(20) NULL,
    "release_reason" VARCHAR(500) NULL,
    "note" VARCHAR(500) NULL,
    PRIMARY KEY ("entry_id"),
    UNIQUE ("request_id"),
    FOREIGN KEY ("request_id") REFERENCES "blacklist_request"("request_id"),
    FOREIGN KEY ("released_by") REFERENCES "agent"("agent_id")
);
COMMENT ON COLUMN "blacklist_entry"."customer_ref" IS '전화번호의 HMAC. blacklist_request 와 같은 체계다(`decisions/205` ③)';
COMMENT ON COLUMN "blacklist_entry"."approved_at" IS '등록 시작. 에피소드의 고유 사실이다. 승인자는 request.decided_by 로 따라간다';
COMMENT ON COLUMN "blacklist_entry"."expires_at" IS '**만료가 없으면 영구 표시가 된다**(`decisions/205` ⑤). J-5 는 released_at IS NULL AND expires_at > now() 만 본다. 관리자가 연장·단축할 수 있고 그때마다 blacklist_entry_expiry_change 에 쌓인다(`decisions/309` — 205 「새 요청으로만」 철회)';
COMMENT ON COLUMN "blacklist_entry"."released_at" IS '해제 시각. **행을 지우지 않는다** — 지우면 「왜 풀렸는지」가 사라진다(절대 원칙 8)';
COMMENT ON COLUMN "blacklist_entry"."released_by" IS '⚠ 행만 남기고 이 컬럼이 없어서 **어차피 「왜 풀렸는지」가 기록되지 않았다**';
COMMENT ON COLUMN "blacklist_entry"."note" IS '**관리자 승인 메모**다. 요청 사유의 사본이 아니다 — 사본을 두면 같은 개인정보가 두 벌이 된다(`decisions/205` ⑤)';
CREATE UNIQUE INDEX "blacklist_entry_uq0" ON "blacklist_entry" ("customer_ref") WHERE "released_at" IS NULL;

-- J-4 등록 만료 변경 이력 — 관리자 연장·단축 1건 = 1행(`decisions/309`). `blacklist_entry.expires_at` 만 덮으면 누가 왜 늘리거나 줄였는지가 사라진다. 갱신·삭제하지 않는다
CREATE TABLE "blacklist_entry_expiry_change" (
    "change_id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "entry_id" BIGINT NOT NULL,
    "previous_expires_at" TIMESTAMPTZ NOT NULL,
    "new_expires_at" TIMESTAMPTZ NOT NULL,
    "changed_by" VARCHAR(20) NOT NULL,
    "reason" VARCHAR(500) NOT NULL,
    "changed_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("change_id"),
    FOREIGN KEY ("entry_id") REFERENCES "blacklist_entry"("entry_id"),
    FOREIGN KEY ("changed_by") REFERENCES "agent"("agent_id")
);
COMMENT ON COLUMN "blacklist_entry_expiry_change"."new_expires_at" IS '이전보다 뒤면 연장, 앞이면 단축이다 — 방향을 따로 저장하지 않는다';
COMMENT ON COLUMN "blacklist_entry_expiry_change"."changed_by" IS '로그인한 관리자에 연결된 agent_id(`decisions/304`) — released_by 와 같은 체계';
COMMENT ON COLUMN "blacklist_entry_expiry_change"."reason" IS '저장 전 마스킹(`decisions/205` ⑤)';
CREATE INDEX "blacklist_entry_expiry_change_idx0" ON "blacklist_entry_expiry_change" ("entry_id");

-- J-5 배정 결과. **떨어뜨린 경우를 세는 것**이 이 테이블의 목적이다 — 「베테랑이 부족하다」가 fell_back 의 집계다
CREATE TABLE "routing_log" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "call_id" VARCHAR(40) NOT NULL,
    "is_blacklisted" BOOLEAN NOT NULL,
    "assigned_agent_id" VARCHAR(20) NULL,
    "fell_back" BOOLEAN NOT NULL,
    "reason" VARCHAR(200) NOT NULL,
    "routed_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    FOREIGN KEY ("call_id") REFERENCES "call"("call_id"),
    FOREIGN KEY ("assigned_agent_id") REFERENCES "agent"("agent_id")
);
COMMENT ON COLUMN "routing_log"."fell_back" IS '베테랑이 없어 일반 배정으로 떨어진 건';

-- 관리자 로그인 허용 목록. 회원가입이 없다 — 구글 로그인으로 들어온 이메일이 여기 있어야 관리자로 인정한다. 행을 추가·삭제하는 것이 곧 관리자 등록·해제다. `agent.role='admin'`(J-4 승인 권한)과는 다른 개념이다 — 그쪽은 상담원 마스터의 역할 구분이고, 이것은 관리자 화면 로그인 자격이다. 둘을 합치면 상담원이 아닌 관리자 계정을 못 만든다
CREATE TABLE "admin_account" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "email" VARCHAR(255) NOT NULL,
    "name" VARCHAR(100) NULL,
    "agent_id" VARCHAR(20) NULL,
    "created_at" TIMESTAMPTZ NOT NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("email"),
    FOREIGN KEY ("agent_id") REFERENCES "agent"("agent_id")
);
COMMENT ON COLUMN "admin_account"."email" IS '구글 계정 이메일. 대소문자는 저장 전에 소문자로 맞춘다';
COMMENT ON COLUMN "admin_account"."name" IS '구글 프로필 이름 — 화면 표시용, 판단에 쓰지 않는다';
COMMENT ON COLUMN "admin_account"."agent_id" IS '이 관리자가 J-4 승인·해제를 기록할 때 쓰는 상담원 마스터 ID(`decisions/304`). `blacklist_request.decided_by`·`blacklist_entry.released_by` 가 agent 를 참조해서다. NULL 이면 로그인은 되지만 블랙리스트 결정은 못 한다(409) — 누구로 기록할지 지어내지 않는다';

-- 관리자 세션의 refresh token. **원문을 저장하지 않는다** — SHA-256 해시만 둔다(SEC-1과 같은 원칙: 탈취되는 값을 저장하지 않는다). 만료(10분, 테스트 값)는 애플리케이션이 계산해서 넣는다. 회전(rotation) 방식이라 refresh 할 때마다 기존 행을 revoked_at 으로 무효화하고 새 행을 만든다 — 지우지 않는다 (절대 원칙 8, 탈취 흔적 추적용)
CREATE TABLE "admin_refresh_token" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "admin_account_id" BIGINT NOT NULL,
    "token_hash" VARCHAR(64) NOT NULL,
    "issued_at" TIMESTAMPTZ NOT NULL,
    "expires_at" TIMESTAMPTZ NOT NULL,
    "revoked_at" TIMESTAMPTZ NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("token_hash"),
    FOREIGN KEY ("admin_account_id") REFERENCES "admin_account"("id")
);
COMMENT ON COLUMN "admin_refresh_token"."token_hash" IS 'SHA-256 hex — 원문은 응답으로만 한 번 나가고 저장하지 않는다';
COMMENT ON COLUMN "admin_refresh_token"."revoked_at" IS '회전·로그아웃으로 무효화된 시각. NULL 이면 아직 유효(만료 전이라면)';
CREATE INDEX "admin_refresh_token_idx0" ON "admin_refresh_token" ("admin_account_id");

-- 상담원 전용 토큰(`decisions/307`). 상담원 로그인 화면이 없어 관리자가 발급해 건넨다 — 블랙리스트 요청의 요청자를 본문이 아니라 이 토큰에서 얻는다(`decisions/304` 의 남은 구멍). **원문을 저장하지 않는다** — SHA-256 해시만 둔다(`admin_refresh_token` 과 같은 원칙). 폐기해도 행을 지우지 않는다(절대 원칙 8, 누가 언제 쓰던 토큰인지 흔적용). 만료는 아직 없다 — 폐기로만 끊는다
CREATE TABLE "agent_token" (
    "id" BIGINT GENERATED ALWAYS AS IDENTITY NOT NULL,
    "agent_id" VARCHAR(20) NOT NULL,
    "token_hash" VARCHAR(64) NOT NULL,
    "issued_by" BIGINT NULL,
    "issued_at" TIMESTAMPTZ NOT NULL,
    "revoked_at" TIMESTAMPTZ NULL,
    PRIMARY KEY ("id"),
    UNIQUE ("token_hash"),
    FOREIGN KEY ("agent_id") REFERENCES "agent"("agent_id"),
    FOREIGN KEY ("issued_by") REFERENCES "admin_account"("id")
);
COMMENT ON COLUMN "agent_token"."token_hash" IS 'SHA-256 hex — 원문(`cga_…`)은 발급 응답으로 한 번만 나가고 저장하지 않는다';
COMMENT ON COLUMN "agent_token"."issued_by" IS '발급한 관리자';
COMMENT ON COLUMN "agent_token"."revoked_at" IS '폐기 시각. NULL 이면 유효';
CREATE INDEX "agent_token_idx0" ON "agent_token" ("agent_id");

-- 관리자가 바꾸는 운영 설정 — 키 1개 = 1행(`decisions/313`). 지금은 `veteran_years`(J-5 베테랑 근속 기준) 하나다. 행이 없으면 코드의 기본값을 쓴다 — 기본값을 여기 미리 넣지 않는다(두 곳에 적지 않는다)
CREATE TABLE "app_setting" (
    "setting_key" VARCHAR(50) NOT NULL,
    "value" VARCHAR(200) NOT NULL,
    "updated_at" TIMESTAMPTZ NOT NULL,
    "updated_by" BIGINT NULL,
    PRIMARY KEY ("setting_key"),
    FOREIGN KEY ("updated_by") REFERENCES "admin_account"("id")
);
COMMENT ON COLUMN "app_setting"."value" IS '문자열로 저장한다 — 해석은 그 키를 쓰는 코드가 한다';
COMMENT ON COLUMN "app_setting"."updated_by" IS '마지막으로 바꾼 관리자';
