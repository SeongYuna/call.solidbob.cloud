---
title: "서버 잔손질 묶음 — `/health` 배포 버전 · `eval_run` 구성 컬럼 · 보존 기간 · ERD · D-6 주석"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 6
priority: 80
date: 2026-09-22
paths:
  - "server/*"
  - "db/*"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

작아서 티켓 하나로 묶는다. 순서대로.

1. `/health` 에 배포 이미지 태그 — 밖에서 어느 태그가 떠 있는지 알 길이 없다(09-22 하루에 태그가 네 번 겹쳤다)
2. `eval_run` 에 검색·NER 구성 컬럼 — run_id 3·4·7 이 DB 만으로 구분되지 않는다(류준 님 요청)
3. 보존 기간을 결정 하나로 묶기(`decisions/3xx`)
4. `db/generate_schema_docs.py` 로 ERD 재생성(199 컬럼 반영)
5. D-6 주석 · 「허브는 스포크를 직접 import 하지 않는다」 계약을 `.importlinter` 에 넣을지

## 완료 조건

- [x] 1·2 는 코드+테스트, 3 은 결정 기록, 4 는 그림 갱신, 5 는 넣거나 「안 넣는다」 한 줄

## 2026-09-22 — 장민석 착수·완료 (담당 확인)

1. **`/health` 의 `version`** — 빌드 인자 `APP_VERSION` 을 이미지에 굽는다(`server.Dockerfile` 끝 · `release.yml` `build-args`). 로컬은 `"unknown"`. 테스트 2건 · 런북 19장 9번
2. **`eval_run.components`** VARCHAR(100) — `run_eval.py --record` 가 실제 구성 한 줄(`retriever=…; masking=rule[+ner]; generation=…`)을 적는다. 마이그레이션 `2026-09-22-eval-run-components.sql`(서버 이미지와 무관, `--record` 전에) — 변경 전 스키마에 넣어 보고 재적용이 멈추는 것까지 확인. 기존 run 은 NULL 로 둔다(소급 안 함)
3. **보존 기간** — `decisions/325` 한 표(원문 0 · 번호 평문 0 · 등록 최대 365일 · 자유 입력 180일 · 나머지 프로젝트 기간 · 평가 기록은 안 지움). 시연 범위의 결정이라고 적었다
4. **ERD** — 생성기(`generate_schema_docs.py`)에 컬럼을 넣고 재생성 → `schema.sql` 이 수동 편집과 한 글자도 다르지 않았다(29 테이블). PNG 는 graphviz 가 없어 **임시 도커(alpine + graphviz + noto-cjk)**로 렌더 · `jekyll/assets/erd/` 복사
5. **D-6 주석** — `/close` 가 통화 종료 즉시 초안을 주는 경로라 `# Requirement: … D-6` 추가. **`.importlinter` 는 넣었다 — 단 범위를 좁혀서**: 「허브는 스포크를 import 하지 않는다」를 통째로 걸면 성립하지 않는다(`hub.dependencies` 가 합성, `hub.adapter` 가 인증 가드). **`hub.app`(DTO·포트·인터랙터) → 스포크 금지**로 넣었고 지금 KEPT — 계약 4종 → 5종
