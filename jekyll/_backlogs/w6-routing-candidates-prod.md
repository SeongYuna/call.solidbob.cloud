---
title: "`ROUTING_CANDIDATES` 운영 값 — 근속 3년 이상 상담원 한 명을 포함해 시크릿에 넣는다"
assignee: "정성윤"
role: "ai"
status: "done"
sprint: 6
priority: 63
date: 2026-09-22
requirement:
  - "J-5"
depends_on:
  - "w7-j5-routing-caller"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

J-5 배정 판정 호출(PR #131)은 후보 목록이 비면 늘 「일반 배정으로 떨어짐」이다. 시연 대본 SYN-006 → SYN-007(같은 번호 재인입, 기대값 `routing: veteran`)이 나오려면
운영 `agent` 행에서 고른 ID 를 `call-mediator-tokens`(또는 매니페스트)에 넣어야 하고, 그중 한 명 이상이 근속 기준 이상이어야 한다.

## 완료 조건

- [x] 운영 `agent` 에서 후보 선정(페르소나 A01~A06 은 배역일 뿐 행이 없다) · 근속 값 확인
- [x] 시크릿 반영은 정성윤(SSM) — 값은 채팅에 적지 않는다
- [x] 테스트 통화 1건으로 `routing_log` 에 행 · SYN-007 이 `veteran`

근거: `w7-j5-routing-caller` 「남은 것 ①」 · `decisions/320`.

## 2026-09-22 — 장민석 진행

- 후보 선정: 페르소나 A01~A06 을 운영 행 **`demo-A01`~`demo-A06`** 으로 만든다 — `scripts/persona_sim/seed_demo_agents.py`(입사일 = 오늘 − 페르소나 근속, **시연용 값** · 발급 토큰은 즉시 폐기) · 입사일 API 는 `decisions/321`
- 근속 3년 이상: A03(7년) · A04(4년) · A06(3년)
- ⚠ **시크릿이 아니라 매니페스트에 넣었다** — `agent_id` 는 비밀이 아니다(`infra/k8s/base/call-mediator.yaml`). SSM 작업이 필요 없다
- 남은 것: 배포 뒤 관리자 토큰으로 시드 한 번(런북 12-2-c) → 테스트 통화로 `routing_log` · SYN-007 `veteran`

## 2026-09-22 — 배포

- **`0.1.35` 운영 배포됨** (PR #132 머지 07:57 → release 성공 · `/health` `version: 0.1.35` · `read_guard: open` 확인, 09-22) · 매니페스트 `ROUTING_CANDIDATES` 반영
- 남은 것: 시드 스크립트 한 번(관리자 토큰, 런북 12-2-c) → 테스트 통화로 `routing_log` · SYN-007 `veteran`

## 2026-09-22 — 정성윤이 넘겨받음 (사용자 지시)

`todo` 라 담당을 옮긴다(§4). 장민석 님이 후보 값(`demo-A01`~`A06`, 매니페스트)과 시드 스크립트(`seed_demo_agents.py`)까지 만들어 두었다 — 남은 것은 운영 확인이다.

- **운영 읽기 확인(09-22 저녁)**: 콜 미디에이터 `ROUTING_CANDIDATES` = `demo-A01..A06` ✅ · **운영 `agent` 에 `demo-%` 행 0** ❌ → 지금은 판정이 늘 「모르는 후보 → 기존 규칙으로 떨어짐」이다(`routing_log` 28행이 그 결과)
- 시드는 관리자 access token(5분, 브라우저 메모리)이 필요해 사용자가 돌린다 — 토큰은 클립보드에서 읽고 찍지 않는 래퍼를 세션 스크래치에 두었다. 드라이런 입사일: A03 2019-09-22(7년) · A04 2022-09-22 · A06 2023-09-22 — 근속 3년 기준 베테랑 후보 셋
- 다음: 시드 → SYN-006 재생(가짜 번호) → 블랙리스트 요청 → 관리자 승인 → 같은 번호로 SYN-007 → `routing_log` 에 베테랑(`demo-A03`·`A04`·`A06` 중) 배정 확인

## 2026-09-22 — 운영 확인 끝 (정성윤) → done

1. `seed_demo_agents.py` 운영 실행(관리자 토큰은 클립보드에서 읽고 찍지 않음) — `demo-A01`~`A06` 행 생성 · 입사일 A03 2019-09-22 · A04 2022-09-22 · A06 2023-09-22 등. 발급한 상담원 토큰은 스크립트가 곧바로 폐기
2. SYN-006 재생(`syn-prod-syn-006-routing2`, 가짜 번호 `01000000666`) → `routing_log` 30 **블랙리스트 아님 — 기존 배정 규칙**
3. 블랙리스트 요청(요청 5, QA상담원1 토큰 · 근거 모욕 1 · 위협 2 · 성적 3 · 21초 · 온도 미측정) → 관리자 승인
4. 같은 번호로 SYN-007 재생(`syn-prod-syn-007-routing`) → `routing_log` 31 **`is_blacklisted=true` · `assigned_agent_id=demo-A03` · 「블랙리스트 고객 — 근속 7.0년 상담사에게 배정」** · 콜 미디에이터 로그 `배정 판정 … assigned=demo-A03 blacklisted=true fell_back=false`. 두 통화 `customer_id` 같음

⚠ 매니페스트 값이 시크릿이 아니라 `call-mediator.yaml` 에 있어 「시크릿 반영」은 필요 없었다. 화면 표시는 `w6-routing-result-ui`(조서희).
⚠ 운영 블랙리스트에 SYN-006 고객 등록이 **살아 있다**(요청 5 승인) — 시연 SYN-007 재료로 둔다. 치우려면 관리자 화면에서 해제.
