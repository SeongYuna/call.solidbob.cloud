-- 고객 뒤 4자리 표시(decisions/144 — 316 「채우지 않는다」 일부 철회). 테이블 수는 그대로 29
--
-- 담는 것: ① customer.display_hint VARCHAR(8) NULL 신설 — 통화 시작(POST /hub/calls, caller_phone)에서 `****1234` 로 만든다
--         ② blacklist_request.display_hint 주석 갱신(요청 생성 때 customer 에서 옮겨 적는다). 컬럼은 이미 있다
--         기존 행은 건드리지 않는다 — 번호 원문이 없어 되채울 수 없다(SEC-1). 새 통화부터 채워진다
-- 전제: 2026-09-22-blacklist-request-note-unmeasured.sql 까지 들어간 DB — 없으면 멈춘다.
--
-- ⚠ 순서: **서버 이미지(0.1.44)를 올리기 전에** 넣는다(런북 19장). 안 넣은 채 새 이미지가 뜨면
--   통화 시작(POST /hub/calls)이 없는 컬럼으로 500 이다. 이 파일을 먼저 넣어도 지금 떠 있는 이미지는 영향이 없다 — 순증이다.
--
-- 트랜잭션 하나다. 이미 적용된 DB 면 멈춘다.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = 'public' AND table_name = 'blacklist_request' AND column_name = 'decision_note') THEN
    RAISE EXCEPTION 'decision_note 가 없다 — 2026-09-22-blacklist-request-note-unmeasured.sql 부터 넣는다';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'customer' AND column_name = 'display_hint') THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
END $$;

ALTER TABLE "customer" ADD COLUMN "display_hint" VARCHAR(8) NULL;

COMMENT ON COLUMN "customer"."display_hint" IS '화면 표시용 뒤 4자리 `****1234`(`decisions/144`, 2026-10-01 — 316 일부 철회). 통화 시작에서 발신 번호로 만들고 그 뒤 번호는 버린다. 뒤 4자리만이라 번호를 되돌릴 수 없다. NULL = 번호가 없던 고객';
COMMENT ON COLUMN "blacklist_request"."display_hint" IS '화면 표시용 뒤 4자리 `****1234` — customer.display_hint 를 요청 생성 때 옮겨 적는다(`decisions/144`, 2026-10-01). 채우지 않는다(`316`)는 일부 철회. 옛 행·번호 없던 통화는 NULL';

COMMIT;
