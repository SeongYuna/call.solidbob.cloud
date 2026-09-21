---
title: "admin_account.agent_id 매핑 — 블랙리스트 승인·해제가 운영에서 409 다"
assignee: "장민석"
role: "ai"
status: "todo"
sprint: 6
priority: 75
date: 2026-09-21
requirement:
  - "J-2"
paths:
  - "server/apps/blacklist/*"
  - "server/apps/admin_auth/*"
---

## 무엇을

운영 `admin_account` 행의 `agent_id` 가 **NULL** 이라 블랙리스트 **승인 · 해제 · 만료 변경이 전부 409** 다
(`decisions/304` — 처리자를 상담원 ID 로 남기는 설계). 이것을 푼다.

## 왜 지금

09-15 에 관리자 로그인이 운영에서 성공한 뒤로 **계속 이 상태다.** 선택지 셋이 로그에 적혀 있고 아직 고르지 않았다.
[시연](/backlog/w8-demo-rehearsal/)에서 J 블록(전환 요청 → 관리자 승인)을 보이려면 여기서 막힌다.

## 같이 볼 것

`decisions/406` 으로 **상담원을 이름으로 만드는 경로**가 생겼다(09-21). 관리자에게 `agent` 행을 붙이는
방법이 그 경로와 겹치는지 먼저 본다 — 두 벌을 만들지 않는다.

## 완료 조건

- [ ] 방식을 고르고 결정 기록(`3xx`)으로 남긴다
- [ ] 운영에서 승인 1건 · 해제 1건이 200 이고 `blacklist_entry` 에 처리자가 남는다
- [ ] 매핑이 없는 관리자가 눌렀을 때의 메시지가 「409」가 아니라 **무엇을 해야 하는지**를 말한다
