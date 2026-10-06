---
title: "상담원 화면 문구를 「원문 표시 · 저장 시 마스킹」 정책에 맞춘다 — 잠금 아이콘 「민감정보가 마스킹되었습니다」"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 8
priority: 7
date: 2026-10-06
requirement:
  - "C-5"
  - "SEC-1"
depends_on:
  - "w8-screen-plain-storage-encrypt"
---

> 장민석이 넘긴 일이다(2026-10-06). 서버·콜 미디에이터 쪽은 [w8-screen-plain-storage-encrypt](/backlog/w8-screen-plain-storage-encrypt/)(장민석)에서 바꿨고,
> **프론트는 고치지 않았다**(사용자 지시 — 프론트는 조서희 전담). 근거: `_project/decisions/326`(비공개).

## 무엇이 바뀌었나

콜 미디에이터 `0.2.14` 부터 `/ws` 의 `transcript.text` 가 **원문**이다. `masked` 구간은 그대로 오고,
`MaskedText` 가 그 자리 글자를 `<mark>` 로 그리므로 화면은 「원문 + 개인정보 자리 강조」가 된다(코드 수정 없이 동작).
DB 저장 쪽은 지금처럼 마스킹본이다 — 지난 통화 보기(`GET /hub/calls/{id}/transcript`)는 여전히 마스킹본을 준다.

## 정할 것 — 문구가 옛 정책 그대로다

- [ ] 자막 잠금 아이콘 title·aria-label 「민감정보가 마스킹되었습니다」(`TranscriptPanel.tsx`) — 원문이 보이는데 이 문구가 뜬다
- [ ] `MaskedText.tsx`·`maskSensitiveText.ts` 주석 「실서버는 원문을 절대 주지 않는다」
- [ ] `.claude/rules/call.md §2`
- [ ] 문구를 바꿀지 그대로 둘지는 프론트 판단이다 — 「저장 시 마스킹됨」처럼 바꿀 수도 있다
