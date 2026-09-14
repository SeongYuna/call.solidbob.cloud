# 304 — 고객은 발신 번호 HMAC 으로 잇고, 블랙리스트 요청자는 agent_id · 승인자는 관리자 로그인이다

**날짜**: 2026-09-14
**작성**: 장민석 (브랜치 `server`)
**관련**: `decisions/204`(블랙리스트 흐름) · `decisions/205` ③④⑤(HMAC·distress·만료) · `decisions/301`(통화 시작) · 티켓 `w4-blacklist-api` · `w4-call-list-api`

## 맥락

J(블랙리스트)와 재상담 이력은 규칙·테이블이 있는데 **저장·HTTP 를 만들 수 없었다.** 세 군데가 비어 있었다.

1. **고객을 가리킬 값이 없다.** `decisions/205` ③ 이 `customer_ref = HMAC(전화번호)` 로 정했지만 전화번호가 서버에
   들어오는 경로가 없다. `call.customer_id` 는 어떤 코드도 채우지 않고, 게다가 `VARCHAR(40)` 라 HMAC(hex 64자)이 안 들어간다
2. **결정자를 기록할 수 없다.** `blacklist_request.decided_by`·`blacklist_entry.released_by` 가 `agent` 를 참조하는데
   관리자 로그인(`admin_account`, 구글 이메일)은 `agent` 와 연결이 없다. 상담원 로그인은 아예 없다
3. **만료 기간의 근거가 없다.** `expires_at` 이 NOT NULL 인데(`decisions/205` ⑤) 얼마로 할지 정한 곳이 없다

## 결정 (사용자 선택, 2026-09-14)

| | 선택 | 대안 |
|---|---|---|
| 고객 식별 | **통화 시작 때 게이트웨이가 발신 번호를 넘기고 서버가 곧바로 HMAC** — `POST /hub/calls` 의 `caller_phone`, 게이트웨이는 `/ingest` 헤더 `X-Caller-Phone` | 블랙리스트 요청 본문에 번호(재상담 이력은 계속 막힘) · 보류 |
| 요청자 | **요청 본문의 `requested_by`(agent_id)** — `agent` 에 없으면 422 | 인증 없이 요청·승인 모두 본문 |
| 승인자 | **관리자 로그인(`require_admin`) + `admin_account.agent_id`** — 연결 안 된 관리자는 409 | `decided_by` FK 를 `admin_account` 로 바꾸기 |
| 만료 | **승인할 때 관리자가 `expires_in_days`(1~365) 필수 입력** — 코드에 기본값 없음 | 고정 90일 |

세부:

- **평문 번호는 어디에도 남지 않는다.** 서버는 받은 즉시 `HMAC-SHA256(숫자만 남긴 번호, CUSTOMER_REF_HMAC_KEY)` 로 바꾸고
  응답에는 `customer_linked` 불리언만 싣는다. 번호 형식이 틀리면 422 인데 **입력값을 되돌려 주지 않는다**(pydantic 422 와 달리).
  `+82 10 …`·`010-…`·`010…` 은 같은 고객이다
- **키가 없으면 통화는 열리고 고객만 잇지 않는다.** 평문이나 키 없는 해시로 대신하지 않는다(전화번호는 전수 대입으로 되돌려진다)
- URL 쿼리로 받지 않는다 — 접근 로그에 남는다. 과금 토큰을 헤더로만 받는 것과 같은 이유다
- 스키마: `customer.customer_id`·`call.customer_id` `VARCHAR(40)→(64)`, `admin_account.agent_id VARCHAR(20) NULL FK agent`
- 블랙리스트 요청의 **근거·고객·자막은 서버가 DB 에서 모은다** — 요청 본문은 `call_id`·`requested_by`·`reason` 뿐이다(`decisions/205`).
  사유·승인 메모·해제 사유는 저장 전에 마스킹한다. 위기 신호(distress)는 요청을 막지 않고 `has_distress` 로만 돌려준다 — 저장하지 않는다

## 근거

- 번호를 통화 시작에서 받으면 **한 번 받아 두 기능(재상담 이력·블랙리스트)이 같이 풀린다.** 요청 본문에서 받으면 상담원이 번호를
  손으로 옮겨 적어야 하고 오타가 곧 다른 고객이 된다
- 승인은 되돌리기 어려운 행위라 로그인 뒤에 둔다. 요청은 지금 서버 전체에 상담원 인증이 없으므로 다른 허브 API 와 같은 수준이다 —
  **요청은 누구나 부를 수 있다**는 한계를 남긴다(아래)
- 만료 기본값은 근거 없는 숫자다(절대 원칙 2). 관리자가 매번 정하게 하는 쪽이 「영구 표시」 도 「근거 없는 90일」 도 피한다

## ⚠ 남는 것

- **상담원 인증이 없다** — `POST /hub/blacklist-requests` 는 `agent` 에 있는 아무 ID 로나 부를 수 있다
- **`display_hint`(뒤 4자리 등)를 채우는 경로가 없다** — 늘 null. 평문 번호를 버리는 순간 만들어야 하는데 아직 저장 자리가 없다
- **반려 요청의 사유·자막을 일정 기간 뒤 비우는 작업이 없다**(`decisions/205` 「보존 기간」)
- **운영에 키를 넣어야 한다** — `CUSTOMER_REF_HMAC_KEY` 를 `.env.example`(보호 훅 때문에 사람이) · `server-env` 시크릿에. 키를 잃으면 기존 식별자를 다시 찾을 수 없다
- `admin_account.agent_id` 를 운영자가 SQL 로 채워야 승인이 된다(회원가입 화면이 없다)

## 되돌리는 법

1. `POST /hub/calls` 의 `caller_phone`·`customer_linked` 와 `CustomerRefPort`·`hmac_customer_ref_adapter.py`·`customer_ref_provider.py` 를 지운다
2. 블랙리스트 라우터 5개·인터랙터·`blacklist/adapter/outbound/postgres_blacklist_repository.py`·`blacklist_evidence_repository.py` 를 지운다
3. 스키마: `admin_account.agent_id` 를 드롭한다. `customer_id` 길이는 되돌리지 않아도 된다(넓힌 것뿐)
4. 게이트웨이: `ws_server.ts` 의 `callerPhoneOf`, `CallStartRequest.caller_phone` 을 지운다
