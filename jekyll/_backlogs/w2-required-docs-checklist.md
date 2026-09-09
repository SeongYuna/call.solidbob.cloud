---
title: "다산 필요서류 체크리스트로 F-2 패널 전용"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 5
date: 2026-08-28
paths:
  - "apps/dashboard/src/components/TermsPanel.tsx"
  - "apps/dashboard/src/types/contract.ts"
  - "apps/dashboard/src/mock/scenarios/dasan.ts"
  - "apps/dashboard/src/lib/evidenceHints.ts"
depends_on:
  - "w2-closure-evidence-hints"
---

`decisions/201` §3. 오른쪽 패널을 종결 충족요건에서 다산콜센터 **필요서류 체크리스트**로 바꾼다.
DTO(`evidence` · `missing`)는 재사용하고, `ClosureType` enum은 지우지 않는다.

## 완료 조건

- 패널 제목·칩·버튼·진행률 문구가 서류 안내 의미로 바뀐다
- mock은 POLICY 카테고리 기준 **예시** 표시. 69종 실측 목록은 지식베이스에 아직 없음
- 미안내 항목이 있으면 「안내 완료로 표시」 비활성(또는 숨김), 전부 안내되면 활성
- `typecheck` · `build` 통과
