---
title: "C-6 베타 — 폭언 감지 시 단계 판정(1차·2차 안내·종료 권고) + call_guard_intervention 메시지"
assignee: "류준"
role: "ai"
status: "done"
sprint: 8
priority: 6
date: 2026-10-06
requirement:
  - "C-6"
paths:
  - "services/call-mediator/src/domain/call_guard_intervention.ts"
  - "services/call-mediator/src/app/call_registry.ts"
  - "services/call-mediator/src/app/ports.ts"
  - "services/call-mediator/src/config.ts"
---

> 설계·근거 `_project/decisions/221`. 화면은 조서희(`w8-c6-intervention-overlay-ui`), 고객 쪽 송출은 정성윤 조사(`w8-c6-intervention-telephony`).
> **베타 — 기본 꺼짐**(`CALL_GUARD_INTERVENTION_BETA=1` 일 때만). 운영 매니페스트에 넣지 않는다.

## 무엇을

고객 발화에서 폭언(`insult`·`threat`·`sexual`)이 잡히면 통화 안 횟수로 단계를 정한다(매뉴얼 5.1·5.2 를 옮긴 규칙):
1회 `warning`(일시정지 + 「계속되면 종료될 수 있다」 고정 안내) → 2회 `final_warning` → 그 뒤 `end_suggested`(권고만, **시스템은 끊지 않는다**).
`threat`·`sexual` 은 1차 안내 뒤 곧바로 `end_suggested`. `distress` 는 들어가지 않는다(5.4).

## 완료 조건

- 단계 판정 순수 함수 + 단위 테스트(횟수·갈래·distress 제외·발화당 1회)
- 스위치 꺼짐이면 메시지가 하나도 나가지 않는다 — 테스트로 고정
- 켜짐이면 `call_guard` 다음에 `call_guard_intervention`(값은 전부 문자열)이 나간다
- 미디에이터 typecheck·테스트 통과

## 베타를 벗어나는 조건 (`221` 5절)

탐지는 지금 규칙(어휘 사전)이다. 실제 고객 데이터는 개인정보 때문에 모으기 어려워 **분류기 학습·측정이 불가**하다.
데이터를 얻게 되면 비속어·욕설 분류기를 학습해(학습용·측정용 분리) `CallGuardPort` 를 갈아끼우고, 하네스로 잰 숫자로 새 결정을 써서 운영에 켠다.
