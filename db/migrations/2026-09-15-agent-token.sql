-- 상담원 전용 토큰 테이블 — 2026-09-14 마이그레이션 적용 DB(25 테이블) → 26 테이블 (decisions/307)
--
-- 왜 파일이 따로 있나: db/schema.sql 은 빈 DB 에 넣는 전체 DDL 이라 데이터가 있는 운영 DB 에는 CREATE TABLE 이 실패한다.
-- 담는 것: agent_token 신설 하나뿐이다. 기존 테이블은 건드리지 않는다(순증).
-- 전제: 2026-09-14-customer-ref-admin-closure.sql 이 먼저 들어가 있어야 한다 — admin_account 를 외래키로 참조한다.
--
-- ⚠ 순서: **서버 이미지를 올리기 전에** 넣는다(런북 19장). 안 넣은 채 새 이미지가 뜨면
--   POST /hub/blacklist-requests 와 /admin/agent-tokens 가 500 이다(`agent_token` 없음, 42P01).
--
-- 트랜잭션 하나다. 중간에 실패하면 아무것도 바뀌지 않는다. 이미 적용된 DB 면 멈춘다.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'admin_account') THEN
    RAISE EXCEPTION 'admin_account 가 없다 — 2026-09-14-customer-ref-admin-closure.sql 부터 넣는다';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'agent_token') THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
END $$;

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

COMMIT;
