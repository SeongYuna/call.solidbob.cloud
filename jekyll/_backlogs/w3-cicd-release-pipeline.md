---
title: "머지하면 배포되게 만든다 — GitHub Actions + OIDC + SSM"
assignee: "정성윤"
role: "infra"
status: "in-progress"
sprint: 3
priority: 2
date: 2026-09-09
depends_on:
  - "w3-k3s-image-and-manifests"
paths:
  - ".github/workflows/release.yml"
---

## 무엇을

`main` 에 머지하면 이미지를 굽고 EC2 의 k3s 에 배포되게 한다.
지금은 손으로 굽고 손으로 `kubectl apply` 한다.

## 어떻게 — 설계가 갈린 지점 넷

**① 버전은 저장소가 정한다.** `kustomization.yaml` 의 `images.newTag` 를 읽어 그 태그로 굽는다.
CI 가 태그를 만들어 저장소에 되쓰지 **않는다** — main 이 보호돼 있어 봇이 push 할 수 없고,
되쓰면 「저장소 = 클러스터」 불변식이 흔들린다. **버전 올리기는 PR 안에서 사람이 한다.**

**② 인스턴스에서 git 을 쓰지 않는다.** 러너가 `kubectl kustomize` 로 렌더한 YAML 을 base64 로
SSM 에 실어 보낸다. 2026-09-09 확인 결과 **인스턴스에 git 도 저장소 클론도 없었다.**
만들 이유가 없다 — CI 가 렌더한 그 YAML 이 그대로 적용되는 편이 어긋날 여지가 적다.
렌더 결과는 `/opt/callguard/current.yaml` 에 남겨 부팅 시 자동 수렴이 재사용한다.

**③ SSM 을 쓰는 이유는 포트를 열지 않기 위해서다.** 러너 IP 는 매번 바뀌는데 6443·22 는
담당자 IP 하나로만 열려 있다. GitHub IP 대역을 여는 것은 6443 을 인터넷에 여는 것과 같다.

**④ 자격증명을 저장하지 않는다.** OIDC 로 `callguard-deploy-role` 을 빌린다(1시간 임시).
Root 단독 운영이라 대안이 **Root 액세스 키뿐**인데 그건 계정 전체를 GitHub 에 맡기는 것이다.

## 완료 조건

- [x] `callguard-ec2-role` 생성·부착 — SSM 통로 (실측: IMDS 404 → `HealthCheck reporting agent health`)
- [x] OIDC 자격 증명 공급자
- [x] `callguard-deploy-role` — 신뢰 정책 `refs/heads/main` 한정 · 권한 3종(475개 서비스 중 2개)
- [x] `.github/workflows/release.yml`
- [x] ~~탄력적 IP 부착~~ — **붙이지 않기로 했다**(2026-09-09). IP 갱신을 매일 수동으로 한다
- [x] Docker Hub Access Token + GitHub Secrets 4개 (2026-09-09)
- [ ] 첫 배포 실검증
- [ ] 부팅 시 자동 수렴 systemd 유닛
- [ ] 자동 중지 cron
- [ ] `_project/decisions/108`

## 탄력적 IP 를 붙이지 않는다 (2026-09-09 결정)

인스턴스를 껐다 켜면 공인 IP 가 바뀐다(`16.184.8.48` → `16.184.33.38` 실측).
**매일 켤 때 Cloudflare `server` A 레코드를 손으로 갱신한다.** 월 약 $3.6 을 아끼는 대신
그 손질을 받는다.

⚠ **파이프라인에 미치는 영향 하나** — `release.yml` 의 스모크 테스트가
`https://server.solidbob.cloud/health` 를 친다. **DNS 가 낡은 상태에서 머지하면 배포는
성공해도 스모크 테스트가 실패한다.** 인스턴스를 켠 뒤 DNS 를 먼저 고치고 머지한다.

## 안 하는 것

- **필수 통과 검사에 넣지 않는다.** 넣으면 배포가 PR 머지를 막는다(`CLAUDE.md` §7)
- **ES 인덱스 적재를 파이프라인에 넣지 않는다.** 지식베이스가 바뀔 때만 필요하다 — 별도 Job
