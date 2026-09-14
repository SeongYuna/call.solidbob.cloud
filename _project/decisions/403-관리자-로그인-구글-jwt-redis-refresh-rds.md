# 403 — 관리자 로그인: 구글 OAuth만, JWT access(Redis) + refresh(RDS) 회전

**날짜**: 2026-09-14
**상태**: 확정

## 맥락

`apps/admin`(관리자 화면)에는 로그인 자체가 없었다 — `mock/adminAuth.ts`가 고정 문자열
"관리자"를 돌려주는 자리채움이었고(주석: "계정 API가 오면 이 값만 서버 응답으로 바꾼다"),
`server/`에는 인증 코드가 전혀 없었다(Google OAuth·JWT·Redis 전부 0줄).

사용자 지시: 회원가입 화면은 만들지 않는다. 로그인은 구글 계정 하나뿐이다. access token은
"테스트만 진행"할 것이라 Redis에 5분으로 짧게 잡는다. refresh token은 RDS(PostgreSQL)로
가고 10분 만료다.

## 결정

1. **회원가입 없음 — 허용 목록은 `admin_account`(RDS) 테이블.** 구글 인증을 통과해도
   이 테이블에 이메일이 없으면 403이다. 행 추가·삭제(관리자 등록·해제)는 앱에 쓰기 경로를
   두지 않고 운영자가 직접 SQL로 한다. `agent.role='admin'`(J-4 승인 권한)과는 다른
   개념으로 분리했다 — 그쪽은 상담원 마스터의 역할 구분이고 이것은 로그인 자격이다.
2. **구글 로그인은 클라이언트 사이드(Google Identity Services)로 간다.** 프론트가
   `accounts.google.com/gsi/client` 버튼으로 id_token을 받아 `POST /admin/auth/google`에
   실어 보내고, 서버가 `google-auth` 라이브러리로 서명·issuer·audience·만료를 검증한다.
   서버 사이드 Authorization Code 리다이렉트(별도 콜백 라우트·client_secret 보관)보다
   구현이 단순해 이쪽을 택했다.
3. **access token = JWT(HS256) + Redis 세션, 5분.** 서명 검증만으로는 로그아웃이 exp
   전에 반영되지 않는다 — 그래서 발급마다 Redis에 `jti`를 TTL=만료와 같게 심고, 검증
   시 서명 다음에 그 세션 존재까지 함께 본다. 로그아웃은 Redis 키를 지우는 것뿐이다.
4. **refresh token = 불투명 랜덤 문자열 + `admin_refresh_token`(RDS), 10분, 회전(rotation).**
   원문은 응답으로 한 번만 나가고 저장하지 않는다 — SHA-256 해시만 둔다(SEC-1과 같은
   원칙: 탈취되는 값을 그대로 저장하지 않는다). refresh 할 때마다 기존 행을
   `revoked_at`으로 무효화하고 새 행을 만든다 — 지우지 않는다(절대 원칙 8, 탈취 흔적
   추적용). 재사용 시도가 오면(이미 회전된 토큰) 실패하므로 탈취 재사용이 드러난다.
5. **Redis는 테스트 스코프다 — 운영(k3s) 배포 매니페스트를 만들지 않았다.** 로컬은
   `docker run redis:7-alpine` 한 줄(`infra/README.md` "로컬 개발" 절과 같은 패턴).
   **AWS ElastiCache(관리형 Redis)는 만들지 않는다** — `infra/CLAUDE.md` §1-2가 이미
   금지하는 항목이고, 이번 결정도 그 경계를 넘지 않는다. 운영에 필요해지면 그때
   별도로 정한다.
6. **`server/apps/admin_auth/` 신설 — hub 포트를 구현하는 스포크가 아니라 hub와 같은
   레벨의 독립 슬라이스다.** 관리자 로그인은 통화 파이프라인과 무관해 hub 계약에
   얹을 이유가 없었다. `.importlinter`에 `admin_auth`를 `hub`·`masking`·`closure_gate`·
   `blacklist`와 같은 계약(클린 아키텍처·`ai` 비의존·프레임워크 격리)으로 추가했다.
7. **설정이 없으면 조용히 통과시키지 않고 RuntimeError로 막는다.** hub의 다른
   프로바이더들(예: `call_record_provider`)은 PostgreSQL 미설정 시 Log 어댑터로
   대체해 "일단 뜨게" 한다 — 인증에는 그 패턴을 쓰지 않는다. 가짜 구현이 곧 누구나
   로그인되는 구멍이기 때문이다.
8. **응답 스키마 숫자 필드는 `StrField`로 문자열화한다.** 2026-09-10 조서희·장민석
   합의(7.3절 인터페이스 계약)가 모든 HTTP 응답에 적용되고, `test_segment_id_contract.py`가
   전체 OpenAPI 스키마를 훑어 이를 강제한다 — `TokenPairResponse`의 만료 초 필드도
   대상이다.
9. **DB 스키마는 `db/generate_schema_docs.py`의 `TABLES`에서만 고친다.** `db/schema.sql`은
   자동 생성 파일이라 직접 손대지 않는다(파일 상단 경고). `admin_account`·
   `admin_refresh_token` 두 테이블을 추가하고 재생성했다.

## 근거

- 회원가입을 만들지 않은 것은 사용자 명시 지시다 — 관리자는 소수이고 사전에 아는
  사람들이라 셀프서비스 가입 흐름 자체가 필요 없다.
- access/refresh 만료를 각각 5분/10분으로 짧게 잡은 것도 사용자 지시("테스트만
  진행")다 — 운영 값으로 굳힌 것이 아니다. 나중에 실제 운영에 올릴 때는 이 값과
  Redis 배포 방식(위 5번) 둘 다 다시 정해야 한다.
- refresh token을 해시로만 저장하는 것과 access token 세션을 Redis로 즉시 무효화
  가능하게 만든 것은 SEC-1·SEC-2가 이미 요구하는 "탈취되는 값을 그대로 두지
  않는다"는 원칙을 인증에도 그대로 적용한 것이다.

## 되돌리는 법

- `server/apps/admin_auth/` 디렉터리를 통째로 지운다. `server/main.py`의
  `auth_router` import·`include_router` 두 줄을 뺀다.
- `server/.importlinter`에서 `admin_auth` 4곳(root_packages·계약 1 containers·
  계약 2 source_modules·계약 3 source_modules)을 뺀다.
- `server/core/config.py`·`.env.example`의 `GOOGLE_OAUTH_CLIENT_ID`·`ADMIN_JWT_SECRET`·
  `ADMIN_ACCESS_TOKEN_TTL_SECONDS`·`ADMIN_REFRESH_TOKEN_TTL_SECONDS`·`REDIS_URL`을 뺀다.
- `server/requirements.txt`에서 `PyJWT`·`redis`·`google-auth` 세 줄을 뺀다.
- `db/generate_schema_docs.py`의 `TABLES`에서 `admin_account`·`admin_refresh_token`
  두 테이블을 빼고 재생성한다(운영 RDS에 이미 적용했다면 `DROP TABLE`도 별도로 필요).
- `apps/admin/src/lib/auth/`·`src/components/AdminLoginScreen.tsx`를 지우고
  `App.tsx`를 로그인 게이트 이전 상태로 되돌린다(`AdminPanel`을 바로 렌더링).

## 승인

사용자 직접 지시로 진행 (2026-09-14).
