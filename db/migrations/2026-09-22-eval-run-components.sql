-- 평가 실행에 구성 한 줄 — eval_run.components (w6-server-loose-ends ②, 2026-09-22). 테이블 수는 그대로 29
--
-- 왜: run_id 3·4·7 처럼 검색기(bm25·dense·rerank-dense·hybrid)나 NER 을 바꿔 잰 실행이 DB 만으로 구분되지 않았다(류준 님 요청).
-- 담는 것: eval_run.components VARCHAR(100) NULL 신설. 기존 행은 NULL 로 둔다 — 그때 무엇을 꽂았는지 소급해 적지 않는다(절대 원칙 8).
-- 전제: 2026-09-22-blacklist-request-note-unmeasured.sql 까지 들어간 DB — 없으면 멈춘다.
--
-- ⚠ 순서: 서버 이미지와 **무관**하다 — 이 컬럼은 평가 스크립트(`scripts/run_eval.py --record`)만 쓴다.
--   다만 그 스크립트를 `--record` 로 돌리기 전에는 넣어야 한다(없으면 INSERT 가 없는 컬럼으로 실패).
--   배포 전 스키마 대조(`decisions/128`)가 붙으면 이 파일을 넣기 전까지 어긋남으로 잡힌다.
--
-- 트랜잭션 하나다. 이미 적용된 DB 면 멈춘다.

BEGIN;

DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                 WHERE table_schema = 'public' AND table_name = 'blacklist_request' AND column_name = 'decision_note') THEN
    RAISE EXCEPTION 'blacklist_request.decision_note 가 없다 — 2026-09-22-blacklist-request-note-unmeasured.sql 부터 넣는다';
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = 'eval_run' AND column_name = 'components') THEN
    RAISE EXCEPTION '이미 적용된 DB 다 — 멈춘다';
  END IF;
END $$;

ALTER TABLE "eval_run" ADD COLUMN "components" VARCHAR(100) NULL;
COMMENT ON COLUMN "eval_run"."components" IS '실제로 꽂은 구성 한 줄 — 예: retriever=hybrid; masking=rule+ner; generation=none. 검색기·NER 을 바꿔 잰 실행이 DB 만으로 구분되지 않았다(2026-09-22). 그 전 실행은 NULL';

COMMIT;
