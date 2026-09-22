# 314 — 관리자마다 전용 `agent` 행을 붙여 블랙리스트 결정을 기록한다 (승인·해제 409 해소)

**날짜**: 2026-09-22
**작성**: 장민석 (브랜치 `server`)
**관련**: `decisions/304`(처리자를 상담원 마스터 ID 로 남긴다) · `406`(상담원을 이름으로 찾거나 만든다) · 티켓 `w6-admin-agent-mapping` · 미결 「`admin_account.agent_id` 를 채워야 블랙리스트 승인·해제가 된다」

## 맥락

`blacklist_request.decided_by`·`blacklist_entry.released_by`·만료 변경 `changed_by` 가 `agent` 를 참조한다(`304`).
로그인한 관리자의 `admin_account.agent_id` 가 비어 있으면 **409** 였고 회원가입 화면이 없어 운영자가 SQL 로 채워야 했다.
09-15 운영 첫 로그인부터 이 값은 NULL 이라 **운영의 승인·해제·만료 변경이 전부 막혀 있었다.** 시연의 J 블록(요청 → 승인)이 여기서 막힌다.

## 선택지

| 후보 | 판단 |
|---|---|
| **① 관리자마다 `agent` 행을 만들어 잇는다** | 사람 = 행 하나, 누가 눌렀는지가 행 단위로 남는다. `agent.role` 에 이미 `'admin'` 값이 있어 **스키마 변경이 없다** |
| ② 공용 행 하나(`admin-console`) | 가장 단순하지만 누가 눌렀는지가 DB 에서 사라진다 |
| ③ `decided_by` 가 `admin_account` 를 가리키게 스키마 변경 | 마이그레이션 · 되돌리기 어렵다 |

## 결정 (사용자 선택, 2026-09-22) — ①

- 처음 결정할 때(`get_blacklist_decider`) 연결이 없으면 **`admin-<admin_account.id>`, `role='admin'`** 행을 찾거나 만들고(`ON CONFLICT DO NOTHING`)
  `admin_account.agent_id` 가 **비어 있을 때만** 채운다(`COALESCE` — 동시에 두 번 눌러도 먼저 쓴 값이 이긴다). 이미 연결된 관리자는 그 값 그대로
- 이름은 구글 프로필 이름(30자로 자름), 없으면 ID. **이메일을 이름 자리에 쓰지 않는다**
- `406` 의 `resolve_or_create` 를 **쓰지 않는다** — 이름으로도 찾기 때문에, 관리자와 이름이 같은 상담원이 있으면 관리자의 결정이
  그 상담원 이름으로 기록된다. 그래서 ID 로만 찾는 `AgentDirectoryPort.ensure_admin` 을 따로 뒀다
- 반대 방향도 막는다 — 상담원 목록(`GET /admin/agents`)과 이름 찾기는 `role='agent'` 만 본다. 관리자 행이 토큰 발급 후보로 섞이지 않고,
  관리자 행 ID 로 토큰을 발급하려 하면 빌려주지 않고 `UnknownAgentError`(404)다
- 위치: 유스케이스는 `agent_auth`(`AdminAgentLinkInteractor`) — `agent_auth` 가 이미 `admin_auth` 를 알고 반대는 모른다. `admin_account` 쓰기는 `AdminAccountPort.link_agent` 한 칸뿐이다

## 근거

- 감사 추적은 사람 단위여야 한다(②를 버린 이유). 스키마를 안 바꾸고 된다(③을 버린 이유)
- 운영자가 SQL 을 치는 단계를 없앤다 — 운영에서 409 가 3주 가까이 남아 있던 원인이 「누가 언제 채울지」가 정해지지 않은 것이었다

## ⚠ 남는 것

- 운영에 이미 `admin_account.agent_id` 를 손으로 채운 행이 있으면 그 값을 그대로 쓴다(덮어쓰지 않는다) — 09-22 운영 값은 NULL 로 알려져 있다
- 관리자 행 ID 와 같은 이름으로 토큰을 발급하면 404 다(`admin-1` 이라는 상담원 이름) — 드물어서 그대로 둔다

## 되돌리는 법

`hub/dependencies/blacklist_decider_provider.py` 를 409 버전으로 되돌린다(git). 이미 생긴 `admin-*` 행과 연결은 남아도 해가 없다 — 지우려면 `admin_account.agent_id` 를 NULL 로 되돌린 뒤 결정 기록이 참조하지 않는 행만 지운다.
