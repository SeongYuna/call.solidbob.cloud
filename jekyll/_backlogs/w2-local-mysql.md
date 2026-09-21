---
title: "로컬 MySQL 도커 구성 + 스키마 적용"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 2
priority: 1
date: 2026-08-27
requirement:
  - "SEC-1"
  - "SEC-2"
paths:
  - "infra/docker-compose.yml"
  - "infra/README.md"
---

`db/schema.sql` 이 설계 문서로만 있고 **실제로 적용된 적이 없었다.** 조회 API 3건
([w3](/backlog/w3-transcript-query-api/)·[w4](/backlog/w4-knowledge-gap-intake/)·[w7](/backlog/w7-card-feedback/))이
전부 여기서 막혀 있었다.

```bash
cd infra && docker compose up -d     # 최초 기동 시 ../db/schema.sql 자동 적용
```

팀원 누구나 같은 명령으로 같은 상태를 만들 수 있게 `infra/` 에 뒀다. 자세한 건
[`infra/README.md`](https://github.com/solidbob02/call.solidbob.cloud/blob/main/infra/README.md).

## ⚠ 적용하면서 스키마 버그를 찾았다 — 예약어

첫 시도에서 **16개 테이블 중 2개만 만들어졌다.**

```
ERROR 1064 (42000) at line 21: ... near 'call ('
```

`CALL` 은 MySQL 예약어(스토어드 프로시저 호출)다. `CREATE TABLE call (` 에서 파싱이 멈추고
**그 뒤 14개가 통째로 생성되지 않았다.** 같은 이유로 `recommendation_card.rank` 도
예약어다(MySQL 8.0 윈도우 함수).

`information_schema.KEYWORDS` 로 확인한 결과 우리 스키마에 걸리는 것은 **`CALL`·`RANK` 둘**이다.

### 두 번째 — 서로게이트 PK 에 AUTO_INCREMENT 가 없었다

```
(1364, "Field 'id' doesn't have a default value")
```

숫자 PK 11개 **전부** 없어서 INSERT 마다 ID 를 직접 넣어야 했는데, 애플리케이션에 ID 를 만드는
코드가 어디에도 없다. `Column` 에 `auto_increment` 를 추가하고 서로게이트 PK **10개**에 켰다.
**`transcript_segment.segment_id` 만 예외** — [7.3절](/docs/07/) 계약상 콜 미디에이터가 정해서 보내는 값이다.

**고친 방식**: `db/generate_schema_docs.py` 의 `to_sql()` 이 테이블·컬럼·FK 식별자를 전부
백틱으로 감싸게 했다. 예약어 목록은 MySQL 버전마다 늘어나므로 **개별 예외를 두지 않았다.**
`schema.sql` 은 자동 생성물이라 직접 고치지 않고 생성기를 고쳐 재생성했다.

> 이 버그는 **스키마를 실제로 적용해보기 전에는 드러날 수 없었다.** 팀 교차검증(`db/docs/ERD.md`)도
> ERD 관점이라 잡지 못했다. 설계 문서만으로는 확인되지 않는 종류의 결함이다.

## 자격증명 (SEC-2)

compose 의 기본값은 **로컬 개발 전용**이다(`callguard`/`callguard-dev`). 운영 자격증명을 넣지 않는다.
포트·비밀번호를 바꾸고 싶으면 `infra/.env`(gitignore 대상)를 만든다. 저장소 루트 `.env` 도 그대로 gitignore 다.

## 완료 조건

`docker compose up -d` 로 16개 테이블이 전부 생성되고, `server/` 가 `mysql_configured=True` 를 인식한다.
