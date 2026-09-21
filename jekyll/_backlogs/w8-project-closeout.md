---
title: "종료 정리 — 자원을 내리고 키를 폐기한다"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 8
priority: 88
date: 2026-09-21
requirement:
  - "SEC-2"
  - "COST-1"
depends_on:
  - "w8-presentation"
paths:
  - "docs/infra-runbook.md"
---

## 무엇을

개발기간 종료(2026-10-27) 뒤 **돈이 나가는 것과 열려 있는 것을 닫는다.**

## 대상

- **AWS** — EC2(k3s) · RDS `callguard-pg` · GPU 인스턴스(세웠다면) · EIP · S3 `assist-apne2`. 런북 「되돌리기 · 정리」 절 순서대로.
  ⚠ S3 는 버전 관리가 꺼져 있어 **지우면 못 되살린다** — 골든셋·평가 결과를 먼저 내려받는다. AI Hub 원본은 재신청에 시간이 걸린다
- **GCP** — STT · TTS API 사용 중지, 서비스 계정 키 · API 키 삭제, 결제 계정 연결 해제
- **토큰·시크릿** — `UPLOAD_TOKEN` · 서비스 토큰 · 뷰 토큰 · 관리자 JWT 시크릿 · **만료 없는 상담원 토큰**(`decisions/122`)
- **Vercel 3종 · 클라우드플레어 DNS · Docker Hub 레포** — 남길 것과 내릴 것을 가른다
- **GitHub** — OIDC 역할 `callguard-deploy-role` · 저장소 시크릿

## 먼저 정할 것 — 전시용으로 남기는가

포트폴리오로 사이트(`docs.solidbob.cloud`)와 데모(mock 모드)를 남길 수 있다 — 그 둘은 돈이 거의 안 든다.
**운영 서버를 남기면 `122`(토큰 만료 없음)를 다시 봐야 한다** — 그 결정은 「프로젝트 기간 동안」을 전제로 했다.

## 완료 조건

- [ ] 남기는 것 · 내리는 것 목록을 팀과 정한다
- [ ] 내린 뒤 **다음 달 청구서에서 0 을 확인한다** — 콘솔에서 지웠다고 끝난 것이 아니다
- [ ] 저장소 이력에 자격증명이 없는지 마지막으로 훑는다(§8)
