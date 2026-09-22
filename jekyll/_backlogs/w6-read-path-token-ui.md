---
title: "읽기 경로에 인증이 걸리면 화면이 토큰을 싣는다 — `w6-read-path-auth` 와 같은 릴리스"
assignee: "조서희"
role: "app"
status: "todo"
sprint: 6
priority: 69
date: 2026-09-22
requirement:
  - "SEC-1"
paths:
  - "apps/call/src/*"
  - "apps/admin/src/*"
depends_on:
  - "w6-read-path-auth"
---
> **정성윤이 09-22 저녁 최종 QA(류준 페르소나 4 + 검증 웨이브)·운영 확인 결과를 보고 만든 티켓이다.** 담당은 «제안»이다 — 본인이 확인하고 맞으면 착수, 아니면 옮긴다.

## 무엇을

통화 목록·전사·기록·검색 조회에 문이 걸리면(`w6-read-path-auth`, 장민석) 상담원 화면·관리자 화면이 그 호출에 토큰을 실어야 한다.
먼저 걸면 화면이 깨지고, 화면만 먼저 하면 의미가 없다 — **같은 날 같은 릴리스**로 맞춘다.

## 완료 조건

- [ ] 장민석 님 라우터 표에 있는 GET 마다 `authedGet` 패턴 적용
- [ ] 운영에서 토큰 없는 탭(로그아웃)에서 목록이 비고 오류 문구가 뜬다
