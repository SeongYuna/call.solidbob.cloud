-- 블랙리스트 요청 — D-5 「미측정」 · 반려 사유 (decisions/316). 테이블 수는 그대로 29
--
-- 왜 파일이 따로 있나: db/schema.sql 은 빈 DB 에 넣는 전체 DDL 이라 데이터가 있는 운영 DB 에는 CREATE TABLE 이 실패한다.
-- 담는 것: ① blacklist_request.temperature_outliers NOT NULL 해제 — NULL = 미측정(0 = 이상 없음과 다르다)
--         ② blacklist_request.decision_note 신설(반려 사유) ③ display_hint 주석(채우지 않는다)
--         ④ admin_account.agent_id 주석(비어 있으면 서버가 채운다 — decisions/314, 컬럼은 그대로).
--         기존 행은 건드리지 않는다 — 지금까지 저장된 temperature_outliers 0 은 실제로는 미측정이었지만 소급해 바꾸지 않는다(절대 원칙 8).
-- 전제: 2026-09-15-summary-revision-app-setting.sql 까지 들어간 DB(29 테이블) — 없으면 멈춘다.
--
-- ⚠ 순서: **서버 이미지를 올리기 전에** 넣는다(런북 19장). 안 넣은 채 새 이미지가 뜨면
--   블랙리스트 요청 생성(POST /hub/blacklist-requests)이 NOT NULL 위반으로, 요청 목록·결정이 없는 컬럼으로 500 이다.
--   이 파일을 먼저 넣어도 **지금 떠 있는 이미지는 영향이 없다** — 순증이다.
--
-- 트랜잭션 하나다. 중간에 실패하면 아무것도 바뀌지 않는다. 이미 적용된 DB 면 멈춘다.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'app_setting') THEN
    RAISE EXCEPTION 'app_setting 이 없다 — 2026-09-15-summary-revision-app-setting.sql 부터 넣는다';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'blacklist_request' AND column_name = 'decision_note') THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
END $$;

ALTER TABLE "blacklist_request" ALTER COLUMN "temperature_outliers" DROP NOT NULL;
ALTER TABLE "blacklist_request" ADD COLUMN "decision_note" VARCHAR(500) NULL;

COMMENT ON COLUMN "blacklist_request"."temperature_outliers" IS 'D-5 통화 온도 이상 구간 수(`decisions/203`). 점수가 아니라 건수다 — 부록 A-1. **NULL 은 「미측정」**이다 — 서버 요청 경로에 D-5 판정이 붙지 않아 셀 수 없었다(`decisions/316`). 0(「이상 없음」)과 다르다';
COMMENT ON COLUMN "blacklist_request"."decision_note" IS '**반려 사유**(관리자, 반려면 필수 — `decisions/316`). 저장 전 마스킹. 승인 메모는 여기가 아니라 blacklist_entry.note 다. 반려 180일 뒤 비운다(`decisions/312`)';
COMMENT ON COLUMN "blacklist_request"."display_hint" IS '⚠ **채우지 않는다**(`decisions/316`) — 전화번호 뒷자리도 P4 의 일부라 HMAC 으로 가린 것을 되돌리는 단서가 된다. 관리자는 call_id·마스킹된 자막으로 알아본다. 컬럼은 되돌릴 때를 위해 남긴다';
COMMENT ON COLUMN "admin_account"."agent_id" IS '이 관리자가 J-4 승인·해제를 기록할 때 쓰는 상담원 마스터 ID(`decisions/304`). `blacklist_request.decided_by`·`blacklist_entry.released_by` 가 agent 를 참조해서다. 비어 있으면 처음 결정할 때 서버가 그 관리자 전용 agent 행(`admin-<id>`, role=admin)을 만들어 채운다(`decisions/314` — 전엔 409). 채운 값은 덮어쓰지 않는다';

COMMIT;
