---
title: "AWS 자원 정리 — RDS 권장 사항 2건 · Enhanced Monitoring · 7월 잔재"
assignee: "정성윤"
role: "infra"
status: "cancelled"
sprint: 4
priority: 4
date: 2026-09-14
requirement:
  - "SEC-2"
  - "COST-1"
---

## 무엇을

2026-09-14 콘솔 실측에서 나온 «봐야 할 것» 셋을 닫는다.
런북 이름 정정(같은 날)은 끝났고 남은 것은 **자원 자체**다.

## 할 것

- [x] **RDS 권장 사항 2건의 내용 확인** — 「퍼블릭 액세스 허용」이거나 「백업 보존 0일」이면 즉시 조치 대상이다.
      RDS 를 고른 이유가 **백업 하나**였다(`w3-aws-deploy`) — 보존이 0이면 고른 이유가 사라진다
- [x] **`rds-monitoring-role` 이 있다 = Enhanced Monitoring 이 켜져 있다.** 의도한 것인지 확인하고,
      아니면 끈다. 소액이지만 CloudWatch Logs 로 계속 나간다(COST-1)
- [ ] **7월 잔재 정리** — 두 번째 VPC `vpc-0a2f05f0b6898780f` · 보안 그룹 `admin-security` · `launch-wizard-1`(07-24 생성).
      인스턴스가 1대뿐이라 **과금은 없다.** 지우는 이유는 돈이 아니라 **자원 목록이 읽히게 하는 것**이다 —
      09-14 의 이름 어긋남 2건도 목록이 지저분해서 늦게 찾았다
- [ ] 지운 뒤 런북 22장(점검 명령) 출력과 대조

## 왜 지금

- 인스턴스 역할로 `aws rds describe-*` 가 AccessDenied 인 것은 **정상이다.** 워크로드 역할에 계정 전역 조회 권한을
  붙이면 인스턴스가 뚫렸을 때 정찰 범위만 넓어진다. 그래서 이 점검은 **사람 자격증명(콘솔)으로** 한다 —
  자동화하지 않는 이유가 여기 있다
- 지우는 작업이라 **되돌릴 수 없다.** 지우기 전에 각 자원이 무엇에 붙어 있는지 콘솔에서 한 번씩 본다

## 완료 조건

RDS 권장 사항이 0건이거나 «의도한 것»으로 판단 근거가 남아 있고, 7월 잔재가 목록에서 사라진다.

## 2026-09-21 읽기 전용 확인 (정성윤) — 급한 둘은 해당 없음

| 확인 | 값 | 판단 |
|---|---|---|
| RDS 백업 보존 | **7일** | 즉시 조치 대상 아님 |
| RDS 퍼블릭 접근 | **꺼짐** | 즉시 조치 대상 아님 |
| RDS 저장소 암호화 | 켜짐 | — |
| Enhanced Monitoring | **꺼짐**(`MonitoringInterval 0`) | `rds-monitoring-role` 은 남아 있지만 비용은 안 나간다 |
| RDS 권장 사항 | **2건 · 둘 다 informational** — `enhanced_monitoring_off` · `multi_az_instance` | 둘 다 「더 켜라」는 권고다. 켜면 돈이 든다 → **안 한다**로 닫을 수 있다 |

**7월 잔재** — 과금은 없다. 지우는 이유는 목록이 읽히게 하는 것이다.
- 두 번째 VPC `vpc-0a2f05f0b6898780f`(10.0.0.0/16) — 서브넷 1 · 인터넷 게이트웨이 1 · 라우트 테이블 2(메인 1) · **네트워크 인터페이스 0** · NAT 0 · 엔드포인트 0. 안에 보안 그룹 `admin-security`
- 기본 VPC 의 `launch-wizard-1` — 어느 네트워크 인터페이스에도 붙어 있지 않다
- `launch-wizard-2` 는 **건드리지 않는다** — `decisions/116` ⑥ 이 하지 않기로 했다

지우는 명령 — **실행하지 않았다.** 되돌릴 수 없으니 콘솔에서 한 번 더 보고 한 줄씩 친다(순서가 있다 — 의존하는 것부터).
```bash
R="--region ap-northeast-2"
aws ec2 delete-security-group $R --group-id sg-0037a91800c29936d          # launch-wizard-1 (기본 VPC)
aws ec2 delete-security-group $R --group-id sg-0f1a2dfb593e9548b          # admin-security
aws ec2 delete-subnet $R --subnet-id subnet-021169b3144ecb757
aws ec2 delete-route-table $R --route-table-id rtb-0cf14e9e6721be9f6      # 메인이 아닌 쪽. 메인은 VPC 와 함께 지워진다
aws ec2 detach-internet-gateway $R --internet-gateway-id igw-08af6f27a9a8cbab8 --vpc-id vpc-0a2f05f0b6898780f
aws ec2 delete-internet-gateway $R --internet-gateway-id igw-08af6f27a9a8cbab8
aws ec2 delete-vpc $R --vpc-id vpc-0a2f05f0b6898780f
```

## 2026-09-30 — 읽기 전용 확인 (정성윤) · 삭제만 남았다

- **RDS 권장 2건의 내용** — `describe-db-recommendations`(09-30): ① Enhanced Monitoring 꺼짐 ② Multi-AZ 아님. **둘 다 informational** 이고 「퍼블릭 액세스」·「백업 0일」이 아니다
  (`PubliclyAccessible False` · `BackupRetentionPeriod 7`). 즉시 조치 없음 — 둘 다 **안 한다**(Multi-AZ 는 비용 2배, Enhanced Monitoring 은 CloudWatch Logs 과금).
- **`rds-monitoring-role`** — 인스턴스 `MonitoringInterval 0` · `MonitoringRoleArn None`. **역할만 있고 Enhanced Monitoring 은 꺼져 있다**(비용 0). 역할은 7월 잔재와 같이 지워도 되고 두어도 된다.
- **7월 잔재 삭제** — 되돌릴 수 없어 사용자 확인 뒤 한다. 명령은 위 그대로다(VPC `vpc-0a2f05f0b6898780f` · `admin-security` · `launch-wizard-1`). 지운 뒤 런북 22장 점검 명령과 대조.

## 2026-10-01 — cancelled (사용자 결정 「티켓 닫아」)

7월 잔재는 지우지 않는다. 운영과 무관한 자원이고 비용이 거의 없다(RDS 권장 2건은 informational, Enhanced Monitoring 은 꺼져 있음). 종료 정리(`w8-project-closeout`)에서 계정의 자원을 한 번에 내릴 때 같이 사라진다 — 그때 이 티켓의 명령을 쓴다.
