---
title: "충족요건 항목별 안내·조항"
assignee: "조서희"
role: "app"
status: "done"
sprint: 2
priority: 6
date: 2026-08-28
paths:
  - "apps/dashboard/src/lib/evidenceHints.ts"
  - "apps/dashboard/src/components/TermsPanel.tsx"
  - "apps/dashboard/src/index.css"
---

「충족요건」 탭에서 미충족 evidence마다 상담원이 지금 할 말과 근거 조항을 붙인다.
판정 규칙은 그대로 두고, `closure_type` 없는 카드는 목록에서 뺀다.

## 완료 조건

- 문구·조항은 finance/shopping POLICY·MANUAL 표에서 옮긴다. 없는 필드는 「확인 필요」, 조항 생략
- 충족(✓) 항목에는 권장 문구를 내지 않는다
- 연결된 카드가 없으면 패널 안내 한 줄, 여러 건이면 전부 표시
- `typecheck` · `build` 통과
