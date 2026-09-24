---
title: "`vercel.json` 셋 — PM·ai·server 브랜치의 Vercel 배포 생성을 끈다 (하루 100건 한도)"
assignee: "조서희"
role: "app"
status: "done"
sprint: 6
priority: 57
date: 2026-09-22
paths:
  - "apps/call/vercel.json"
  - "apps/admin/vercel.json"
  - "apps/platform/vercel.json"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

09-22 Vercel 하루 배포 한도(100건)에 걸려 운영 화면이 반나절 멈췄다. Ignored Build Step 은 빌드만 취소하고 **배포 생성은 그대로 세어** 막지 못한다
(24시간에 147건 생성, 그중 123건 Canceled). 다섯 브랜치 × 세 프로젝트라 push 한 번이 3건이다.

## 어떻게

`apps/call` · `apps/admin` · `apps/platform` 각 Root Directory 에 같은 파일:

```json
{ "git": { "deploymentEnabled": { "PM": false, "ai": false, "server": false } } }
```

main·frontend 만 남아 147 → 76 이 된다. `apps/` 가 조서희 전담이라 여기서 넣는다(정성윤이 넣고 확인받는 것도 된다 — 미결).

## 완료 조건

- [ ] 셋 다 커밋 · 다음 PM/ai/server push 에서 Vercel 체크가 안 생기는 것 확인
- [ ] 런북 18-4 에 한 줄(정성윤)

근거: 정성윤 11·14번 기록 · 런북 18-4.

## 2026-09-22 — 파일 대신 Vercel 설정으로 끝냄 (정성윤)

정성윤이 **Vercel 프로젝트 설정에서 직접** 브랜치 배포를 막았다 — `vercel.json` 파일은 넣지 않는다. 그래서 `apps/`(조서희 전담)는 건드리지 않았다.
확인할 것: 다음 `PM`·`ai`·`server` push 에서 Vercel 체크가 생기지 않는지. 설정이 저장소에 없으므로 프로젝트를 새로 만들면 다시 해야 한다(런북 18-4 에 한 줄).
