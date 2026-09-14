---
title: "블랙리스트: 신규 vs 기존(재범) 분류 + 등록일 표시"
assignee: "조서희"
role: "app"
status: "done"
sprint: 4
priority: 4
date: 2026-09-14
paths:
  - "apps/admin/src/components/admin/EntriesTab.tsx"
---

무엇: 관리자 화면 블랙리스트 탭에 `[전체] [신규] [기존(재범)]` 필터 버튼을 추가하고,
각 등록 행에 등록일(`approved_at`, 언제 블랙컨슈머가 됐는지)을 표시한다.

기준: "기존(재범)"은 같은 고객(`customer_ref`)이 이 행 말고도 다른 등록 이력(해제된
것 포함)이 있는 경우다 — 사용자에게 재등록 여부 기준 vs 최근 등록일 기준 두 가지를
제시해 재등록 여부를 선택받았다.

완료 조건:
- [x] `isRepeatOffender()` — customer_ref 기준으로 다른 entry_id가 있으면 재범
- [x] 필터 버튼 3개(전체/신규/기존) + 각 배지에 카운트
- [x] 행마다 "신규"/"기존(재범)" 배지 + 등록일(만료일 옆에 추가)
- [x] mock 데이터에 재범 예시 1건 추가(`hmac_seed_3` — 1차 등록 해제 후 재등록)
- [x] `cd apps/admin && npm run typecheck && npm run build` 통과
- [x] 사용자가 임시 로그인 우회(`VITE_DEV_SKIP_AUTH`, 검증 후 코드에서 제거함)로
      직접 확인

근거: 사용자 요청(2026-09-14).
