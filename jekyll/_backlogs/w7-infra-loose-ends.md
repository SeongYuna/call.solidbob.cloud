---
title: "인프라 잔여 넷 — 프로브 · ES configured · uploads 수명 주기 · Vercel 설정"
assignee: "정성윤"
role: "infra"
status: "todo"
sprint: 7
priority: 80
date: 2026-09-21
depends_on:
  - "w5-manual-qa-full-stack"
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
[w2-stt-batch](/backlog/w2-stt-batch/)는 08-28 이후 멈춰 있다 — 오디오가 있는 머신이 없었다. ~~S3 `datasets/` 에 음성이 있으니 EC2 에서 5~10건 돌릴 수 있는지 본다.~~ **2026-09-21 정정 — `datasets/` 는 비어 있다.** 버킷 최상위에 `uploads/` 하나뿐이다(`aws s3 ls s3://assist-apne2/`). 오디오를 누군가 먼저 올려야 이 길이 열린다

## 완료 조건

- [ ] 넷 각각 «했다» 또는 «안 한다 + 이유» 로 미결에서 내린다
- [ ] 위 두 티켓을 끝내거나, 안 하기로 하면 `cancelled` 로 닫고 이유를 적는다

## 준비 — 2026-09-21 읽기 전용으로 확인한 사실 (정성윤)

넷 다 «했다» 또는 «안 한다»로 닫기 위한 재료다. 운영은 아무것도 바꾸지 않았다.

1. **`/health/ready` 프로브** — 서버의 readinessProbe 는 지금 **`/docs`** 를 본다(`infra/k8s/base/server.yaml` 31~37줄, 주석에 「운영이 실제로 쓰는 값이라 그대로 뒀다」). liveness 프로브는 없다.
   `/health/ready` 로 바꾸면 ES·DB 가 잠깐 끊길 때 **서비스에서 빠진다**(재시작은 liveness 가 없어 일어나지 않는다). 자막·마스킹은 ES 없이도 돌아서 대가가 크다.
   **권고: 안 한다** — 지금처럼 `/docs` 를 두고 `/health/ready` 는 런북 19장 수동 검사로 둔다
2. **ES `configured`** — 원인을 아직 안 봤다. 노드에서 `sudo k3s kubectl diff -f <렌더한 매니페스트>` 로 무엇이 다르다고 보는지 한 번 본다.
   StatefulSet 은 `volumeClaimTemplates` 기본값이 서버에서 채워져 매번 diff 가 나는 경우가 흔하다(추정). 실제로 바뀌는 것이 없으면 **안 한다**로 닫아도 된다
3. **업로드 수명 주기** — 버킷 규칙은 **하나뿐**이다: `datasets-to-ia`(접두어 `datasets/`, 30일 뒤 Standard-IA). **`uploads/` 에는 규칙이 없다.** 그런데 `datasets/` 에는 객체가 없다(위 정정).
   하려면 `uploads/` 에 만료 규칙(예: 90일 — 근거 없는 예시값)을 더한다. 시연 음성을 남겨야 하면 **안 한다**
4. **Vercel** — 이 머신에 vercel CLI 가 없다. 대시보드에서 한다: 프로젝트 셋의 Settings → Git → Ignored Build Step 값과 Root Directory 를 런북 18-4 대조표와 눈으로 맞춘다.
   옛 변수 둘(`VITE_GATEWAY_WS_URL` · `VITE_GATEWAY_DEMO_BASE_URL`)은 `call-solidbob-cloud-kxu6` → Settings → Environment Variables 에서 지운다(재배포 불필요 — 번들이 이미 새 변수로 구워졌다)
