---
title: "`ROUTING_CANDIDATES` 운영 값 — 근속 3년 이상 상담원 한 명을 포함해 시크릿에 넣는다"
assignee: "장민석"
role: "ai"
status: "in-progress"
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

- [ ] 운영 `agent` 에서 후보 선정(페르소나 A01~A06 은 배역일 뿐 행이 없다) · 근속 값 확인
- [ ] 시크릿 반영은 정성윤(SSM) — 값은 채팅에 적지 않는다
- [ ] 테스트 통화 1건으로 `routing_log` 에 행 · SYN-007 이 `veteran`

근거: `w7-j5-routing-caller` 「남은 것 ①」 · `decisions/320`.

## 2026-09-22 — 장민석 진행

- 후보 선정: 페르소나 A01~A06 을 운영 행 **`demo-A01`~`demo-A06`** 으로 만든다 — `scripts/persona_sim/seed_demo_agents.py`(입사일 = 오늘 − 페르소나 근속, **시연용 값** · 발급 토큰은 즉시 폐기) · 입사일 API 는 `decisions/321`
- 근속 3년 이상: A03(7년) · A04(4년) · A06(3년)
- ⚠ **시크릿이 아니라 매니페스트에 넣었다** — `agent_id` 는 비밀이 아니다(`infra/k8s/base/call-mediator.yaml`). SSM 작업이 필요 없다
- 남은 것: 배포 뒤 관리자 토큰으로 시드 한 번(런북 12-2-c) → 테스트 통화로 `routing_log` · SYN-007 `veteran`
