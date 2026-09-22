---
title: "컴플라이언스 방송 켜기 — compliance + 검사 실패 신호"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 6
priority: 64
date: 2026-09-22
requirement:
  - "C-1"
  - "C-4"
depends_on:
  - "w6-compliance-spoke"
paths:
  - "services/call-mediator/src/app/call_registry.ts"
  - "services/call-mediator/src/app/ports.ts"
  - "services/call-mediator/src/main.ts"
---

## 무엇을

콜 미디에이터의 `announceCompliance` 를 켠다. 검사·저장은 09-18 부터 운영에서 돌았고(`0.2.1`), 대시보드 파서가
main 에 들어와(`349b18b`, 조서희 09-21) 켤 조건이 찼다 — **파서 먼저, 방송 나중** 순서 그대로.

## 왜 신호가 하나 더 필요한가

조서희 님 요청(09-22): 위반 없음과 **검사 실패**가 프론트에서 똑같이 「메시지 없음」이라 구분이 안 됐다.
`w6-compliance-alert-ui` 완료 조건의 「스포크가 501 이면 탐지 없음이 아니라 **탐지 미동작**으로」를 화면이
만들 재료가 없었다. 그래서 검사가 실패한 상담원 발화마다 `compliance_unavailable` 을 보낸다 —
`{call_id, segment_id, status}`, `status` 는 HTTP 상태 문자열(`"501"` 스포크 없음 · `"404"` 호출 순서 · `"연결 실패"`).
위반 없음은 여전히 침묵이다(부록 A-1 — 「안전함」을 만들지 않는다).

## 완료 조건

- [x] `compliance_unavailable` 메시지 정의 + 실패 시 발행(스위치는 `announceCompliance` 공용) — 테스트 135 통과
- [x] `main.ts` `announceCompliance: true` · `kustomization.yaml` call-mediator `0.2.3`
- [ ] 릴리스 뒤 운영 `/call-mediator/health` ok · 실통화(또는 재생기)에서 상담원 「무조건 됩니다」 에 `compliance` 도착 확인
- [ ] 조서희 님 파서에 `compliance_unavailable` 타입 추가(그전까지는 `onError` 로 떨어져 배너만 뜨고 화면은 안 깨진다)
