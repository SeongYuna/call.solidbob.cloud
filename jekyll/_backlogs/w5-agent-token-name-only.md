---
title: "상담원 토큰 발급 — 이름만으로 발급(없으면 자동 등록)"
assignee: "조서희"
role: "app"
status: "done"
sprint: 5
priority: 20
date: 2026-09-21
requirement:
  - "J-1"
depends_on:
  - "w4-agent-token"
paths:
  - "apps/admin/src/components/admin/SettingsTab.tsx"
  - "server/apps/agent_auth/*"
---

## 무엇을

`w4-agent-token`에서 "ID 대신 이름으로 고른다"고 했지만, `agent` 테이블에 애초에 행이
없어(상담원을 만드는 화면·API가 없음) `GET /admin/agents`가 빈 목록을 돌려주고 화면이
"agent.agent_id 직접 입력"으로 빠졌다. 관리자가 거기에 상담원 이름("최효원")을 치면
`agent_id`로 오인돼 FK 위반 404("상담원이 없습니다: 최효원")가 났다 — 실사용 중 발견.

`decisions/406`으로 발급 대상을 **이름으로만** 받게 한다 — 서버가 같은 이름의 상담원을
찾아 쓰거나, 없으면 그 자리에서 새로 만든다. 상담원 관리 화면은 아직 안 만든다(테스트 단계).

## 완료 조건

- [x] `AgentDirectoryPort.resolve_or_create` — 이름/ID로 찾고 없으면 생성
- [x] `IssueAgentTokenInteractor` 가 발급 전에 상담원을 확보하도록 배선
- [x] `server/apps/agent_auth` 유닛 24건 통과(신규: 이름 재사용·자동 생성·라우터 201)
- [x] Postgres 통합 테스트 추가(`test_agent_directory_repository.py`, 미실행 — 로컬에 DB 없음)
- [x] 화면: 입력창 하나(이름) + 있으면 `<datalist>` 자동완성, "agent_id 직접 입력" 문구 제거
- [x] `apps/admin` `tsc --noEmit` 통과
- [ ] 운영 배포 후 실제 화면에서 재확인 (다음 세션)
