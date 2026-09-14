# 108. 운영 DB 를 Neon(임시)에서 RDS 로 옮긴다

- 날짜: 2026-09-11
- 작성: 정성윤
- 관련: `018`(PostgreSQL 전환) · `105`(한 컨테이너·한 도메인) · `107`(k3s 배포) · `301`(통화 시작 · `DATABASE_URL` 수정)
  · 티켓 `w4-rds-prod-db` · `w3-aws-deploy` · `w4-schema-qa-followup` · 런북 `docs/infra-runbook.md` 6·12·17·19장

## 맥락

**설계는 처음부터 RDS 였다.** `w3-aws-deploy`(09-03) · 런북 6장 · `infra/k8s/base/server.yaml` 주석
(「RDS 를 독립적으로 쓴다」)이 전부 RDS 를 전제한다. RDS 를 고른 이유는 **백업 하나**였다 —
전사 데이터는 지우면 복구 경로가 없다(`2026-09-03-01-seongyun`).

**그런데 09-08 EC2 배포 때 RDS 를 만들지 않고, 운영 시크릿 `server-env` 의 `DATABASE_URL` 에
Neon(`ap-southeast-1`, 싱가포르)을 임시로 넣었다.** 이 선택은 어디에도 기록되지 않았다.
`POSTGRES_HOST` 는 빈 값으로 들어갔다.

**2026-09-11 확인한 것** (1차 자료 — 운영 파드 로그 · 시크릿 키 · AWS CLI):

| 확인 | 결과 |
|---|---|
| `kubectl -n callguard logs deploy/callguard-server` | `psycopg.OperationalError: connection to server on socket "/var/run/postgresql/.s.PGSQL.5432" failed` |
| `server-env` 의 `POSTGRES_HOST` | 빈 값 |
| `server-env` 의 `DATABASE_URL` | Neon `…-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb` |
| `aws rds describe-db-instances` (서울) | **빈 결과 — RDS 가 없다** |
| 운영 `GET /hub/knowledge-gaps` | 500 |

**즉 운영 DB 연결은 09-08 배포 이후 한 번도 성공하지 않았다.** 원인은 두 가지가 겹친 것이다.

1. 운영 이미지 `0.1.1` 의 연결 코드(`connection.py`, `7de863f`)는 `POSTGRES_*` 만 읽고
   `DATABASE_URL` 을 무시한다. 그런데 `/health` 의 `postgres_configured` 는 `DATABASE_URL` 이
   있으면 true 다 — 설정 코드와 연결 코드가 서로 다른 규칙을 따랐다.
2. 운영 시크릿의 `POSTGRES_HOST` 가 비어 있어, 연결 코드가 호스트 없이 libpq 기본값(로컬 유닉스
   소켓)으로 갔다.

장민석이 09-10 `7396275` 에서 1번을 고쳤으나 `newTag` 가 `0.1.1` 그대로라 운영에 가지 않았다.
**태그만 올리면 이번에는 운영이 Neon 에 붙는다** — 아래 문제를 안은 채로.

| # | Neon 을 운영으로 쓸 때의 문제 |
|---|---|
| ① | **개발과 섞인다.** 같은 Neon 호스트가 정성윤 로컬 `.env` 에도 있고, 장민석의 로컬 서버와 **인증 없는 ngrok 터널**도 Neon 에 쓴다(`301`, `2026-09-10-01-minseok`). 장민석 쪽이 같은 엔드포인트인지는 확인하지 않았다 |
| ② | **리전이 다르다.** EC2 는 서울, Neon 은 싱가포르다. 쿼리마다 리전 간 왕복이 붙어 B 의 내부 처리 p95 측정에 섞인다(미측정) |
| ③ | **백업.** RDS 를 고른 유일한 이유가 백업이다. Neon 쪽 보존 정책은 확인하지 않았다 |
| ④ | **노출.** Neon 엔드포인트는 인터넷에 열려 있다. RDS 는 퍼블릭 액세스 없이 EC2 보안 그룹만 받는다(SEC-1) |
| ⑤ | **스키마 판.** 09-10 장민석 대조에서 Neon DDL 은 rev.5 이전이다 |

## 선택지

| | 내용 | 문제 |
|---|---|---|
| A | Neon 을 그대로 운영으로 쓴다 | 위 ①~⑤ 전부 |
| B | Neon 안에 운영 전용 DB(브랜치)를 따로 둔다 | 가장 빠르다. ①만 풀리고 ②③④ 는 남는다 |
| **C** | **RDS PostgreSQL 17, db.t4g.micro, 단일 AZ (런북 6장 원안)** | 생성 약 10분 + 스키마 적용. 비용은 런북 0장 근사치 6주 ≈ $21 |
| D | 클러스터 안에 PostgreSQL StatefulSet | 백업을 직접 만들어야 한다. 데이터가 EC2 디스크 생명주기에 묶인다 |

## 결정

**C. RDS 를 만들고 운영 DB 를 옮긴다.** 세션 중 「B 가 가장 빠르다」는 권고가 있었으나,
①~④ 를 한 번에 푸는 쪽으로 정했다(정성윤 결정). Neon 은 **개발용으로 남긴다**.

1. **이름은 운영 실물(`callguard`)에 맞춘다.** 런북은 `assist-*` 를 쓰지만 운영 클러스터는 이미
   네임스페이스 `callguard` · 디플로이먼트 `callguard-server` · 시크릿 `server-env` 다.
   식별자 `callguard-pg` · 마스터 사용자 `callguard` · 초기 DB `callguard` ·
   DB 보안 그룹 `callguard-db`. **런북과 다른 곳이므로 런북을 따로 고친다**(남은 것).

   > **정정 (2026-09-11, 같은 날).** 위 1번은 **틀린 전제**였다 — `callguard` 는 **k8s 오브젝트** 이름이고,
   > AWS 자원은 원안 `assist-*` 가 실물이다(EC2 보안 그룹 `assist-web`, 콘솔 확인). 실제로 만든 RDS 는
   > `aws rds describe-db-instances` 로 확인했다: **식별자 `callguard-pg` · 마스터 사용자 `callguard` ·
   > 초기 DB `assist`**. 그래서 연결 문자열은 `postgresql://callguard:<암호>@<엔드포인트>:5432/assist?sslmode=require`
   > 이고 `POSTGRES_DB_NAME=assist` 다. DB 보안 그룹도 원안 이름 **`assist-db`** 다(`describe-security-groups` 로
   > 확인 — 5432 인바운드 소스가 운영 EC2 에 붙은 `assist-web` 이다. 두 ID 를 대조해 확인했다).
   > 원문은 결정 당시의 판단이라 지우지 않는다(절대 원칙 8).
   > 런북 6·12-2·17 · `secret.example.yaml` · 티켓 `w4-rds-prod-db` 를 이 값으로 고쳤다.
2. **시크릿에는 `DATABASE_URL` 과 `POSTGRES_*` 를 둘 다 RDS 값으로 넣는다.** 옛 이미지(`0.1.1`,
   `POSTGRES_*` 만 읽음)와 새 이미지(`DATABASE_URL` 우선) **어느 쪽이 떠 있어도 같은 DB 에 붙는다.**
   이번 사고가 「두 규칙이 서로 다른 값을 보고 있었다」였으므로 두 값을 같게 만든다.
   `DATABASE_URL` 에는 `?sslmode=require` 를 붙인다.
3. **`server-env` 에서 `AWS_ACCESS_KEY_ID`·`AWS_SECRET_ACCESS_KEY` 를 뺀다.** 서버 코드는 읽지 않는다
   (`server/core/config.py` 에 AWS 항목 없음). 쓰지 않는 정적 자격증명이 파드에 있을 이유가 없다.
4. **스키마는 지금의 `db/schema.sql`(22 테이블)을 적용한다.** ⚠ 전사 저장 어댑터가 이 스키마와
   어긋나 있다(`w4-schema-qa-followup` ① — `ON CONFLICT ("segment_id")`, `masking_event` 에 `call_id` 누락).
   **읽기는 RDS 로 바로 살아나지만, 전사 저장은 그 수정 + 이미지 `0.1.2` 배포 전까지 실패한다.**
   RDS 문제가 아니라 어댑터 문제다.
5. **Neon 에서 데이터를 옮기지 않는다.** 운영이 Neon 에 연결된 적이 없으므로(위 로그) 옮길 운영
   데이터가 없다. Neon 에 있는 것은 개발·터널 테스트 데이터다.
6. **검증은 `/health` 가 아니라 실제 읽기로 한다.** `/health` 의 `postgres_configured` 는 설정이
   있는지만 센다 — 이번 사고를 사흘간 가린 것이 그 값이었다. 운영 `GET /hub/knowledge-gaps` 200 과
   RDS 에 직접 `\dt` 를 기준으로 삼는다.

## 근거

- **백업(③)이 RDS 를 고른 원래 이유이고, 그 이유는 바뀌지 않았다.** 자동 백업 7일.
- **같은 리전(②).** EC2 와 같은 서울 리전·같은 VPC 라 리전 간 왕복이 없다.
- **비공개(④).** 퍼블릭 액세스 「아니요」 + 인바운드 5432 는 EC2 보안 그룹에서만. 전사 데이터(SEC-1)가
  인터넷에 열린 엔드포인트에 있지 않게 된다. k3s 파드에서 나가는 트래픽은 노드 IP 로 바뀌어(SNAT)
  EC2 네트워크 인터페이스로 나가므로, 보안 그룹을 소스로 한 규칙이 그대로 맞는다.
- **분리(①).** 운영과 개발·터널이 같은 DB 를 쓰지 않는다.

## 되돌리는 법

- **Neon 으로 되돌리기**: `server-env` 의 `DATABASE_URL`·`POSTGRES_*` 를 이전 값으로 되돌리고
  `kubectl -n callguard rollout restart deploy/callguard-server`. 이전 시크릿은 교체 직전에
  `server-env.backup.yaml` 로 떠 둔다(인스턴스 안, 권한 600, 확인 뒤 삭제).
- **RDS 를 없애기**: 삭제 방지를 먼저 끄고 삭제한다. 최종 스냅샷을 남길지 고른다.
- ⚠ **RDS 는 「중지」해도 7일 뒤 자동으로 다시 켜진다**(AWS 동작). 오래 쉬게 할 거면 스냅샷 후 삭제한다.
  EC2 자동 중지 cron(런북 21-1)은 RDS 를 멈추지 않는다 — RDS 는 상시 과금이다.

## 남은 것

- **`w4-schema-qa-followup` ① 을 먼저 고친 뒤 `newTag` 를 `0.1.2` 로 올린다.** 순서가 바뀌면 새 이미지가
  RDS 의 새 스키마에서 전사 저장을 깨뜨린다.
- 런북 6장(이름) · 12-2(실제 시크릿은 `server-env`, `--from-env-file`) · 17장(인스턴스에 저장소 클론이 없다 —
  `raw.githubusercontent.com` 에서 받는다) · 19장(쓰기 확인 추가)을 실물에 맞춰 고친다.
- `/health` 가 DB 에 실제로 `SELECT 1` 을 보내게 할지 — 설정 여부와 연결 여부를 구분하려면 필요하다.
- `newTag` 를 안 올린 머지를 머지 후가 아니라 PR 단계에서 막을지.
