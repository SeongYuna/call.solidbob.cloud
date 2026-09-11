# 인프라 구축 런북 — 빈 AWS 계정에서 시작

> **대상**: 실시간 상담원 어시스트 RAG 시스템 (다산콜센터)
> **전제**: **AWS 에 아무것도 만들어져 있지 않음.** 계정 설정부터 시작한다
> **구성**: 단일 g4dn.xlarge + k3s + RDS + S3. 근거는 [부록 A](#부록-a--왜-이-구성인가)
> **예산**: $400 중 약 $200 소진 예상
> **AWS 밖 전제**: Cloudflare 에 `solidbob.cloud` 존 존재, GitHub 저장소 존재

> ⚠ **실물과 다른 곳이 있다 (2026-09-11).** 이 런북은 09-04 원안이다. 09-08 실제 배포는
> 네임스페이스 `callguard` · Deployment `callguard-server` · 시크릿 `server-env` ·
> Traefik Ingress + cert-manager(Caddy 없음) · Amazon Linux 2023 · **인스턴스에 저장소 클론 없음**
> (배포는 `.github/workflows/release.yml` 이 SSM 으로 한다)이다.
> **DB 가 걸린 곳 — 6 · 12-2 · 17 · 19장과, 같은 이름이 나오는 0장 자원표 · 3-2 · 22장 · 문제 해결 표 —
> 은 실물 기준으로 고쳤다**(`_project/decisions/108`).
>
> **이름 정정 (2026-09-11, 같은 날 두 번째).** `callguard` 는 **k8s 오브젝트**(네임스페이스·Deployment)의 이름이고,
> **AWS 자원은 원안 `assist-*` 가 실물이다** — EC2 보안 그룹 `assist-web`(콘솔 확인). 첫 정정이 둘을 섞었다.
> RDS 만 섞여 있다: **식별자 `callguard-pg` · 마스터 사용자 `callguard` · 초기 DB `assist`**
> (`aws rds describe-db-instances` 로 확인). RDS 에 붙은 DB 보안 그룹도 원안 이름 **`assist-db`** 이고
> 5432 인바운드 소스가 운영 EC2 에 붙은 **`assist-web`** 이다(3-2 의 대조 명령으로 두 ID 일치 확인, 2026-09-11).
> 나머지 장 — 특히 13(클론) · 16-2(Caddy) — 은 원안 그대로다. 클러스터 구성의 정본은
> `infra/k8s/base/` 다(라이브 클러스터와 `kubectl diff` 차이 0, 2026-09-08).

---

## 작업 순서 한눈에

```
[1] 계정 · 예산 · 할당량      ← 오늘. GPU 할당량은 승인에 하루 걸림
[2] 키 페어
[3] 보안 그룹 2개              ← web 먼저, db 나중 (db 가 web 을 참조)
[4] IAM 역할
[5] S3 + VPC 엔드포인트
[6] RDS 생성 시작              ← 10분 걸림. 걸어 두고 [7] 로 진행
[7] EC2 인스턴스
[8] 탄력적 IP
─────────────────────── 여기까지 AWS 콘솔 작업
[9] 접속 · 디스크 · GPU 확인
[10] k3s 설치
[11] GPU 공유 설정             ← 가장 실수하기 쉬운 지점
[12] 네임스페이스 · 시크릿 · 볼륨
[13] 코드 클론 · 이미지 빌드
[14] Ollama + EXAONE
[15] Elasticsearch
[16] server + Caddy
[17] DB 스키마
[18] DNS · HTTPS
[19] 검증
[20] AMI 스냅샷                ← 반드시
[21] 자동 중지 설정            ← 예산을 결정하는 단계
```

**총 소요**: 콘솔 작업 1시간 + 서버 작업 2~3시간. GPU 할당량 승인 대기는 별도.

---

## 목차

- [0. 최종 자원 명세와 비용](#0-최종-자원-명세와-비용)
- [1. 계정 · 예산 · 할당량 — 오늘 해야 함](#1-계정--예산--할당량--오늘-해야-함)
- [2. 키 페어](#2-키-페어)
- [3. 보안 그룹](#3-보안-그룹)
- [4. IAM 역할](#4-iam-역할)
- [5. S3 버킷 + VPC 엔드포인트](#5-s3-버킷--vpc-엔드포인트)
- [6. RDS PostgreSQL](#6-rds-postgresql)
- [7. EC2 인스턴스](#7-ec2-인스턴스)
- [8. 탄력적 IP](#8-탄력적-ip)
- [9. 접속 · 디스크 · GPU 확인](#9-접속--디스크--gpu-확인)
- [10. k3s 설치](#10-k3s-설치)
- [11. GPU 를 여러 파드가 나눠 쓰게 만들기](#11-gpu-를-여러-파드가-나눠-쓰게-만들기)
- [12. 네임스페이스 · 시크릿 · 볼륨](#12-네임스페이스--시크릿--볼륨)
- [13. 코드 클론 · 이미지 빌드](#13-코드-클론--이미지-빌드)
- [14. Ollama + EXAONE](#14-ollama--exaone)
- [15. Elasticsearch](#15-elasticsearch)
- [16. server + Caddy](#16-server--caddy)
- [17. DB 스키마](#17-db-스키마)
- [18. DNS · HTTPS](#18-dns--https)
- [19. 검증 체크리스트](#19-검증-체크리스트)
- [20. AMI 스냅샷 — 반드시](#20-ami-스냅샷--반드시)
- [21. 자동 중지 · 일상 운영](#21-자동-중지--일상-운영)
- [22. 측정 전용 인스턴스 (5주차)](#22-측정-전용-인스턴스-5주차)
- [트러블슈팅](#트러블슈팅)
- [만들지 말 것](#만들지-말-것)
- [되돌리기 · 정리](#되돌리기--정리)
- [부록 A — 왜 이 구성인가](#부록-a--왜-이-구성인가)
- [부록 B — 결정 기록에 남길 것](#부록-b--결정-기록에-남길-것)

---

## 0. 최종 자원 명세와 비용

### 만드는 것 (전부 신규)

| # | 자원 | 이름 | 사양 |
|---|---|---|---|
| 1 | 키 페어 | `assist-key` | RSA, .pem |
| 2 | 보안 그룹 | `assist-web` | 80·443 전체 / 22·6443 내 IP |
| 3 | 보안 그룹 | `assist-db` | 5432 ← `assist-web` |
| 4 | IAM 역할 | `assist-ec2-role` | S3 + SSM |
| 5 | S3 버킷 | `assist-<계정ID>-apne2` | 데이터셋·모델·골든셋 |
| 6 | VPC 엔드포인트 | `assist-s3-gw` | **Gateway** 유형, 무료 |
| 7 | RDS | `callguard-pg` | PostgreSQL 17, db.t4g.micro, 20GiB |
| 8 | EC2 | `assist-gpu-01` | **g4dn.xlarge**, Ubuntu DLAMI |
| 9 | EBS 루트 | (EC2 에 포함) | **gp3 150 GiB**, 암호화 O |
| 10 | 인스턴스 스토어 | (내장, 무료) | 125GB NVMe |
| 11 | 탄력적 IP | — | 1개 |
| 12 | AMI | `assist-gpu-baseline` | 세팅 완료 후 |

> **VPC · 서브넷은 만들지 않습니다.** AWS 계정에는 리전마다 **기본 VPC** 가 자동 생성돼 있고, 퍼블릭 서브넷 구성이라 그대로 쓰면 됩니다. 직접 만들면 NAT Gateway(월 $35+)를 붙이게 될 위험만 커집니다.

### EC2 사양을 g4dn.xlarge 로 잡은 근거

확정 모델(`decisions/010`) 전체를 올렸을 때의 사용량입니다.

| | VRAM | 호스트 RAM |
|---|---|---|
| EXAONE-4.0-1.2B GGUF (Q4) + KV 캐시 | ~1.5GB | ~1.0GB |
| KoE5 (335M, fp16) | ~0.7GB | — |
| KcELECTRA-base (fp16) | ~0.25GB | — |
| koelectra-ner (fp16) | ~0.25GB | — |
| klue-roberta-base (5주차 대조군) | ~0.25GB | — |
| CUDA 컨텍스트 (프로세스 2개) | ~1.0GB | ~2.0GB |
| Elasticsearch (힙 2g) | — | ~3.0GB |
| FastAPI server · Node 게이트웨이 · Caddy | — | ~1.0GB |
| k3s · containerd · OS | — | ~1.5GB |
| **합계 / 가용** | **~4.0 / 16GB** | **~8.5 / 16GiB** |

여유가 충분합니다. 6주차 생성 대조군(kanana-2.1b)을 확보해 추가로 올려도 문제없습니다.

### 비용 (6주, 서울 리전 정가 근사치)

| 항목 | 6주 |
|---|---|
| g4dn.xlarge (하루 8h × 주 5일 = 240h) | $142 |
| EBS gp3 150GiB | $19 |
| AMI 스냅샷 85GB | $6 |
| 탄력적 IP | $5 |
| RDS db.t4g.micro + 스토리지 20GiB | $21 |
| S3 100GB | $4 |
| t3.micro 측정용 40h | $1 |
| **합계** | **≈ $198** |

> ⚠ **GPU 를 24/7 로 켜면 $142 → $597 이 되어 예산을 초과합니다.** 다른 모든 항목을 합친 것보다 이 변수 하나가 큽니다. **21장의 자동 중지를 반드시 설정하십시오.**

정확한 값은 AWS Pricing Calculator 에서 확인하십시오. 위는 정가 근사치입니다.

---

## 1. 계정 · 예산 · 할당량 — 오늘 해야 함

### 1-1. GPU 서비스 할당량 ⚠ 최우선

**신규 AWS 계정은 G 계열 vCPU 할당량이 0 인 경우가 흔하고, 증설 승인에 영업일 하루 이상 걸립니다.** 이걸 모르면 착수 당일에 인스턴스를 못 만듭니다. AI Hub 승인 지연과 같은 성격의 리스크입니다.

콘솔 → 상단 검색 **Service Quotas** → **AWS 서비스** → **Amazon EC2** → 검색창에 `G and VT` 입력

| 항목 | 확인 |
|---|---|
| `Running On-Demand G and VT instances` | **적용된 값이 4 이상**이어야 g4dn.xlarge(4 vCPU) 생성 가능 |

**0 이거나 4 미만이면 지금 즉시 증설 요청**하십시오. **8** 정도로 요청하면 여유가 있습니다.

- 요청 사유란에 "GPU inference for a university team project, single instance, ~8 hours/day" 정도로 적으면 됩니다
- 승인까지 보통 수 시간 ~ 영업일 2일

CLI 로 확인하려면:

```bash
aws service-quotas get-service-quota \
  --service-code ec2 --quota-code L-DB2E81BA --region ap-northeast-2
```

### 1-2. 리전 고정

오른쪽 위가 **아시아 태평양(서울) ap-northeast-2** 인지 확인하십시오.

**모든 자원을 같은 리전에 만들어야 합니다.** 다른 리전에 만들면 서로 통신이 안 되거나 통신료가 붙고, Google STT 왕복 지연도 늘어 4.3절 E2E 측정이 나빠집니다.

### 1-3. 루트 계정 보호 (신규 계정이라면)

| 항목 | 조치 |
|---|---|
| 루트 계정 MFA | **활성화** — 계정 탈취 시 예산이 아니라 계정 전체가 문제 |
| 일상 작업용 IAM 사용자 | 별도 생성 후 그것으로 작업. 루트로 콘솔을 쓰지 않음 |

### 1-4. 결제 정보 접근 허용

**루트 계정으로 로그인한 상태에서만** 설정할 수 있습니다.

```
계정 (우상단 계정명) → 계정 설정
  → "IAM 사용자/역할의 결제 정보 액세스" → 활성화
```

이걸 안 하면 IAM 사용자로는 Budgets 화면이 안 보입니다.

### 1-5. 예산 알람 ⚠ 인스턴스를 만들기 전에

콘솔 → **Billing and Cost Management** → **Budgets** → **예산 생성**

| 항목 | 값 |
|---|---|
| 템플릿 | 사용자 지정 (고급) |
| 유형 | **비용 예산** |
| 기간 | 월별 |
| 예산 금액 | **$150** (월 기준. 총 $400 을 다 쓰고 알리면 늦습니다) |
| 알림 임계값 | **40% / 60% / 80% / 100%** — 각각 메일 |

이어서 **Cost Anomaly Detection** 도 활성화하십시오. 평소 대비 비용이 튀면 알려 줍니다. 무료입니다.

> ⚠ **AWS 는 알림만 하고 자동으로 차단하지 않습니다.** 예산 초과를 막는 유일한 방법은 **비싼 것을 만들지 않는 것**과 **안 쓸 때 끄는 것**입니다.

### 1-6. 기본 VPC 확인

콘솔 → **VPC** → **VPC** 목록에 `기본 VPC = 예` 인 항목이 있는지 확인하십시오.

없다면 (드묾): **작업 → 기본 VPC 생성** 을 누르면 됩니다. 직접 VPC 를 설계하지 마십시오 — 프라이빗 서브넷을 만들면 NAT Gateway 가 필요해지고 **월 $35+** 가 붙습니다.

---

## 2. 키 페어

콘솔 → **EC2** → 왼쪽 **네트워크 및 보안** → **키 페어** → **키 페어 생성**

| 항목 | 값 |
|---|---|
| 이름 | **`assist-key`** |
| 키 페어 유형 | RSA |
| 프라이빗 키 파일 형식 | **.pem** (macOS·Linux·최신 Windows) |

생성 즉시 `assist-key.pem` 이 다운로드됩니다. **이때 한 번만 받을 수 있고, 다시 받을 방법이 없습니다.**

```bash
mkdir -p ~/.ssh
mv ~/Downloads/assist-key.pem ~/.ssh/
chmod 400 ~/.ssh/assist-key.pem
```

`chmod 400` 을 안 하면 SSH 가 `UNPROTECTED PRIVATE KEY FILE` 오류로 거부합니다.

---

## 3. 보안 그룹

**순서가 있습니다.** `assist-db` 가 `assist-web` 을 소스로 참조하므로 web 을 먼저 만들어야 합니다.

### 3-1. `assist-web` — EC2 용

EC2 → 왼쪽 **보안 그룹** → **보안 그룹 생성**

| 항목 | 값 |
|---|---|
| 이름 | **`assist-web`** |
| 설명 | `EC2 app node` |
| VPC | **기본 VPC** |

**인바운드 규칙** 4개:

| 유형 | 포트 | 소스 | 용도 |
|---|---|---|---|
| HTTP | 80 | `0.0.0.0/0` | Let's Encrypt 챌린지 + 리다이렉트 |
| HTTPS | 443 | `0.0.0.0/0` | 서비스 |
| SSH | 22 | **내 IP** | 서버 접속 |
| 사용자 지정 TCP | **6443** | **내 IP** | k3s API (kubectl) |

**아웃바운드**: 기본값(전체 허용) 그대로 둡니다.

> ⚠ **6443 을 `0.0.0.0/0` 으로 열지 마십시오.** 쿠버네티스 API 서버가 인터넷에 노출되면 클러스터 전체가 위험합니다.
>
> ⚠ **11434(Ollama)는 어떤 경우에도 열지 마십시오.** Ollama 는 인증이 전혀 없어서, 열면 누구나 여러분의 GPU 로 추론을 돌릴 수 있습니다. 인터넷에 노출된 Ollama 를 스캔하는 봇이 실제로 돌아다닙니다. 클러스터 내부 ClusterIP 로만 접근합니다.
>
> "내 IP" 를 고르면 현재 공인 IP 가 자동 입력됩니다. **공유기 IP 는 바뀔 수 있으므로**, 나중에 SSH 가 갑자기 막히면 여기를 먼저 확인하십시오.

### 3-2. `assist-db` — RDS 용

> **2026-09-11 정정** — 한때 `callguard-db` 로 고쳤다가 되돌렸다. AWS 자원은 원안 `assist-*` 가 실물이다(머리말).
> RDS 에 붙은 보안 그룹은 **`assist-db`** 이고 5432 인바운드 규칙 1개가 보안 그룹을 소스로 한다(2026-09-11 확인).
> **그 소스가 EC2 에 실제로 붙은 `assist-web` 인지**는 아래로 대조한다 — 두 줄의 ID 가 같아야 한다.
> (2026-09-11 대조 결과: 같다. 운영 EC2 에 붙은 보안 그룹은 `assist-web` 하나다.)
>
> ```bash
> # ① assist-db 의 5432 소스
> aws ec2 describe-security-groups --filters Name=group-name,Values=assist-db \
>   --query 'SecurityGroups[].IpPermissions[?FromPort==`5432`][].UserIdGroupPairs[].GroupId' --output text
> # ② 운영 EC2 에 붙은 보안 그룹 (이름·ID)
> aws ec2 describe-instances --filters Name=instance-state-name,Values=running \
>   --query 'Reservations[].Instances[].SecurityGroups[].[GroupName,GroupId]' --output text
> ```

**보안 그룹 생성** 을 다시 누릅니다.

| 항목 | 값 |
|---|---|
| 이름 | **`assist-db`** |
| 설명 | `RDS PostgreSQL` |
| VPC | **기본 VPC** (web 과 같아야 함) |

**인바운드 규칙** 1개:

| 유형 | 포트 | 소스 |
|---|---|---|
| PostgreSQL | 5432 | **사용자 지정 → `assist-web`** |

소스에 IP 가 아니라 **보안 그룹을 지정**하는 것이 핵심입니다. 이러면 EC2 를 새로 만들거나 IP 가 바뀌어도 규칙을 고칠 필요가 없습니다.

> **운영 EC2 에 붙은 보안 그룹은 `assist-web` 이다**(2026-09-11 콘솔 확인). 한때 이 자리에 «운영 인스턴스는
> 원안대로 만들어지지 않았다» 고 적었는데 틀렸다 — 보안 그룹은 원안 그대로다.
> k3s 파드가 나가는 트래픽은 노드 IP 로 바뀌어(SNAT) EC2 네트워크 인터페이스로 나가므로, 보안 그룹을 소스로 한 규칙이 파드에도 그대로 맞는다.

---

## 4. IAM 역할

서버에 액세스 키를 넣지 마십시오. 역할을 붙이면 자격증명이 자동 주입되고, 유출 위험이 없습니다.

콘솔 → **IAM** → **역할** → **역할 생성**

1. 신뢰할 수 있는 엔터티 유형 → **AWS 서비스** → 사용 사례 **EC2**
2. 권한 → `AmazonSSMManagedInstanceCore` 검색 후 체크
3. 역할 이름 → **`assist-ec2-role`** → 생성

### 4-1. S3 권한을 인라인 정책으로 추가

`AmazonS3FullAccess` 를 붙이면 계정의 모든 버킷에 접근됩니다. 버킷 하나로 좁힙니다.

역할 `assist-ec2-role` → **권한 추가** → **인라인 정책 생성** → **JSON** 탭

`<계정ID>` 를 본인 12자리 계정 번호로 바꾸십시오 (우상단 계정 메뉴에서 확인).

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": "arn:aws:s3:::assist-<계정ID>-apne2"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::assist-<계정ID>-apne2/*"
    }
  ]
}
```

정책 이름: `assist-s3-access`

---

## 5. S3 버킷 + VPC 엔드포인트

### 5-1. 버킷 생성

콘솔 → **S3** → **버킷 만들기**

| 항목 | 값 | 이유 |
|---|---|---|
| 이름 | **`assist-<계정ID>-apne2`** | 버킷 이름은 **전역 고유**. 계정 ID 를 넣으면 충돌 없음 |
| 리전 | **아시아 태평양(서울)** | EC2 와 같아야 전송 무료 |
| 객체 소유권 | ACL 비활성화 (기본) | |
| 퍼블릭 액세스 차단 | **모두 차단** | 전사·평가 데이터가 들어감 |
| 버킷 버전 관리 | **비활성화** | 전체에 켜면 저장료가 두 배 |
| 기본 암호화 | SSE-S3 (기본) | 무료 |

### 5-2. 왜 EBS 가 아니라 S3 인가

| | EBS gp3 | S3 Standard |
|---|---|---|
| 100GB 월 비용 | $9.1 | **$2.5** |
| 여러 인스턴스에서 접근 | 불가 | 가능 |
| 인스턴스 종료 후 | 설정에 따라 소멸 | **무관하게 생존** |

**AI Hub 음성 데이터는 승인받는 데 시간이 걸리는 자산입니다.** 인스턴스와 생명주기를 묶으면 안 됩니다.

### 5-3. 프리픽스 구조

버킷 안에 폴더를 만들 필요는 없습니다. 업로드할 때 경로를 이렇게 쓰면 자동으로 생깁니다.

```
s3://assist-<계정ID>-apne2/
├── datasets/
│   ├── aihub-seoul-minwon/   서울 행정 민원상담 음성 6,614개
│   ├── aihub-505/            외국인 한국어 발화 (A-5)
│   └── aihub-71479/          교육용 아시아어 한국어 (숙련도 라벨)
├── models/                   HF 가중치 미러 — 재다운로드 회피
├── goldenset/                골든셋 JSON
├── eval-results/             평가 결과 · matplotlib 산출물
└── backups/                  ES 스냅샷 · 설정 백업
```

### 5-4. 수명 주기 규칙

버킷 → **관리** 탭 → **수명 주기 규칙 생성**

| 항목 | 값 |
|---|---|
| 규칙 이름 | `datasets-to-ia` |
| 범위 | 접두사로 제한 → `datasets/` |
| 작업 | **스토리지 클래스 간 객체의 현재 버전 전환** |
| 전환 | **Standard-IA**, **30**일 후 |

한 번 전처리하면 원본은 자주 읽지 않습니다. 약 45% 절감됩니다.

### 5-5. Gateway VPC 엔드포인트 ⚠ 무료이니 반드시

콘솔 → **VPC** → 왼쪽 **엔드포인트** → **엔드포인트 생성**

| 항목 | 값 |
|---|---|
| 이름 | `assist-s3-gw` |
| 서비스 범주 | AWS 서비스 |
| 서비스 | 검색창에 `s3` → **`com.amazonaws.ap-northeast-2.s3`** 중 **유형이 `Gateway`** 인 것 |
| VPC | 기본 VPC |
| 라우팅 테이블 | 기본 라우팅 테이블 **체크** |
| 정책 | 전체 액세스 |

> ⚠ **반드시 `Gateway` 유형을 고르십시오.** 같은 이름으로 `Interface` 유형도 나오는데, 그건 **시간당 요금이 붙습니다.** Gateway 는 무료입니다.

이걸 만들면 S3 트래픽이 인터넷 게이트웨이를 안 거치고 VPC 안에서 처리됩니다. 무료이고 더 빠르고 더 안전합니다.

---

## 6. RDS PostgreSQL

> **생성에 약 10분 걸립니다.** 여기까지 설정을 넣고 **생성 버튼을 누른 뒤, 기다리지 말고 7장(EC2)으로 진행**하십시오.
>
> **2026-09-11 실물 기준으로 고쳤다** — 이름은 원안의 `assist-*` 가 아니라 운영 클러스터에 맞춘 `callguard-*` 다
> (`decisions/108`). 09-08 배포 때 RDS 를 만들지 않고 운영 시크릿에 Neon 을 임시로 넣었고, 운영 DB 연결은
> 그 뒤 **한 번도 성공하지 않았다**(파드 로그로 확인). 이 장부터 12-2 → 17 → 19 순서로 간다.

콘솔 → 상단 검색 `RDS` → 왼쪽 **데이터베이스** → **데이터베이스 생성**

### 6-1. 엔진

| 항목 | 값 | 이유 |
|---|---|---|
| 생성 방식 | **표준 생성** | ⚠ "손쉬운 생성" 은 보안 그룹을 고를 수 없습니다 |
| 엔진 유형 | **PostgreSQL** | `decisions/018` |
| 엔진 버전 | **17.x** 중 최신 | |
| 템플릿 | **개발/테스트** | 프로덕션 템플릿은 Multi-AZ 가 기본이라 요금이 두 배 |
| 가용성 및 내구성 | **단일 DB 인스턴스** | 이중화는 팀 프로젝트에 불필요 |

### 6-2. 설정

| 항목 | 값 |
|---|---|
| DB 인스턴스 식별자 | **`callguard-pg`** |
| 마스터 사용자 이름 | **`callguard`** |
| 자격 증명 관리 | **자체 관리** |
| 마스터 암호 | 직접 정한다 — **영문 대소문자와 숫자만, 16자 이상** |

> **암호에 특수문자를 피하는 이유**: 연결 문자열 `postgresql://user:암호@host:5432/db?sslmode=require` 에서
> `@ / : ? # %` 가 구분자·인코딩과 충돌해 파싱이 깨집니다. 12-2 는 이 암호를 JSON 안에 넣으므로 `" \` 도 깨집니다.
> 영문·숫자만 쓰면 어느 쪽도 걱정할 필요가 없습니다.
>
> ⚠ **암호를 지금 안전한 곳에 적어 두십시오.** 나중에 확인할 방법이 없고, 12장에서 씁니다.

### 6-3. 인스턴스 · 스토리지

| 항목 | 값 |
|---|---|
| DB 인스턴스 클래스 | **버스터블 클래스** → **db.t4g.micro** |
| 스토리지 유형 | **gp3** |
| 할당된 스토리지 | **20** GiB |
| 스토리지 자동 조정 | **활성화**, 최대 **60** GiB |

> **db.t4g.micro 도 버스터블입니다.** EC2 t3 와 같은 CPU 크레딧 구조를 가집니다. 평가 하네스가 DB 를 계속 두드리면 크레딧이 마르고, 그 지연이 레이턴시 측정에 섞여 들어옵니다. 22장에서 함께 기록하는 이유입니다.
>
> **micro 로 시작하십시오.** CloudWatch 의 `FreeableMemory` 가 200MB 밑으로 떨어지면 그때 `db.t4g.small` 로 올리면 됩니다(재시작 몇 분). 미리 올리는 것은 6주 $18 의 낭비입니다.

### 6-4. 연결 — 여기가 제일 중요합니다

| 항목 | 값 |
|---|---|
| 컴퓨팅 리소스 | **EC2 컴퓨팅 리소스에 연결 안 함** |
| VPC | **기본 VPC** (3장 보안 그룹과 같은 것) |
| DB 서브넷 그룹 | 기본값 |
| **퍼블릭 액세스** | **아니요** ← 전사 데이터가 들어감 (SEC-1) |
| VPC 보안 그룹 | **기존 항목 선택** → **`assist-db`** (3-2) |
| | 기본으로 붙어 있는 **`default` 는 X 로 지운다** |
| 가용 영역 | 기본 설정 없음 |

### 6-5. 추가 구성 ⚠ 접혀 있어서 놓치기 쉽습니다

화면 아래쪽 **추가 구성** 을 **펼치십시오.**

| 항목 | 값 |
|---|---|
| **초기 데이터베이스 이름** | **`assist`** ← **비워 두면 DB 가 안 만들어집니다**. 실물 값(2026-09-11 확인) — 식별자·사용자(`callguard`)와 다르다 |
| 자동 백업 | **활성화**, 보존 기간 **7일** |
| 삭제 방지 | **활성화** — 전사 데이터는 지우면 복구 경로가 없다 |
| 백업 창 | 한국 새벽이면 UTC **18:00** 시작 |
| 암호화 | 활성화 (기본) |
| 성능 개선 도우미 | 비활성화 (무료 티어 넘으면 요금) |

> **초기 데이터베이스 이름을 비우면**, RDS 인스턴스는 만들어지지만 그 안에 데이터베이스가 없습니다. 나중에 연결이 안 되는 가장 흔한 원인입니다.
>
> **자동 백업이 RDS 를 고른 이유의 전부입니다.** 끄면 EC2 에 직접 깔 걸 그랬다는 뜻이 됩니다.

### 6-6. 생성

**데이터베이스 생성** → 약 10분. **기다리지 말고 7장으로 넘어가십시오.**

완료되면 `callguard-pg` 클릭 → **엔드포인트** 를 적어 둡니다.

```
callguard-pg.xxxxxxxx.ap-northeast-2.rds.amazonaws.com
```

### 6-7. 연결 문자열 — SSL 이 강제된다

**RDS PostgreSQL 15 이상은 기본 파라미터 그룹에서 `rds.force_ssl = 1` 입니다.** 암호화하지 않은 연결은
`no pg_hba.conf entry ... no encryption` 으로 거절됩니다. 그래서 연결 문자열에 `sslmode=require` 를 붙입니다.

```
postgresql://callguard:<암호>@<엔드포인트>:5432/assist?sslmode=require
```

이 값은 저장소 어디에도 적지 않고 12-2 의 시크릿에만 넣습니다(SEC-2).
**사용자는 `callguard`, DB 는 `assist` 다** — 경로를 `/callguard` 로 쓰면 `database "callguard" does not exist` 로 붙지 않는다.

> ⚠ **RDS 는 「중지」해도 7일 뒤 AWS 가 자동으로 다시 켭니다.** EC2 자동 중지(21-1)는 RDS 를 멈추지 않으므로
> RDS 는 상시 과금입니다. 오래 쉬게 할 거면 스냅샷을 뜬 뒤 삭제합니다(삭제 방지를 먼저 끈다).

---

## 7. EC2 인스턴스

콘솔 → **EC2** → **인스턴스** → **인스턴스 시작**

### 7-1. 이름과 AMI

| 항목 | 값 | 이유 |
|---|---|---|
| 이름 | **`assist-gpu-01`** | 역할 + 번호. 특정 하위 기능 이름을 쓰지 않음 |
| AMI | **Deep Learning OSS Nvidia Driver AMI GPU PyTorch (Ubuntu 22.04)** | NVIDIA 드라이버 · CUDA · Docker · nvidia-container-toolkit 사전 설치 |
| 아키텍처 | **64비트(x86)** | T4 는 x86 전용 |

**AMI 찾는 법**: AMI 섹션에서 **AMI 검색** 클릭 → 검색창에 `Deep Learning OSS Nvidia Driver AMI GPU PyTorch` → **AWS AMI(빠른 시작)** 또는 **커뮤니티 AMI** 탭 → **Ubuntu 22.04** 버전 선택.

> **DLAMI 를 쓰는 이유**: 일반 Ubuntu AMI 에 NVIDIA 드라이버 + CUDA 툴킷 + container-toolkit 을 직접 깔면 **반나절이 날아갑니다.** 드라이버 버전과 CUDA 버전 조합이 어긋나면 더 걸립니다. DLAMI 는 전부 검증된 상태로 옵니다.
>
> AL2023 기반 DLAMI 도 있으나 Ubuntu 쪽 문서·커뮤니티 사례가 훨씬 많습니다.

### 7-2. 인스턴스 유형과 키 페어

| 항목 | 값 |
|---|---|
| 인스턴스 유형 | **g4dn.xlarge** (4 vCPU / 16 GiB / T4 16GB) |
| 키 페어 | **`assist-key`** (2장) |

> 목록에 g4dn 이 없거나 시작 시 오류가 나면 **1-1 의 GPU 할당량 문제**입니다.

### 7-3. 네트워크 설정

오른쪽 **편집** 클릭:

| 항목 | 값 |
|---|---|
| VPC | 기본 VPC |
| 서브넷 | 기본 설정 없음 (아무 퍼블릭 서브넷) |
| 퍼블릭 IP 자동 할당 | **활성화** |
| 방화벽 | **기존 보안 그룹 선택** → **`assist-web`** |

> ⚠ 기본값인 **"보안 그룹 생성"** 을 그대로 두면 3장 작업이 무의미해집니다. 반드시 **기존 선택** 으로 바꾸십시오.

### 7-4. 스토리지 구성

| 항목 | 값 | 이유 |
|---|---|---|
| 크기 | **150** GiB | 아래 산정 근거 |
| 볼륨 유형 | **gp3** | gp2 보다 20% 저렴하고 기본 성능이 더 좋음 |
| IOPS | **3000** (기본) | 추가 프로비저닝은 돈 낭비 |
| 처리량 | **125** MB/s (기본) | 동일 |
| **종료 시 삭제** | **비활성화** | 실수로 종료해도 데이터 보존 |
| 암호화 | **활성화** | 마스킹 전 전사가 잠시라도 디스크에 닿을 수 있음. 무료 |

**150 GiB 산정 근거**

| 항목 | 용량 |
|---|---|
| DLAMI 베이스 (드라이버 + CUDA 툴킷) | ~25GB |
| **CUDA 포함 PyTorch 도커 이미지** | **~12GB** ← 가장 큼 |
| Ollama 이미지 + EXAONE GGUF | ~2GB |
| HF 모델 5종 | ~8GB |
| Elasticsearch · Caddy · postgres 클라이언트 이미지 | ~2GB |
| 도커 빌드 캐시 (반복 빌드로 누적) | ~15GB |
| ES 인덱스 (조항 20개 + 임베딩) | ~1GB |
| 작업 여유 · 로그 | ~20GB |
| **소계 ~85GB + 여유 65GB** | **150GB** |

> **EBS 는 늘릴 수는 있어도 줄일 수 없습니다.** 처음에 잡아야 합니다.
>
> **인스턴스 스토어(125GB NVMe)는 이 화면에 표시되지 않습니다.** g4dn 에 물리적으로 내장돼 있고 자동으로 붙습니다. 무료입니다.

### 7-5. 고급 세부 정보

**고급 세부 정보** 를 펼칩니다.

| 항목 | 값 |
|---|---|
| **IAM 인스턴스 프로파일** | **`assist-ec2-role`** ← 4장 |
| **종료 방지** | **활성화** |
| 종료 동작 | **중지** (기본값) |

**종료 동작이 「중지」여야** 21장의 자동 종료 스크립트가 인스턴스를 삭제하지 않고 중지시킵니다.

### 7-6. 시작

오른쪽 **인스턴스 시작** → 1~2분 뒤 **인스턴스 상태 `실행 중`**, **상태 검사 `2/2 통과`**

---

## 8. 탄력적 IP

인스턴스를 껐다 켜면 퍼블릭 IP 가 바뀝니다. 매일 켜고 끌 것이므로 고정 주소가 필수입니다.

EC2 → 왼쪽 **네트워크 및 보안** → **탄력적 IP**

1. **탄력적 IP 주소 할당** → 그대로 **할당**
2. 생성된 주소 체크 → **작업** → **탄력적 IP 주소 연결**
3. 인스턴스 **`assist-gpu-01`** 선택 → **연결**

**이 주소를 적어 두십시오.** 18장에서 Cloudflare 에 넣습니다.

> ⚠ **연결돼 있어도 요금이 나갑니다** — 2024-02-01 부터 모든 퍼블릭 IPv4 가 시간당 $0.005(월 약 $3.6)입니다. 「연결돼 있으면 무료」는 옛 규칙입니다. 자동 할당 IP 를 써도 요금은 같으니 아낄 수 있는 항목이 아닙니다.
>
> **인스턴스를 중지해도 EIP 요금은 계속 나갑니다.** 정리할 때 반드시 릴리스하십시오.

---

## 9. 접속 · 디스크 · GPU 확인

```bash
ssh -i ~/.ssh/assist-key.pem ubuntu@<탄력적 IP>
```

처음엔 `Are you sure you want to continue connecting?` → `yes`

> ⚠ **DLAMI Ubuntu 의 사용자 이름은 `ubuntu`** 입니다. AL2023 의 `ec2-user` 가 아닙니다.

### 9-1. GPU 확인 — 가장 먼저

```bash
nvidia-smi
```

```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 5xx.xx    Driver Version: 5xx.xx    CUDA Version: 12.x            |
|-------------------------------+----------------------+----------------------+
|   0  Tesla T4            On   | 00000000:00:1E.0 Off |                    0 |
| N/A   30C    P8     9W /  70W |      0MiB / 15360MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

**`Tesla T4` 와 `15360MiB` 가 보이면 성공**입니다. 안 보이면 AMI 를 잘못 골랐습니다.

### 9-2. 인스턴스 스토어 마운트

```bash
lsblk
# nvme0n1  → 150G  EBS 루트
# nvme1n1  → 116G  인스턴스 스토어  ← 이것
```

재시작할 때마다 자동으로 준비되도록 systemd 서비스로 등록합니다.

```bash
sudo tee /etc/systemd/system/scratch-mount.service > /dev/null <<'EOF'
[Unit]
Description=Format and mount instance store
After=local-fs.target

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -c '\
  if [ -b /dev/nvme1n1 ]; then \
    if ! blkid /dev/nvme1n1 >/dev/null 2>&1; then mkfs -t xfs /dev/nvme1n1; fi; \
    mkdir -p /mnt/scratch; \
    mount /dev/nvme1n1 /mnt/scratch; \
    chown ubuntu:ubuntu /mnt/scratch; \
  fi'

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable --now scratch-mount.service
df -h /mnt/scratch
```

**넣을 것 / 넣지 말 것**

| 넣는다 (재생성 가능) | 넣지 않는다 |
|---|---|
| AI Hub 음성 다운로드·전처리 작업 공간 | 모델 가중치 (매일 8GB 재다운로드는 비현실적) |
| 8kHz 다운샘플링 결과 | ES 인덱스 |
| STT 오류 주입 중간 산출물 | 설정 파일 · 시크릿 |

> ⚠ **인스턴스를 중지하면 `/mnt/scratch` 내용이 전부 사라집니다.** 이건 고장이 아니라 사양입니다. 그 대신 무료이고 EBS 보다 빠릅니다.

### 9-3. 커널 파라미터 — Elasticsearch 필수

```bash
sudo tee /etc/sysctl.d/99-elasticsearch.conf > /dev/null <<'EOF'
vm.max_map_count=262144
vm.swappiness=1
EOF

sudo sysctl --system
sysctl vm.max_map_count   # 262144 확인
```

없으면 ES 컨테이너가 부팅 검사에서 죽습니다:
`max virtual memory areas vm.max_map_count [65530] is too low`

### 9-4. nvidia-container-toolkit 확인 ⚠ k3s 설치 전에

```bash
dpkg -l | grep nvidia-container-toolkit
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

두 번째 명령에서 GPU 정보가 나오면 도커에서 GPU 를 쓸 수 있는 상태입니다.

> ⚠ **이 확인을 k3s 설치 전에 해야 합니다.** k3s 는 설치 시점에 nvidia 런타임을 자동 감지해 containerd 설정에 넣습니다. 순서가 바뀌면 수동으로 고쳐야 합니다.

---

## 10. k3s 설치

```bash
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_EXEC="--disable=traefik --write-kubeconfig-mode=644" sh -
```

**`--disable=traefik` 이유**: 저장소에 이미 Caddyfile 이 있습니다. Traefik 으로 갈아타면 인증서 설정을 다시 해야 하고, GPU·쿠버네티스를 동시에 도입하는 지금은 변수를 늘릴 때가 아닙니다.

### 10-1. 확인

```bash
sudo systemctl status k3s
sudo k3s kubectl get nodes
```

```
NAME             STATUS   ROLES                  AGE   VERSION
ip-172-31-x-x    Ready    control-plane,master   30s   v1.3x.x+k3s1
```

### 10-2. kubectl 을 sudo 없이

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown ubuntu:ubuntu ~/.kube/config
echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc
source ~/.bashrc
kubectl get nodes
```

### 10-3. nvidia 런타임 감지 확인

```bash
sudo grep -A3 nvidia /var/lib/rancher/k3s/agent/etc/containerd/config.toml
```

`[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.nvidia]` 블록이 보이면 자동 감지 성공입니다. 안 보이면 9-4 를 다시 확인하고 `sudo systemctl restart k3s` 하십시오.

### 10-4. (선택) 로컬 PC 에서 kubectl

```bash
# 로컬 PC 에서
scp -i ~/.ssh/assist-key.pem ubuntu@<EIP>:~/.kube/config ~/.kube/assist.yaml

# macOS
sed -i '' 's/127.0.0.1/<EIP>/' ~/.kube/assist.yaml
# Linux
# sed -i 's/127.0.0.1/<EIP>/' ~/.kube/assist.yaml

export KUBECONFIG=~/.kube/assist.yaml
kubectl get nodes
```

3-1 에서 6443 을 내 IP 로 열어 둔 것이 이걸 위해서입니다.

---

## 11. GPU 를 여러 파드가 나눠 쓰게 만들기

**이 문서에서 가장 실수하기 쉬운 지점입니다.**

### 문제

쿠버네티스의 표준 방식은 NVIDIA device plugin 을 깔고 파드에서 `nvidia.com/gpu: 1` 을 요청하는 것입니다. 그런데 이 요청은 **배타적**입니다. GPU 가 1장이면 **파드 하나만 GPU 를 받고 나머지는 영원히 `Pending`** 에 걸립니다.

우리는 GPU 가 필요한 파드가 둘입니다.

- `ollama` — EXAONE 생성 (B-4)
- `server` — KoE5 임베딩(B-2) + KcELECTRA 분류(C-1~C-4) + NER(C-5)

표준 방식대로 하면 **둘 중 하나가 못 뜹니다.**

### 해법 — RuntimeClass 만 쓰고 device plugin 은 깔지 않는다

`nvidia.com/gpu` 리소스를 요청하지 않고 런타임만 지정하면 **모든 파드가 GPU 를 함께 봅니다.** CUDA 드라이버가 알아서 시분할합니다. VRAM 사용량이 4GB / 16GB 이므로 충돌하지 않습니다.

```bash
kubectl apply -f - <<'EOF'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata:
  name: nvidia
handler: nvidia
EOF

kubectl get runtimeclass
```

이후 GPU 가 필요한 파드에는 이렇게만 씁니다.

```yaml
spec:
  runtimeClassName: nvidia          # ← 이것만
  containers:
    - env:
        - { name: NVIDIA_VISIBLE_DEVICES, value: all }
        - { name: NVIDIA_DRIVER_CAPABILITIES, value: compute,utility }
      # resources 에 nvidia.com/gpu 를 쓰지 않는다   ← 중요
```

### 확인

```bash
kubectl run gpu-test --rm -it --restart=Never \
  --image=nvidia/cuda:12.4.0-base-ubuntu22.04 \
  --overrides='{"spec":{"runtimeClassName":"nvidia"}}' \
  -- nvidia-smi
```

T4 정보가 나오면 성공입니다.

> **더 정석적인 방법**: device plugin 에 time-slicing(`replicas: 4`)을 설정하면 GPU 하나를 논리적으로 4개처럼 쓸 수 있습니다. 발표 거리는 되지만 설정이 늘고 실익이 없습니다. 지금은 위 방식으로 두십시오.

---

## 12. 네임스페이스 · 시크릿 · 볼륨

### 12-1. 네임스페이스

```bash
kubectl create namespace assist
kubectl config set-context --current --namespace=assist
```

### 12-2. 시크릿 — `server-env` (RDS 접속 정보)

> **2026-09-11 실물 기준으로 고쳤다.** 원안은 `db-credentials` 에 `DATABASE_URL` 하나였으나, 실제 서버는
> `.env` 전체(16키)를 **`server-env` 하나로** 받는다(`infra/k8s/base/server.yaml` 의 `envFrom`).
> 키 목록·처음 만드는 명령은 `infra/k8s/base/secret.example.yaml` 에 있다. **저장소에 값을 커밋하지 않는다(SEC-2).**

**RDS 로 바꾸는 절차** — 운영 인스턴스 SSM 세션에서 한다. 암호는 `read -s` 로 받아 **명령줄·셸 이력에 남기지 않는다.**

> **SSM 웹 터미널에서 겪은 것 (2026-09-11 실제 수행).** ① 기본 셸이 `sh` 라 먼저 `bash` 를 친다. ② 여러 줄을 한 번에
> 붙이면 `sh` 가 붙여넣기 표시를 명령으로 읽어(`$'\E[200~': command not found`) **`K=` 줄이 사라진다** — 그러면 `$K get pods`
> 가 `get: command not found` 다. **한 줄씩 붙여 넣고** `echo "$K"` 로 확인한다. ③ 암호 입력은 아래 반복문으로 한다 —
> 길이가 0 이 아닌지 보고, patch 뒤 `… -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 -d | wc -c` 가 같은 숫자인지 본다.

```bash
K="sudo k3s kubectl -n callguard"

# ① 지금 시크릿을 떠 둔다 — 되돌리는 법이다(decisions/108). 확인이 끝나면 지운다
(umask 077; $K get secret server-env -o yaml > ~/server-env.backup.yaml)

# ② 값이 아니라 키 이름만 본다
$K get secret server-env -o go-template='{{range $k, $v := .data}}{{$k}}{{"\n"}}{{end}}'

# ③ DATABASE_URL 과 POSTGRES_* 를 「둘 다」 RDS 로 — 사용자 callguard · DB assist (6-5, 실물)
EP=callguard-pg.xxxxxxxx.ap-northeast-2.rds.amazonaws.com   # 6-6 의 엔드포인트
# 빈 값이면 다시 묻는다 — 웹 터미널(SSM)에 붙여 넣으면 줄바꿈이 딸려 와 read 가 빈 Enter 를 먼저 받는다
# (2026-09-11 실제로 암호가 빈 값으로 들어가 `fe_sendauth: no password supplied` 가 났다). 한 줄씩 붙여 넣는다
# 윈도 클립보드(CRLF)로 붙이면 끝에 \r 이 남아 patch JSON 이 깨진다 — 지운다(a5 세션 확인)
PGPW=; until [ -n "$PGPW" ]; do read -rsp 'RDS password: ' PGPW; echo; PGPW=${PGPW%$'\r'}; done; echo "length ${#PGPW}"
$K patch secret server-env --type merge -p "$(printf '{"stringData":{
  "DATABASE_URL":"postgresql://callguard:%s@%s:5432/assist?sslmode=require",
  "POSTGRES_HOST":"%s","POSTGRES_PORT":"5432","POSTGRES_DB_NAME":"assist",
  "POSTGRES_USER":"callguard","POSTGRES_PASSWORD":"%s"}}' "$PGPW" "$EP" "$EP" "$PGPW")"
unset PGPW

# ④ 서버가 읽지 않는 AWS 정적 키를 뺀다(decisions/108 ③). 키가 이미 없으면 이 명령만 실패한다
$K patch secret server-env --type json \
  -p '[{"op":"remove","path":"/data/AWS_ACCESS_KEY_ID"},{"op":"remove","path":"/data/AWS_SECRET_ACCESS_KEY"}]'

# ⑤ 시크릿은 파드가 뜰 때만 읽힌다 — 재시작한다
$K rollout restart deploy/callguard-server
$K rollout status deploy/callguard-server
```

**왜 두 벌을 같은 값으로 넣나.** 운영 이미지 `0.1.1` 은 `POSTGRES_*` 만 읽고, `0.1.2` 부터는 `DATABASE_URL` 을
먼저 읽는다(`server/apps/hub/adapter/outbound/postgres/connection.py`). 09-08~09-11 사고가 정확히
「두 규칙이 서로 다른 값을 보고 있었다」였다 — `POSTGRES_HOST` 는 비어 있고 `DATABASE_URL` 은 Neon 이었다.
두 값을 같게 두면 어느 이미지가 떠 있어도 같은 DB 에 붙는다. `POSTGRES_*` 쪽에는 `sslmode` 가 없지만
libpq 기본값 `prefer` 가 SSL 을 먼저 시도하므로 6-7 의 SSL 강제에 걸리지 않는다.

**검증 범위(2026-09-11)**: ③ 의 JSON 이 올바르고 연결 문자열이 호스트·사용자·DB·`sslmode=require` 로
파싱되는 것까지 로컬에서 확인했다. `kubectl patch` 자체는 그 머신에 kubectl 이 없어 돌려 보지 못했다 —
처음 쓸 때 ② 로 키가 바뀌었는지 본다.

**되돌리기**: `$K apply -f ~/server-env.backup.yaml && $K rollout restart deploy/callguard-server`.
17 · 19장 확인이 끝나면 백업을 지운다 — `shred -u ~/server-env.backup.yaml`.

> ⚠ **이 값은 인스턴스가 사라지면 같이 사라집니다.** 암호와 엔드포인트를 별도로 안전한 곳에 보관하시거나, SSM Parameter Store 에 넣어 두십시오.

### 12-3. 영속 볼륨

k3s 는 `local-path` 프로비저너를 기본 내장하고 있습니다. **EBS 루트(150GiB)에 저장되므로 인스턴스를 중지해도 살아남습니다.**

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: ollama-models, namespace: assist }
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: { requests: { storage: 20Gi } }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: hf-cache, namespace: assist }
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: { requests: { storage: 30Gi } }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: es-data, namespace: assist }
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: { requests: { storage: 20Gi } }
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata: { name: caddy-data, namespace: assist }
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path
  resources: { requests: { storage: 1Gi } }
EOF

kubectl get pvc -n assist
```

> `caddy-data` 는 Let's Encrypt 인증서 보관용입니다. `emptyDir` 로 두면 파드 재시작마다 인증서를 다시 받게 되는데, **Let's Encrypt 는 주당 발급 한도가 있습니다.**

---

## 13. 코드 클론 · 이미지 빌드

```bash
sudo mkdir -p /opt/assist && sudo chown ubuntu:ubuntu /opt/assist
git clone https://github.com/SeongYuna/call.solidbob.cloud.git /opt/assist/repo
cd /opt/assist/repo
```

### 13-1. 이미지 빌드 후 k3s 로 반입

**k3s 는 도커 데몬이 아니라 containerd 를 씁니다.** 로컬 도커로 구운 이미지는 자동으로 보이지 않으므로 명시적으로 넣어야 합니다.

```bash
cd /opt/assist/repo

# Elasticsearch (nori 플러그인 포함 커스텀 이미지)
docker build -t assist-es:local infra/elasticsearch/
docker save assist-es:local | sudo k3s ctr images import -

# FastAPI server
docker build -f infra/docker/server.Dockerfile -t assist-server:local .
docker save assist-server:local | sudo k3s ctr images import -

sudo k3s ctr images ls | grep assist
```

> **`ai/requirements.txt`(torch) 를 서버 이미지에 넣을지**는 확정 모델 배치에 달렸습니다. KoE5·KcELECTRA·NER 을 `server` 프로세스에서 직접 로드한다면 필요하고, 그러면 이미지가 ~12GB 로 커집니다. 150GiB 산정에 이미 반영돼 있습니다.

---

## 14. Ollama + EXAONE

### 14-1. 배포

```bash
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: ollama, namespace: assist }
spec:
  replicas: 1
  selector: { matchLabels: { app: ollama } }
  template:
    metadata:
      labels: { app: ollama }
    spec:
      runtimeClassName: nvidia
      containers:
        - name: ollama
          image: ollama/ollama:latest
          env:
            - { name: NVIDIA_VISIBLE_DEVICES, value: all }
            - { name: NVIDIA_DRIVER_CAPABILITIES, value: compute,utility }
            - { name: OLLAMA_HOST, value: "0.0.0.0:11434" }
            # 유휴 시 모델을 언로드하지 않는다 — 콜드 스타트가 p95 를 오염시킴
            - { name: OLLAMA_KEEP_ALIVE, value: "-1" }
            # 동시 요청이 GPU 를 나눠 쓰면 지연 분포가 흔들림
            - { name: OLLAMA_NUM_PARALLEL, value: "1" }
          ports: [{ containerPort: 11434 }]
          volumeMounts:
            - { name: models, mountPath: /root/.ollama }
          resources:
            requests: { memory: "2Gi", cpu: "500m" }
            limits:   { memory: "6Gi" }
      volumes:
        - name: models
          persistentVolumeClaim: { claimName: ollama-models }
---
apiVersion: v1
kind: Service
metadata: { name: ollama, namespace: assist }
spec:
  type: ClusterIP        # ← 내부 전용. NodePort/LoadBalancer 절대 금지
  selector: { app: ollama }
  ports: [{ port: 11434, targetPort: 11434 }]
EOF

kubectl rollout status deploy/ollama -n assist
```

### 14-2. EXAONE 내려받기

```bash
kubectl exec -n assist deploy/ollama -- \
  ollama pull hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF

kubectl exec -n assist deploy/ollama -- ollama list
```

812MB 이므로 1~2분이면 끝납니다.

### 14-3. 동작 확인 — `"think": false` 필수

```bash
kubectl exec -n assist deploy/ollama -- \
  curl -s http://localhost:11434/api/chat -d '{
    "model": "hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF",
    "messages": [{"role":"user","content":"대리 신청에 필요한 서류를 두 문장으로 정리해줘"}],
    "think": false,
    "stream": false
  }'
```

> ⚠ **`"think": false` 를 빠뜨리면 안 됩니다.** EXAONE 4.0 은 추론 모드가 있어서, 끄지 않으면 사고 과정 토큰이 먼저 나옵니다. **4.3절의 「첫 토큰 500ms」 를 재는 것이 무의미해집니다.**

### 14-4. GPU 점유 확인

```bash
nvidia-smi
```

`ollama` 프로세스가 1~2GB 를 쓰고 있으면 정상입니다. `0MiB` 이면 CPU 로 돌고 있는 것이므로 11장을 다시 확인하십시오.

### 14-5. 라이선스

EXAONE 은 **EXAONE AI Model License Agreement 1.2 — NC(비상업)** 입니다.

- 팀 프로젝트·포트폴리오 범위 안에서만 사용
- 발표 자료에 라이선스 명시
- 상업 서비스로 오해될 표현을 피할 것

---

## 15. Elasticsearch

```bash
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: elasticsearch, namespace: assist }
spec:
  replicas: 1
  selector: { matchLabels: { app: elasticsearch } }
  template:
    metadata:
      labels: { app: elasticsearch }
    spec:
      containers:
        - name: es
          image: assist-es:local
          imagePullPolicy: Never          # 로컬 반입 이미지
          env:
            - { name: discovery.type, value: single-node }
            - { name: xpack.security.enabled, value: "false" }   # 내부 전용
            - { name: ES_JAVA_OPTS, value: "-Xms2g -Xmx2g" }
          ports: [{ containerPort: 9200 }]
          volumeMounts:
            - { name: data, mountPath: /usr/share/elasticsearch/data }
          resources:
            requests: { memory: "3Gi", cpu: "500m" }
            limits:   { memory: "4Gi" }
      volumes:
        - name: data
          persistentVolumeClaim: { claimName: es-data }
---
apiVersion: v1
kind: Service
metadata: { name: elasticsearch, namespace: assist }
spec:
  type: ClusterIP
  selector: { app: elasticsearch }
  ports: [{ port: 9200, targetPort: 9200 }]
EOF

kubectl rollout status deploy/elasticsearch -n assist
```

> **`ES_JAVA_OPTS` 의 `2g` 는 GB 가 아니라 GiB(2³⁰ 바이트)입니다.** JVM 의 `g` 접미사는 항상 이진 단위입니다. `1g` 를 10억 바이트로 계산하면 약 73MB 를 잘못 세게 됩니다.
>
> 힙은 **물리 RAM 의 절반 이하**로 잡는 것이 원칙입니다. 나머지는 Lucene 이 파일 캐시로 씁니다.

### 확인

```bash
kubectl exec -n assist deploy/elasticsearch -- curl -s localhost:9200
kubectl exec -n assist deploy/elasticsearch -- curl -s "localhost:9200/_cat/plugins?v"
# analysis-nori 가 보여야 함
```

---

## 16. server + Caddy

### 16-1. FastAPI server

```bash
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: server, namespace: assist }
spec:
  replicas: 1
  selector: { matchLabels: { app: server } }
  template:
    metadata:
      labels: { app: server }
    spec:
      runtimeClassName: nvidia          # 임베딩·분류기가 GPU 를 씀
      containers:
        - name: server
          image: assist-server:local
          imagePullPolicy: Never
          env:
            - { name: NVIDIA_VISIBLE_DEVICES, value: all }
            - { name: NVIDIA_DRIVER_CAPABILITIES, value: compute,utility }
            - { name: ELASTICSEARCH_URL, value: "http://elasticsearch:9200" }
            - { name: OLLAMA_URL, value: "http://ollama:11434" }
            - { name: HF_HOME, value: /models }
          envFrom:
            - secretRef: { name: db-credentials }
          ports: [{ containerPort: 8000 }]
          volumeMounts:
            - { name: hf, mountPath: /models }
          resources:
            requests: { memory: "2Gi", cpu: "1" }
            limits:   { memory: "5Gi" }
      volumes:
        - name: hf
          persistentVolumeClaim: { claimName: hf-cache }
---
apiVersion: v1
kind: Service
metadata: { name: server, namespace: assist }
spec:
  type: ClusterIP
  selector: { app: server }
  ports: [{ port: 8000, targetPort: 8000 }]
EOF
```

### 16-2. Caddy — hostPort 로 80/443 직결

```bash
kubectl create configmap caddyfile -n assist \
  --from-file=Caddyfile=/opt/assist/repo/infra/docker/Caddyfile

kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata: { name: caddy, namespace: assist }
spec:
  replicas: 1
  selector: { matchLabels: { app: caddy } }
  template:
    metadata:
      labels: { app: caddy }
    spec:
      containers:
        - name: caddy
          image: caddy:2-alpine
          ports:
            - { containerPort: 80,  hostPort: 80  }
            - { containerPort: 443, hostPort: 443 }
          volumeMounts:
            - { name: conf, mountPath: /etc/caddy }
            - { name: data, mountPath: /data }
          resources:
            requests: { memory: "64Mi" }
            limits:   { memory: "256Mi" }
      volumes:
        - name: conf
          configMap: { name: caddyfile }
        - name: data
          persistentVolumeClaim: { claimName: caddy-data }
EOF
```

> ⚠ **`Caddyfile` 의 업스트림 주소를 확인하십시오.** compose 때 `server:8000` 이었다면 그대로 동작합니다 — 쿠버네티스에서도 같은 네임스페이스의 Service 이름으로 해석됩니다. 도메인도 `server.solidbob.cloud` 로 맞춰져 있어야 합니다.

---

## 17. DB 스키마

RDS 는 퍼블릭 액세스가 없으므로 **클러스터 안에서** 넣습니다.

> **2026-09-11 실물 기준으로 고쳤다.** 원안은 `postgres:17` 파드에 암호를 `--env` 로 넘기고
> `/opt/assist/repo` 의 파일을 읽었는데, 운영 인스턴스에는 **저장소 클론이 없다**(2026-09-09 확인).
> 그래서 **서버 파드 안에서, 서버가 쓰는 그 `DATABASE_URL` 로** 붙는다. 암호를 다시 입력할 일이 없고,
> **서버가 실제로 보는 값으로 확인한다** — 09-08~09-11 운영 DB 사고를 사흘간 가린 것이 「설정은 있다」는
> `/health` 값이었다(`decisions/108`). **12-2 를 먼저 끝낸다.**
>
> 아래 명령은 전부 2026-09-11 로컬 PostgreSQL 에 `kubectl exec` 만 빼고 그대로 돌려 확인했다.

### 17-1. 연결 확인

```bash
K="sudo k3s kubectl -n callguard"
$K exec deploy/callguard-server -- python -c "
import os, psycopg
c = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)
print(c.execute('select current_database(), current_user').fetchone(), 'ssl', c.pgconn.ssl_in_use)"
```

기대 출력: `('assist', 'callguard') ssl True` — DB `assist` · 사용자 `callguard`(6-5 실물)

| 증상 | 원인 |
|---|---|
| `KeyError: 'DATABASE_URL'` | 12-2 ③ 을 안 했거나 ⑤ 재시작을 안 했다 |
| 5초 뒤 타임아웃 | RDS 보안 그룹(`assist-db`)의 5432 인바운드 소스가 `assist-web` 이 아니다(3-2) · VPC 가 다르다 |
| `database "callguard" does not exist` | 연결 문자열의 DB 를 `/callguard` 로 썼다 — 실물은 **`/assist`** 다(6-7) |
| `database "assist" does not exist` | 6-5 에서 초기 데이터베이스 이름을 비웠다 |
| `password authentication failed` | 암호가 틀렸다 — 12-2 ③ 을 다시 한다 |
| `fe_sendauth: no password supplied` | 암호가 **빈 값**으로 들어갔다(2026-09-11 실제로 났다) — 12-2 ③ 반복문으로 다시 넣고 ⑤ 재시작. RDS 까지는 닿은 것이다 |
| `no pg_hba.conf entry ... no encryption` | `sslmode=require` 가 빠졌다(6-7) |

### 17-2. 스키마 적용

```bash
# 인스턴스에 클론이 없으므로 main 의 파일을 받는다(저장소 공개)
curl -fsSL https://raw.githubusercontent.com/SeongYuna/call.solidbob.cloud/main/db/schema.sql -o /tmp/schema.sql
head -1 /tmp/schema.sql   # "-- CallGuard PostgreSQL 스키마" 로 시작해야 한다

# 한 트랜잭션으로 넣는다 — 중간에 실패하면 아무것도 남지 않는다
$K exec -i deploy/callguard-server -- python -c "
import os, sys, psycopg
c = psycopg.connect(os.environ['DATABASE_URL'])
c.execute(sys.stdin.read()); c.commit(); print('적용 완료')" < /tmp/schema.sql

# 테이블 수 — 2026-09-11 기준 22
$K exec deploy/callguard-server -- python -c "
import os, psycopg
c = psycopg.connect(os.environ['DATABASE_URL'])
print(c.execute(\"select count(*) from pg_tables where schemaname='public'\").fetchone()[0], '테이블')"
```

**`schema.sql` 에는 `IF NOT EXISTS` 가 없다.** 이미 적용된 DB 에 다시 넣으면 첫 문장에서
`DuplicateTable: relation "customer" already exists` 로 멈추고 **아무것도 바뀌지 않는다**(2026-09-11 확인).
스키마를 바꾸려면 마이그레이션이 필요한데 아직 없다.

적용한 스키마의 커밋을 진행 기록에 남긴다 — 로컬에서 `git log -1 --format=%h origin/main -- db/schema.sql`.

---

## 18. DNS · HTTPS

Cloudflare → `solidbob.cloud` 존 → **DNS** → **레코드 추가**

| 항목 | 값 |
|---|---|
| 유형 | **A** |
| 이름 | **server** |
| IPv4 주소 | 8장의 **탄력적 IP** |
| 프록시 상태 | **DNS 전용 (회색 구름)** |

> ⚠ **주황 구름(프록시)을 켜면 안 됩니다.** Let's Encrypt 의 HTTP-01 챌린지가 Cloudflare 에서 끊겨 인증서를 못 받습니다 (`decisions/103`).

DNS 가 퍼지면(보통 1분 안) Caddy 가 알아서 인증서를 받습니다.

```bash
kubectl logs -n assist deploy/caddy | tail -20   # certificate obtained
```

---

## 19. 검증 체크리스트

> **2026-09-11 실물 기준으로 고쳤다** — 네임스페이스 `callguard` · ES 는 StatefulSet(`elasticsearch-0`) ·
> DB 확인은 17장처럼 서버 파드 안에서. **10 · 11번(DB 읽기·쓰기)을 새로 넣었다** — 09-08 배포는 9번까지
> 통과했는데 운영 DB 연결은 한 번도 되지 않았다. `/health` 의 `postgres_configured` 는 **설정이 있다는 뜻일 뿐**
> 연결된다는 뜻이 아니다(`decisions/108`).

운영 인스턴스 SSM 세션에서:

```bash
K="sudo k3s kubectl -n callguard"

# 1. 노드
sudo k3s kubectl get nodes

# 2. 파드 — 전부 Running / READY 1/1
$K get pods

# 3. GPU 점유 — GPU 인스턴스이고 GPU 파드를 올렸을 때만. 지금 infra/k8s/base/ 에는 GPU 파드가 없다
nvidia-smi

# 4. ES + nori
$K exec elasticsearch-0 -- curl -s "localhost:9200/_cat/plugins?v"

# 5. EXAONE 로드 — ollama 는 아직 infra/k8s/base/ 에 없다. 올린 뒤 확인한다
$K exec deploy/ollama -- curl -s http://localhost:11434/api/tags

# 6. RDS — 서버 파드가 보는 값으로. 기대: "22 테이블 · ssl True"
$K exec deploy/callguard-server -- python -c "
import os, psycopg
c = psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)
print(c.execute(\"select count(*) from pg_tables where schemaname='public'\").fetchone()[0], '테이블 · ssl', c.pgconn.ssl_in_use)"

# 7. S3 (IAM 역할이 붙어 있는지) — 원안 자원. 버킷이 없으면 건너뛴다
aws s3 ls s3://assist-<계정ID>-apne2/

# 8. 인스턴스 스토어 — g4dn 원안 항목. 없으면 건너뛴다
df -h /mnt/scratch
```

어디서든(밖에서):

```bash
B=https://server.solidbob.cloud

# 9. 외부 HTTPS
curl -s $B/health

# 10. DB 읽기 — 기대: 200
curl -s -o /dev/null -w '%{http_code}\n' $B/hub/knowledge-gaps

# 11. DB 쓰기 — 통화 → 전사(마스킹 후 저장) → 조회. 이미지 0.1.2 이상에서만(아래 ⚠)
C=test-deploy-$(date +%Y%m%d%H%M)
curl -fsS -X POST $B/hub/calls -H 'content-type: application/json' -d "{\"call_id\":\"$C\"}"
curl -fsS -X POST $B/hub/transcripts -H 'content-type: application/json' \
  -d "{\"call_id\":\"$C\",\"segment_id\":1,\"speaker\":\"customer\",\"text\":\"제 번호는 01012345678 입니다\",\"is_final\":true}"
curl -fsS $B/hub/calls/$C/transcript
```

9번의 기대 출력 (`0.1.2` 기준 — `0.1.1` 은 `trigger` 가 없는 3종):

```json
{"status":"ok","postgres_configured":true,"elasticsearch_configured":true,"spokes":["masking","closure_gate","retrieval","trigger"]}
```

**`spokes` 에 `retrieval` 이 있어야 검색이 꽂힌 것입니다.** 없으면 ES 가 안 떴거나 `ELASTICSEARCH_URL` 이 안 잡힌 것이며, **조용히 501 로 남는 것이 설계된 동작**이라 서버 자체는 정상으로 뜹니다 (`decisions/024`). 순서는 상관없습니다.

11번의 마지막 응답에서 볼 것 — `"text":"제 번호는 *********** 입니다"` · `"masked":[{"type":"P4",...}]` · `"total":"1"`.
**원래 번호가 보이면 SEC-1 위반이다 — 거기서 멈춘다.** 통화 생성 응답의 `"created":"true"` 는 처음 한 번만이고,
같은 `call_id` 로 다시 치면 `"false"` 다(멱등).

> ⚠ **11번은 `0.1.2` 이상에서만 통과한다.** `0.1.1` 의 전사 저장 코드는 발화를 `segment_id` 하나로 구분해서,
> 현재 `schema.sql`(PK `(call_id, segment_id)`)에서 `ON CONFLICT` 가 거부된다 — 500. RDS 문제가 아니라 어댑터 문제다.
>
> ⚠ **11번이 남긴 `test-` 행은 운영 DB 에 그대로 남는다.** 지우는 API 는 없다 — 필요하면 17장처럼 서버 파드에서
> `masking_event` → `transcript_segment` → `call` 순서로 지운다(외래키).
>
> 10 · 11번 명령은 2026-09-11 로컬 서버(현재 작업 트리 코드 + 현재 `schema.sql`)에서 그대로 쳐서 기대 출력을 확인했다.

---

## 20. AMI 스냅샷 — 반드시

**19장을 통과했으면 즉시 AMI 를 만드십시오.** CUDA 환경 + 모델 + k3s 세팅을 다시 하는 데 반나절이 걸립니다.

```
EC2 → 인스턴스 선택 → 작업 → 이미지 및 템플릿 → 이미지 생성
  이미지 이름: assist-gpu-baseline-YYYYMMDD
  재부팅 안 함: 체크 해제 (일관된 스냅샷을 위해 재부팅 권장)
```

- 비용: 실사용분 기준 GB당 월 약 $0.05. 85GB 사용 시 **월 약 $4**
- 인스턴스를 날려도 몇 분 만에 동일 환경 복원
- 인스턴스 등급을 바꿔야 할 때 재세팅 불필요

싼 보험입니다.

---

## 21. 자동 중지 · 일상 운영

### ⚠ 이 장이 예산을 결정합니다

| | 6주 비용 |
|---|---|
| 하루 8h × 주 5일 | **$142** |
| 24/7 | **$597 — 예산 초과** |

### 21-1. 자동 중지 설정 — 반드시

가장 흔한 예산 사고는 "끄는 걸 깜빡했다" 입니다.

```bash
(sudo crontab -l 2>/dev/null; echo "0 2 * * * /sbin/shutdown -h now") | sudo crontab -
sudo crontab -l
```

7-5 에서 종료 동작을 **중지** 로 설정했으므로, `shutdown` 은 인스턴스 삭제가 아니라 **중지**로 이어집니다. EBS 데이터는 안전합니다.

### 21-2. 작업 시작

```
EC2 → 인스턴스 → assist-gpu-01 → 인스턴스 상태 → 인스턴스 시작
```

1~2분 뒤:

```bash
ssh -i ~/.ssh/assist-key.pem ubuntu@<EIP>

df -h /mnt/scratch          # systemd 가 자동 마운트 (9-2)
kubectl get pods -n assist -w   # 파드가 다 뜰 때까지 1~2분
```

### 21-3. 작업 종료

```
EC2 → 인스턴스 상태 → 인스턴스 중지
```

| 상태 | EC2 | EBS | EIP | 인스턴스 스토어 |
|---|---|---|---|---|
| 실행 중 | 나감 | 나감 | 나감 | 유지 |
| **중지** | **멈춤** | 나감 | 나감 | **사라짐** |
| 종료 | 멈춤 | 설정에 따라 | 별도 해제 필요 | 사라짐 |

중지 상태에서도 EBS(월 약 $14) + EIP(월 약 $3.6) 는 계속 나갑니다. 정상이고 감수해야 하는 비용입니다.

### 21-4. 디스크 관리 — 주 1회

150GiB 도 반복 빌드로 찹니다.

```bash
df -h /
docker system df
docker builder prune -f          # 빌드 캐시만 정리
sudo k3s crictl rmi --prune      # 안 쓰는 컨테이너 이미지 정리
```

---

## 22. 측정 전용 인스턴스 (5주차)

**평가 하네스를 g4dn 위에서 돌리면 측정 도구가 측정 대상과 CPU 를 다툽니다.** 6.1절의 p50/p95/p99 가 오염됩니다.

측정할 때만 별도 인스턴스를 띄우십시오.

| 항목 | 값 |
|---|---|
| 유형 | **t3.micro** ($0.013/h) |
| AMI | Amazon Linux 2023 |
| 서브넷 | **g4dn 과 같은 AZ** ← 중요. 왕복 0.5~1ms |
| 보안 그룹 | `assist-web` |
| 용도 | 평가 하네스 실행, `server` 에 원격 호출 |

40시간 사용해도 **$0.5** 입니다. 이 금액으로 "측정 도구와 대상을 분리했다" 를 확보할 수 있으면 사는 게 맞습니다. 10.7절(통제 가능 구간과 아닌 구간 분리)과 서사가 이어집니다.

측정 시 함께 기록할 것:

```bash
# g4dn 쪽에서 측정 중 실행
mpstat 1 60 > /mnt/scratch/cpu-during-measurement.log
nvidia-smi --query-gpu=utilization.gpu,memory.used --format=csv -l 1 > /mnt/scratch/gpu.log
```

**RDS db.t4g.micro 도 버스터블입니다.** 평가 하네스가 DB 를 계속 두드리면 크레딧이 마르고, 그 지연이 레이턴시 측정에 섞여 들어옵니다. CloudWatch → RDS → `callguard-pg` → **`CPUCreditBalance`** 를 함께 기록하십시오.

---

## 트러블슈팅

| 증상 | 원인 · 해결 |
|---|---|
| 만든 게 목록에 안 보인다 | **리전이 서울이 아니다.** 오른쪽 위 확인 |
| g4dn 인스턴스를 만들 수 없다 | **GPU 서비스 할당량이 0** (1-1). 증설 요청 후 대기 |
| `nvidia-smi` 가 없다 | AMI 를 잘못 골랐다. DLAMI 여야 함 |
| `Permission denied (publickey)` | 사용자 이름이 틀렸다. DLAMI Ubuntu 는 **`ubuntu`** |
| `UNPROTECTED PRIVATE KEY FILE` | `chmod 400 ~/.ssh/assist-key.pem` 을 안 했다 |
| SSH 가 응답 없이 멈춤 | 보안 그룹 22번 소스가 지금 내 IP 가 아니다 |
| 파드가 `Pending` | `kubectl describe pod <이름>` → `Insufficient nvidia.com/gpu` 면 **11장을 안 했다.** `resources` 에서 `nvidia.com/gpu` 를 지울 것 |
| 파드가 `ImagePullBackOff` | `imagePullPolicy: Never` 누락 또는 `k3s ctr images import` 를 안 했다 |
| ES 파드가 계속 재시작 | `vm.max_map_count` (9-3). `kubectl logs` 확인 |
| ES 가 OOM 으로 죽는다 | `ES_JAVA_OPTS` 를 `-Xms1g -Xmx1g` 로 낮추거나 `limits.memory` 상향 |
| Ollama 가 CPU 로 돈다 | `nvidia-smi` 에 프로세스가 없다 → `runtimeClassName: nvidia` 누락 |
| 첫 토큰이 3초 넘게 걸린다 | ① `"think": false` 누락 ② `OLLAMA_KEEP_ALIVE=-1` 누락으로 콜드 스타트 |
| RDS 연결 실패 | ① RDS 보안 그룹(`assist-db`) 5432 소스가 `assist-web` 인지 ② **초기 데이터베이스 이름**을 비웠는지(그러면 DB 자체가 없다) · 연결 문자열 DB 가 실물 `assist` 인지 ③ 같은 VPC 인지 ④ `sslmode=require` 가 빠졌는지 — 증상별로는 17-1 의 표 |
| 인증서 발급 실패 | Cloudflare **주황 구름**이 켜져 있다 |
| kubectl 이 로컬에서 안 된다 | 6443 이 내 IP 로 열려 있는지. 공인 IP 가 바뀌었을 수 있다 |
| `/mnt/scratch` 가 비어 있다 | **정상.** 인스턴스 스토어는 중지하면 사라진다 |
| 디스크가 찼다 | `docker builder prune -f` + `k3s crictl rmi --prune` |

---

## 만들지 말 것

| 자원 | 만들면 | 대안 |
|---|---|---|
| **NAT Gateway** | 시간당 + 트래픽당 이중 과금, **월 $35+** | 기본 VPC 의 퍼블릭 서브넷 + 퍼블릭 IP |
| **EKS** | 컨트롤 플레인만 **6주 $102** | k3s |
| **ALB / NLB** | 월 $20+ | Caddy hostPort |
| **Kinesis Data Streams** | 월 $11 + **지연 추가** | WebSocket 직결. 아래 참고 |
| **ElastiCache** | 월 $12+ | 3.1절이 인메모리 LRU 로 확정 |
| **Multi-AZ RDS** | 요금 2배 | 단일 AZ |
| **EBS 프로비저닝 IOPS** | 불필요한 추가 요금 | gp3 기본 3,000 으로 충분 |
| **NVIDIA device plugin** | GPU 배타 할당 → 파드 하나만 뜸 | RuntimeClass (11장) |
| **직접 만든 VPC** | 프라이빗 서브넷 → NAT Gateway 필요 | 기본 VPC |

### Kinesis 를 쓰지 않는 이유

실시간 오디오 파이프라인 때문에 고려하기 쉬우나, 이 프로젝트에는 해롭습니다.

- **지연이 추가된다** — PUT→GET 왕복 수십~수백 ms 가 내부 처리 p95 1,000ms 예산 위에 그대로 얹힘
- **통제 불가 구간이 늘어난다** — 10.7절이 세운 차별점을 스스로 훼손
- **이점이 없다** — KDS 의 가치는 다중 소비자·재생·내구성인데, 우리는 소비자 1개, 재생 불필요, 지연 민감
- **투입자원 목록 밖 도구다** — 부록 C 7번 원칙 위반

---

## 되돌리기 · 정리

### k3s 이관이 막혔을 때

**docker-compose 경로를 지우지 마십시오.** k3s 만 걷어냅니다.

```bash
sudo /usr/local/bin/k3s-uninstall.sh
cd /opt/assist
cp repo/infra/docker/compose.prod.yml .
cp repo/infra/docker/env.prod.example .env
vi .env      # DATABASE_URL, SERVER_DOMAIN 등 채우기
docker compose -f compose.prod.yml up -d
```

GPU 를 쓰려면 compose 에 아래를 추가합니다.

```yaml
services:
  ollama:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - OLLAMA_KEEP_ALIVE=-1
      - OLLAMA_NUM_PARALLEL=1
    expose: ["11434"]      # ⚠ ports 로 열지 말 것
```

### 프로젝트 종료 시 정리

**끄는 것과 지우는 것은 다릅니다.** 중지해도 EBS·EIP·RDS 요금은 계속 나갑니다.

순서대로:

1. **S3** — 골든셋·평가 결과를 로컬로 내려받은 뒤 버킷 비우고 삭제
2. **RDS** — 최종 스냅샷 생성 후 삭제 (스냅샷 보관료는 소액)
3. **EC2** — 종료 방지 해제 → **종료(Terminate)**
4. **EBS 볼륨 삭제** ← 종료 시 삭제를 비활성화했으므로 **수동으로 지워야 함**
5. **탄력적 IP 릴리스** ← 안 하면 계속 과금
6. **AMI 등록 취소 + 연결된 스냅샷 삭제**
7. 보안 그룹 · 키 페어 · IAM 역할 · VPC 엔드포인트 삭제
8. **Cost Explorer 에서 다음 달 청구가 $0 인지 확인**

### 마감 후 전시용으로 남기려면

g4dn 을 24/7 로 켜면 월 $432 입니다. 어떤 예산으로도 감당이 안 됩니다.

| | 개발·측정 기간 | 전시 기간 |
|---|---|---|
| 구성 | 단일 g4dn, 필요 시 기동 | CPU 노드 상시 + GPU 온디맨드 |
| 생성 B-4 | EXAONE | **GPU 꺼져 있으면 추출형 요약으로 폴백** |
| 임베딩 | GPU | 인덱싱은 미리 끝내고 질의 임베딩만 캐시 |
| 월 비용 | — | ~$45 |

**k3s 매니페스트가 있으면 이 전환이 노드 추가 + `nodeSelector` 몇 줄입니다.** compose 로 짜 뒀다면 그때 전부 재작성해야 합니다. 지금 k3s 를 도입하는 가장 강한 명분이 이것입니다.

> ⚠ **폴백 경로는 현재 설계에 없습니다.** B-6("관련 문서 없음" 반환)과 같은 계열이므로, 6주차 생성 모듈을 만들 때 함께 넣어 두십시오. 나중에 붙이려면 훨씬 비쌉니다.

**가장 싼 전시 경로**는 인프라를 전부 내리고 **GitHub Pages 의 Jekyll 문서(무료) + 데모 녹화 영상**만 남기는 것입니다. 발표·면접 때만 30분 기동하면 됩니다. 마감 후 유지비가 월 $60 → 월 $4(AMI 스냅샷)로 떨어지고, **$240 가량이 남습니다.**

---

## 부록 A — 왜 이 구성인가

### A-1. 서버와 GPU 를 분리하지 않는다

임베딩이 `nlpai-lab/KoE5` 로 확정됐고, 베이스가 `multilingual-e5-large`(**335M, 1024차원**)입니다. base 급이 아니라 large 급입니다.

임베딩은 **B-2 하이브리드 검색의 매 질의마다** 돕니다. 2 vCPU 로 돌리면 질의당 80~200ms 이고, **4.3절 검색 예산 150ms 를 임베딩 하나가 전부 먹습니다.** 따라서 임베딩도 GPU 에 있어야 합니다.

그러면 분리 구성의 원래 이점(GPU 를 6주차에만 켠다)이 사라집니다.

| 주차 | GPU 필요 |
|---|---|
| 4주차 dense_vector + RRF | 임베딩 → **필요** |
| 5주차 오류율 0~20% 곡선 | 구간마다 전체 재임베딩 → **필수** |
| 6주차 생성 + 분류기 | **필수** |

**분리해도 GPU 가동 시간이 통합과 거의 같아지므로, CPU 노드 요금이 순수 추가 비용으로만 남습니다.**

| | 통합 | 분리 (t3.medium) | 분리 (c7i.large) |
|---|---|---|---|
| EC2 6주 | **$166** | $203 | $263 |
| 측정 신뢰성 | ✅ 전용 CPU | ❌ 버스터블 크레딧 | ✅ |
| k3s | 단일 노드 | **멀티노드 + PVC 문제** | 동일 |

### A-2. EKS 대신 k3s

| | EKS | k3s |
|---|---|---|
| 컨트롤 플레인 | $0.10/시간 → **6주 $102** | **$0** |
| 최소 노드 | 사실상 2대+ | 1대 |
| GPU 설정 | 노드그룹 + device plugin + taint | RuntimeClass 한 개 |
| 세팅 시간 | 반나절~하루 | 30분 |
| 인그레스 | ALB Controller (월 $20+) | Caddy 유지 |

**k3s 는 CNCF 인증 쿠버네티스입니다.** kubectl·매니페스트·Helm 전부 동일하고, 산출물(YAML)이 EKS 와 같습니다. 면접에서 "왜 EKS 를 안 썼나" 에 **"예산 $400 에 컨트롤 플레인만 $102 가 나가고, 단일 노드라 관리형의 이점이 없어서"** 라고 답하는 편이 판단력의 근거가 됩니다.

3.1절 투입자원 목록의 `Kubernetes | 배포 | 선택` 을 충족하면서 예산을 지키는 유일한 경로입니다.

### A-3. 버스터블(t3)을 주 노드로 쓰지 않는 이유

T3 는 vCPU 당 baseline 20%, 시간당 24 크레딧 적립입니다. 크레딧이 마르면 두 갈래입니다.

| 모드 | 동작 | 비용 |
|---|---|---|
| standard | CPU 20% 로 강제 제한 | 추가 없음 |
| **unlimited** (T3 기본값) | 느려지지 않음 | **잉여 vCPU-시간당 $0.05** |

t3.medium 을 2 vCPU 100% 로 돌리면 시간당 잉여가 1.6 vCPU-시간, **$0.08/h** — **인스턴스 요금($0.052/h)보다 크레딧 요금이 더 큽니다.**

금액보다 심각한 것은 **같은 벤치마크를 두 번 돌렸을 때 값이 달라진다**는 점입니다. 6.2절 2번("여러 번 실행한 값 중 최저치를 기준선으로 고정")을 지키려 해도, 그 최저치가 CPU 성능이 아니라 크레딧 잔량을 반영하게 됩니다.

**g4dn 은 버스터블이 아니므로 이 문제가 없습니다.**

### A-4. 도입 순서에 대한 경고

GPU · 쿠버네티스 · S3 를 한 번에 도입하는 것은 **인프라 측면에서는 맞습니다** — 나중에 얹으면 재작업이 훨씬 큽니다.

다만 실패 시 후퇴 경로를 반드시 남기십시오.

1. 이 문서 9~19장으로 **k3s 위에 전체 스택을 띄워 검증을 통과시킨다**
2. 막히면 「되돌리기」의 compose 경로로 즉시 후퇴한다
3. 인프라가 안정된 뒤에 기능 작업을 얹는다

### A-5. 인프라 말고 순서에 대해

**기능 검증 순서는 인프라와 별개입니다.** 지금 골든셋이 13건이고, 3주차 최우선 과제가 150건 재확장입니다. 6주차 마지막 태스크가 "코어 기준선 통과 확인 — 여기서 F·G·H·I 착수 여부가 갈린다" 인데, **그 기준선이 아직 존재하지 않습니다.**

인프라를 다 세워도 **150건 골든셋 없이는 5·6주차 산출물을 측정할 수 없습니다.** GPU 를 띄워 놓고 "돌아는 가는데 얼마나 좋은지는 모르는" 상태로 시간이 가면, 그건 GPU 가동 시간이 곧 돈이라는 점에서 예산 문제이기도 합니다.

**인프라 세팅과 병렬로 골든셋 150건을 밀어붙이십시오.** 7.1절이 골든셋을 4인 공동으로 배정해 뒀으니, 인프라는 정성윤 님이, 골든셋은 나머지 셋이 동시에 가는 형태가 맞습니다.

---

## 부록 B — 결정 기록에 남길 것

이 문서의 결정 중 나중에 누가 무심코 뒤집을 수 있는 것들입니다. `_project/decisions/` 에 근거와 되돌리는 법을 남겨 두십시오.

| # | 결정 | 뒤집혔을 때 |
|---|---|---|
| 1 | **GPU 인스턴스 상시 가동 금지** | 6주 $142 → $597. 예산 초과 |
| 2 | **EKS 대신 k3s** | 6주 $102 추가 |
| 3 | **NVIDIA device plugin 을 쓰지 않는다** | 파드 하나만 GPU 를 받고 나머지 Pending |
| 4 | **Ollama 포트를 노출하지 않는다** | 인증 없는 GPU 를 인터넷에 공개 |
| 5 | **`"think": false` 고정** | 첫 토큰 지연 측정이 무의미해짐 |
| 6 | **`OLLAMA_KEEP_ALIVE=-1`** | 콜드 스타트가 p95 에 섞임 |
| 7 | **Kinesis · NAT Gateway · ALB 도입 금지** | 통제 불가 지연 구간 추가 또는 월 $35+ |
| 8 | **A-5 평가셋 크기 상한** (별도 확정 필요) | STT 비용의 유일한 변동 요인. 100시간 무분별 처리 시 약 $144 |
| 9 | **EBS 루트 150GiB** | 줄일 수 없음. 작게 잡으면 CUDA 이미지에서 막힘 |
