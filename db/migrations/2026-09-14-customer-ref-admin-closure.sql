-- 운영 DB 스키마 따라잡기 — fd96adc(2026-09-09, 테이블 22개) → b1dade6(2026-09-14, 25개)
--
-- 왜 파일이 따로 있나: db/schema.sql 은 빈 DB 에 넣는 전체 DDL 이라, 데이터가 있는 운영 DB 에는 CREATE TABLE 이 실패한다.
-- 이 파일은 그 사이 바뀐 것만 옮긴다. 2026-09-14 운영에서 확인한 상태(테이블 22개 · closure 0건 · customer_id 채워진 call 0건)를 전제로 한다.
--
-- 담는 것
--   ① admin_account · admin_refresh_token 신설 (cb959a9 관리자 로그인 — 운영에 안 들어갔었다) + admin_account.agent_id (decisions/304)
--   ② customer.customer_id · call.customer_id VARCHAR(40) → (64) (decisions/304, HMAC hex)
--   ③ closure 재정의 + closure_item 신설 (decisions/305). closure 가 비어 있을 때만 — 행이 있으면 멈춘다
--
-- 트랜잭션 하나다. 중간에 실패하면 아무것도 바뀌지 않는다.
-- 검증: 로컬 postgres:17 에 fd96adc 스키마를 넣고 이 파일을 적용한 뒤, 현재 schema.sql 로 새로 만든 DB 와
--       테이블·컬럼·타입·NULL·제약·인덱스를 비교해 같음을 확인했다(2026-09-14).

BEGIN;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('admin_account', 'closure_item')) THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
  IF (SELECT count(*) FROM "closure") > 0 THEN
    RAISE EXCEPTION 'closure 에 행이 있다 — 옛 금융·쇼핑 판정을 어떻게 할지 정하기 전에는 멈춘다';
  END IF;
END $$;

-- ① 관리자 로그인
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

-- ② 고객 식별자 HMAC(hex 64자)
ALTER TABLE "customer" ALTER COLUMN "customer_id" TYPE VARCHAR(64);
ALTER TABLE "call" ALTER COLUMN "customer_id" TYPE VARCHAR(64);
COMMENT ON COLUMN "customer"."customer_id" IS '**전화번호의 HMAC-SHA256(hex 64자)** — `blacklist_request.customer_ref` 와 같은 체계다. 평문 번호·실명을 저장하지 않는다. 통화 시작(`POST /hub/calls` 의 caller_phone)에서 만든다 (`decisions/304`, 2026-09-14 VARCHAR(40)→(64) — 40 자로는 HMAC 이 안 들어갔다)';
COMMENT ON COLUMN "call"."customer_id" IS '콜 미디에이터가 발신 번호를 넘긴 통화만 채워진다(`decisions/304`). 재상담 이력·블랙리스트 요청의 연결 고리';

-- ③ F-2 필요서류 체크리스트. knowledge_gap.closure_id 외래키는 CASCADE 로 함께 떨어지고 아래에서 다시 건다
DROP TABLE "closure" CASCADE;
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

ALTER TABLE "knowledge_gap" ADD FOREIGN KEY ("closure_id") REFERENCES "closure"("closure_id");

COMMIT;
