-- 블랙리스트 등록 만료 변경 이력 — 26 테이블 → 27 테이블 (decisions/309)
--
-- 왜 파일이 따로 있나: db/schema.sql 은 빈 DB 에 넣는 전체 DDL 이라 데이터가 있는 운영 DB 에는 CREATE TABLE 이 실패한다.
-- 담는 것: ① blacklist_entry_expiry_change 신설 ② blacklist_entry.expires_at 컬럼 주석 갱신(205 「연장은 새 요청으로만」 철회).
-- 기존 행·제약은 건드리지 않는다(순증).
-- 전제: 2026-09-15-agent-token.sql 까지 들어간 DB(26 테이블) — agent_token 이 없으면 멈춘다.
--
-- ⚠ 순서: **서버 이미지를 올리기 전에** 넣는다(런북 19장). 안 넣은 채 새 이미지가 뜨면
--   POST /hub/blacklist-entries/{id}/expiry 와 …/expiry-changes 가 500(`42P01`)이다. 다른 경로는 영향 없다.
--
-- 트랜잭션 하나다. 중간에 실패하면 아무것도 바뀌지 않는다. 이미 적용된 DB 면 멈춘다.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'agent_token') THEN
    RAISE EXCEPTION 'agent_token 이 없다 — 2026-09-15-agent-token.sql 부터 넣는다';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'blacklist_entry_expiry_change') THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
END $$;

COMMENT ON COLUMN "blacklist_entry"."expires_at" IS '**만료가 없으면 영구 표시가 된다**(`decisions/205` ⑤). J-5 는 released_at IS NULL AND expires_at > now() 만 본다. 관리자가 연장·단축할 수 있고 그때마다 blacklist_entry_expiry_change 에 쌓인다(`decisions/309` — 205 「새 요청으로만」 철회)';

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

COMMIT;
