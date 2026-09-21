---
title: "홍보 페이지 → 상담원 화면을 같은 call_id 로 여는 진입 경로"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 6
priority: 76
date: 2026-09-21
requirement:
  - "A-3"
paths:
  - "apps/platform/*"
  - "apps/call/src/*"
---

## 무엇을

`www.solidbob.cloud`(`apps/platform`)의 버튼이 상담원 화면(`call.solidbob.cloud`)을 **같은 `call_id` 로** 열어 준다.

## 절반은 되어 있다

2026-09-21 에 로직 쪽이 들어갔다 — 두 화면이 `?call_id=` 를 읽어 같은 통화로 붙고(`lib/sharedCallId.ts`,
URL 에서만 읽고 저장하지 않는다), 상담원 화면은 **그 통화만 구독**한다(`WS /ws?call_id=`).
**남은 것은 그 주소를 만들어 열어 주는 진입 UI** 다. 화면·디자인은 그때 손대지 않았다 — 조서희 님 몫으로 남겼다.

## 완료 조건

- [ ] 홍보 페이지에서 시작한 통화가 상담원 화면에 **그 통화만** 뜬다(다른 사람의 테스트 콜이 섞이지 않는다)
- [ ] `call_id` 가 없는 주소로 들어오면 지금처럼 동작한다(회귀 없음)
- [ ] 운영 주소로 한 번 눌러 본다 — 「배포됐는데 화면에선 안 되는」 자리를 여기서 잡는다
