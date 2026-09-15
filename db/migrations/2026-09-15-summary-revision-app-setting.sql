-- 통화 후 요약 재수정 이력 + 운영 설정 — 27 테이블 → 29 테이블 (decisions/311 · decisions/313)
--
-- 왜 파일이 따로 있나: db/schema.sql 은 빈 DB 에 넣는 전체 DDL 이라 데이터가 있는 운영 DB 에는 CREATE TABLE 이 실패한다.
-- 담는 것: ① call_summary_revision 신설 ② follow_up_action.status 컬럼 주석(draft · confirmed · superseded)
--         ③ app_setting 신설(J-5 베테랑 근속 기준). 기존 행·제약은 건드리지 않는다(순증).
-- 전제: 2026-09-15-blacklist-expiry-change.sql 까지 들어간 DB(27 테이블) — 없으면 멈춘다.
--
-- ⚠ 순서: **서버 이미지를 올리기 전에** 넣는다(런북 19장). 안 넣은 채 새 이미지가 뜨면
--   POST /hub/calls/{id}/summary-revision · …/summary-revisions · /hub/routing-decisions · /hub/routing-settings 가 500(`42P01`)이고 다른 경로는 영향 없다.
--
-- 트랜잭션 하나다. 중간에 실패하면 아무것도 바뀌지 않는다. 이미 적용된 DB 면 멈춘다.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'blacklist_entry_expiry_change') THEN
    RAISE EXCEPTION 'blacklist_entry_expiry_change 가 없다 — 2026-09-15-blacklist-expiry-change.sql 부터 넣는다';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename IN ('call_summary_revision', 'app_setting')) THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
END $$;

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

COMMIT;
