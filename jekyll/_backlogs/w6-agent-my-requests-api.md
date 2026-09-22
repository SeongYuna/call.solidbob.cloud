---
title: "상담원 「내 블랙리스트 요청」 조회 — 반려 사유를 요청자가 본다"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 6
priority: 78
date: 2026-09-22
requirement:
  - "J-2"
  - "J-4"
paths:
  - "server/apps/hub/adapter/inbound/api/v1/my_blacklist_request_list_router.py"
---

## 무엇을

`GET /hub/blacklist-requests/mine` — 상담원 토큰으로 **자기가 올린 요청**과 그 결과(상태·반려 사유)를 본다.

## 왜

`decisions/316` 으로 반려 사유가 저장되지만 **요청한 상담원이 볼 경로가 없다**(미결 「상담원이 반려 사유를 볼 경로가 없다」).
관리자 화면에만 보이면 같은 요청이 반복된다.

## 완료 조건

- [ ] 토큰 없음·틀림 401 · 남의 요청은 안 보인다(요청자는 토큰에서만)
- [ ] 응답에 고객 식별자(HMAC)·결정한 관리자 ID 를 싣지 않는다 — 상담원에게 필요 없는 것을 내보내지 않는다
- [ ] 화면 연결은 조서희 님 — 미결로 넘긴다

---

> **2026-09-22 장민석 — 했다.** `GET /hub/blacklist-requests/mine`(상담원 토큰). 요청자는 토큰에서만 — 쿼리로 남의 ID 를 실어도 무시된다(테스트).
> 응답은 요청 번호·통화·사유·상태·시각·**반려 사유**뿐이고 HMAC·결정자·근거·자막은 싣지 않는다(테스트). 저장소 `list_requests` 에 `requested_by` 필터(실제 DB 테스트).
> 화면 연결은 조서희 님 — 미결로 넘겼다.
