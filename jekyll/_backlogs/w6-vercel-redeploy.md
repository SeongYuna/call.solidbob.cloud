---
title: "프론트 재배포 — Vercel 하루 배포 한도에 걸린 09-22 변경분"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 5
priority: 55
date: 2026-09-22
---

> **정성윤이 09-22 오늘 진행 기록·미결 항목을 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 에 PR 이 많아 Vercel 계정 하루 배포 한도(「Deployment rate limited — retry in 24 hours」)에 걸렸다.
조서희 님 PR #124·#126 의 수정(합성 통화 중 모달 숨김 · 고객 해시 감춤 · 온도 「미측정」 · 진입 경로 자동화 · 이력 화면 둘)이 **운영 화면에 안 나갔다.**
`call.solidbob.cloud` 번들에는 09-21 파서까지만 들어 있다(09-22 확인).

## 어떻게

- 09-23 한도가 풀리면 세 프로젝트를 대시보드에서 Redeploy. `apps/*` 가 안 바뀐 커밋은 Ignored Build Step 에 걸리므로 필요하면 09-17 처럼 CLI `vercel deploy --prod --force`
- **[수동 QA](/backlog/w5-manual-qa-full-stack/) 보다 먼저** — 옛 번들로 누르면 이미 고친 것도 ❌ 로 나온다

## 완료 조건

- [x] 셋 다 배포 성공 · `call.solidbob.cloud` 번들에 09-22 변경이 들어 있다(예: 재수정 이력 문구) — **09-22 15:14 KST 완료.** 한도가 「24시간 뒤」가 아니라 롤링으로 풀려 API(`POST /v13/deployments`, git 소스 `68f749a`)로 셋 다 `READY · PROMOTED`. `main` 머리로 올리면 Ignored Build Step 에 걸려 `Canceled` 된다 — 앱을 건드린 마지막 머지 커밋을 sha 로 줘야 한다(런북 18-4). 번들 `call index-4X0vR1JI`·`admin index-BHChBzPJ`·`www index-De7Koey7` 에서 새 문자열 확인
