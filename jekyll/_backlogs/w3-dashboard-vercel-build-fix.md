---
title: "대시보드 Vercel 빌드 실패를 고친다 — 앱 경계를 넘는 import 제거"
assignee: "정성윤"
role: "infra"
status: "done"
sprint: 3
priority: 4
date: 2026-09-08
depends_on:
  - "w3-dashboard-deploy"
paths:
  - "apps/dashboard/vite.config.ts"
---

## 무엇을

`apps/dashboard` 가 `apps/platform/src` 의 파일을 상대경로로 직접 import 하던 것을 끊는다.
공유하던 `theme.tsx`·`ThemeToggle.tsx`(+`.css`)를 `apps/dashboard/src` 안으로 복사하고,
`vite.config.ts` 의 `server.fs.allow: [".."]` 를 걷어낸다.

## 왜

**Vercel 배포가 `tsc --noEmit` 에서 죽는다.** 실패 로그 —

```
../platform/src/components/ThemeToggle.tsx(1,35): error TS2307: Cannot find module 'react'
../platform/src/theme.tsx(9,8):  error TS2307: Cannot find module 'react'
../platform/src/theme.tsx(66,15): error TS7006: Parameter 'current' implicitly has an 'any' type
../platform/src/theme.tsx(75,5):  error TS2875: This JSX tag requires 'react/jsx-runtime'
Error: Command "npm run build" exited with 2
```

모듈 해석의 기준점은 **tsconfig 위치가 아니라 소스 파일이 놓인 경로**다.
`apps/platform/src/theme.tsx` 안의 `import "react"` 는 `apps/platform/node_modules` →
`apps/node_modules` → 저장소 루트 순으로 찾는데, Vercel 은 Root Directory 인
`apps/dashboard` 하나만 설치한다([w3-dashboard-deploy](/backlog/w3-dashboard-deploy/)).
셋 다 비어 있어 react 를 못 찾는다. TS2875·TS7006 은 그 여파다.

**로컬에서 안 드러난 이유**: 개발 머신에는 `apps/platform/node_modules/react` 가 이미
설치돼 있어 해석이 성공한다. 코드가 아니라 **의존성이 놓인 위치**가 갈린 것이다.

## 완료 조건

- [x] `theme.tsx`·`ThemeToggle.tsx`·`ThemeToggle.css` 를 `apps/dashboard/src` 로 복사
- [x] `main.tsx`·`AgentStandbyScreen.tsx` 의 import 를 프로젝트 안쪽으로 교체
- [x] `vite.config.ts` 의 `server.fs.allow: [".."]` 제거 (같은 커밋 `9f730f9` 에서 들어온 임시방편)
- [x] `apps/platform/node_modules` 가 **없는** 상태에서 `tsc --noEmit` · `vite build` 통과 확인
- [x] 푸시 후 Vercel 재배포가 실제로 초록인지 확인 — PR #50 의 Vercel 검사 2건 통과,
      머지 후 Production 배포 2건 `success`, 라이브 번들 해시가 로컬 빌드와 일치(`index-BycDJbT8.js`)
- [ ] 조서희에게 통보 — `apps/dashboard/` 는 조서희 소관인데 배포 복구라 PM 이 먼저 손댔다

## 남은 것

**공유 코드가 또 생기면 이 복사본이 갈린다.** 지금은 파일 3개뿐이라 복사가 싸지만,
공유가 늘면 npm workspaces 로 `packages/ui` 를 떼고 Vercel Root Directory 를 저장소
루트로 올리는 쪽이 맞다. 그때는 빌드 명령이 `npm run build -w callguard-dashboard` 가 된다.
