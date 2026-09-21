---
title: "인프라 잔여 넷 — 프로브 · ES configured · uploads 수명 주기 · Vercel 설정"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 7
priority: 80
date: 2026-09-21
paths:
  - "infra/k8s/base/*"
---

## 무엇을

[미결 항목](/open-items/)에 흩어져 있는 작은 인프라 항목 넷을 **하거나, 안 하기로 닫는다.** 넷 다 «안 한다»로 닫아도 되는 종류다 —
`decisions/116` 이 위생 작업 여섯을 그렇게 닫았다. **열어 둔 채 발표까지 가지 않는 것이 목적이다.**

1. **`GET /health/ready` 를 k8s 프로브에 붙일지** — 붙이면 ES·DB 가 잠깐 끊길 때 파드가 재시작된다. 그게 나은지가 판단 대상이다
2. **ES StatefulSet 이 릴리스마다 `configured` 로 찍힌다** — 실제로 바뀌는 것이 없는데 diff 가 난다
3. **`uploads/` 수명 주기 규칙** — `datasets/` 에만 걸려 있다(런북 5-4). 테스트 음성이 쌓이기만 한다
4. **Vercel Ignored Build Step 을 `vercel.json` 으로 옮길지 · Root Directory 눈 확인** — 조서희 님과 → **09-22 진행**: Root Directory 셋은 대조표와 일치했고, 랜딩의 Ignored Build Step 이 `apps/admin` 으로 틀려 있어 고쳤다(09-15 이후 랜딩 미배포 — 로그 `2026-09-22-01`, 런북 18-4 추가). `vercel.json` 이관 여부만 남았다

## 같이 — 오래 열린 내 티켓 둘

[w4-aws-resource-hygiene](/backlog/w4-aws-resource-hygiene/)(RDS 권장 2건 · Enhanced Monitoring · 7월 잔재)은 `116` 과 **다른 항목들**이라 그대로 열려 있다.
[w2-stt-batch](/backlog/w2-stt-batch/)는 08-28 이후 멈춰 있다 — 오디오가 있는 머신이 없었다. S3 `datasets/` 에 음성이 있으니 EC2 에서 5~10건 돌릴 수 있는지 본다.

## 완료 조건

- [ ] 넷 각각 «했다» 또는 «안 한다 + 이유» 로 미결에서 내린다
- [ ] 위 두 티켓을 끝내거나, 안 하기로 하면 `cancelled` 로 닫고 이유를 적는다
