---
title: "배포 전에 운영 스키마를 대조한다 — compare_prod_schema 를 절차에 넣기"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 6
priority: 77
date: 2026-09-21
requirement:
  - "SEC-2"
paths:
  - "scripts/compare_prod_schema.py"
  - ".github/workflows/release.yml"
---

## 무엇을

`scripts/compare_prod_schema.py`(09-20, 운영 DB ↔ `db/schema.sql` 컬럼 단위 대조)를 **배포 절차 안에** 넣는다.

## 왜

도구는 있는데 **사람이 기억해야 돈다.** 스키마가 바뀐 서버 이미지가 마이그레이션보다 먼저 나가면
그 테이블을 읽는 경로가 운영에서 500 이 된다 — 09-15 에 27·29 테이블로 늘 때마다 손으로 맞췄다.
09-20 대조는 29 테이블 198 컬럼 어긋남 0 이었지만 **그건 그날의 값이다.**

## 완료 조건

- [ ] 런북 배포 절(19장)에 단계로 들어가거나, `release.yml` 에서 돌게 한다 — 어느 쪽인지와 이유를 적는다
- [ ] 어긋나면 **배포를 멈춘다**(경고만 하고 지나가지 않는다)
- [ ] DB 자격증명을 워크플로 로그에 찍지 않는다(SEC-2)
