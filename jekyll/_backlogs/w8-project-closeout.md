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

## ⚠ 2026-10-08 추가 — 「키 폐기」 전에 전사를 먼저 뽑는다

`TRANSCRIPT_ENC_KEY` 가 **2026-10-08 부터 켜져 있다**(`/health` `"transcript_encryption":"on"`,
[w8-transcript-enc-key-ops](/backlog/w8-transcript-enc-key-ops/)). 그날 이후 저장된 `transcript_segment.text` 는
**`enc:v1:…` 암호문**이고, **그 키로만 읽힌다.**

그래서 종료 정리의 「키 폐기」를 순서 없이 하면 **그 뒤로 쌓인 전사를 영원히 못 읽는다** — 시연 통화도 포함이다.
런북 12-2-d 도 「키를 지우지 않는다 — 지우면 지난 통화 보기·블랙리스트 근거가 500」 이라고 적고 있다.

**순서를 이렇게 고정한다:**

1. 남길 자료 결정 → **전사·요약을 API(`GET /hub/calls/{id}/transcript`)로 뽑는다** — 서버가 풀어서 마스킹본으로 준다
2. 골든셋·평가 결과 내려받기 (S3)
3. 그다음에야 AWS 자원 내림 · GCP 끄기
4. **키 폐기는 맨 끝** — SSM 파라미터 `/callguard/prod/TRANSCRIPT_ENC_KEY` 와 `server-env` 의 같은 키.
   IAM 인라인 정책 `transcript-enc-key` 도 이때 함께 지운다
5. 청구서 0 확인
