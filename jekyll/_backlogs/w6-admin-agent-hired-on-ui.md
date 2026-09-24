---
title: "관리자 화면 — 상담원 입사일 입력란 (J-5 근속)"
assignee: "조서희"
role: "app"
status: "in-progress"
sprint: 6
priority: 62
date: 2026-09-22
requirement:
  - "J-5"
depends_on:
  - "w6-agent-hired-on-api"
paths:
  - "apps/admin/src/*"
---

> **장민석이 09-22 서버 API 를 만들며 요청으로 올린 티켓이다.** 담당은 «제안»이다 — 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

관리자 화면에서 상담원마다 **입사일**을 보고 고칠 수 있게 한다. 서버는 준비됐다(`decisions/321`).

- 목록: `GET /admin/agents` 응답의 각 상담원에 `hired_on`(`"YYYY-MM-DD"` 또는 `null`)이 생겼다
- 저장: `PUT /admin/agents/{agent_id}/hired-on` 본문 `{"hired_on": "2019-03-02"}` — `null` 이면 지운다
  - 404 없는 상담원 · 422 오늘보다 뒤 · 401 로그인 없음 · 응답은 목록 한 줄과 같은 모양

## 왜

J-5 베테랑 판정이 입사일로 근속을 센다. 넣는 길이 없어 운영의 모든 상담원이 근속 0년이었다 — 설정 탭의 「근속 연차 N년 이상이면 베테랑」 기준을 바꿔도 **아무도 해당하지 않는다.**

## 완료 조건

- [x] 상담원 목록(또는 토큰 발급 화면)에 입사일 표시 · 입력 · 저장
- [x] 입사일이 없으면 「근속 0년으로 계산됩니다」처럼 **없다는 사실**을 보인다 — 빈칸으로 두면 조용히 틀린다
- [x] 위험도·점수 표현 없음(부록 A-1)

## 2026-09-23 — 구현 (조서희)

`SettingsTab.tsx`(토큰 발급 화면)에 「상담원 입사일 (J-5 근속)」카드를 새로 추가했다 —
상담원 목록을 따로 만들지 않고 이미 있는 화면에 얹었다(완료 조건 1번의 "또는").

- `hubClient.ts`: `AgentSummary`·`AgentSummaryWire`에 `hiredOn`/`hired_on` 추가,
  `updateAgentHiredOn()`(`PUT /admin/agents/{id}/hired-on`) 신설. `hiredOn`이 빈 문자열이면
  `null`로 보내 서버가 지우게 한다.
- `AgentHiredOnList`(목록) + `AgentHiredOnRow`(행) — 이름은 기존 발급 목록과 같은 규칙으로
  가린다(`maskAgentName`). `date` input `max`를 오늘로 막아 422를 미리 줄인다(서버가 최종
  판정). 값이 안 바뀌었으면 저장 버튼이 비활성화된다. 카드 맨 위에 "입사일이 없으면
  **근속 0년으로 계산됩니다**"를 항상 보이는 안내로 못 박았다(빈칸 방치 방지).
  행마다 "입사일 없음 (근속 0년)" 또는 실제 날짜를 그대로 보여 — 위험도·점수 표현은
  들어갈 자리 자체가 없다.
- 새로 발급한 상담원은 `hiredOn: null`로 목록에 즉시 반영(서버 재조회 없이).

**검증은 `tsc --noEmit`·`vite build`뿐이다** — 서버 API는 `server/apps/agent_auth/tests/`에
테스트가 있는 걸 확인했지만, **화면에서 실제로 저장·404·422 오류를 받아 본 적은 없다**
(로컬에 붙는 서버가 없다). 그래서 `done`이 아니라 `in-progress`로 둔다 — 운영에서 상담원
한 명 골라 입사일을 실제로 넣어 보고 목록이 갱신되는지 확인해야 완료다.
