---
title: "ES 에 연결 못 할 때 /hub/recommendations 500 → 503"
assignee: "장민석"
role: "ai"
status: "done"
sprint: 4
priority: 4
date: 2026-09-14
requirement:
  - "B-2"
paths:
  - "server/main.py"
---

## 무엇을

09-10 에 인덱스가 없을 때(`index_not_found`)는 503 + 이유로 돌려주게 했는데, **ES 자체에 연결을 못 하면**
여전히 500 이다([미결](/open-items/) 2026-09-11 항목). 500 은 «코드가 틀렸다», 503 은 «의존 서비스가 없다» 로
읽혀 고칠 사람이 갈린다.

## 완료 조건

- [x] `elasticsearch.ConnectionError` 도 503 + 이유 (테스트)
- [x] 응답 본문에 주소·자격증명을 싣지 않는다(SEC-2)
