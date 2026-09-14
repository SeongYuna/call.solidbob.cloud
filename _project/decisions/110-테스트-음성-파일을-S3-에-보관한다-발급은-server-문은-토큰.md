# 110 — 테스트 음성 파일을 S3 에 보관한다. 발급 지점은 `server`, 문은 토큰이다

**날짜**: 2026-09-14
**작성**: 정성윤 (브랜치 `PM`)
**관련**: `decisions/105`(한 컨테이너·한 도메인) · `108`(운영 DB·AWS 정적 키 제거) ·
`109`(게이트웨이는 하나 · 문마다 토큰) · `302`(담당 잠금 해제) ·
런북 `docs/infra-runbook.md` 4장(IAM)·5장(S3) · 티켓 [w4-audio-upload-store](/backlog/w4-audio-upload-store/)

## 맥락

**테스트 음성으로 파이프라인을 돌리는 경로는 이미 셋 있다** — `scripts/stream_wav.ts`(파일 재생) ·
`GET /gateway/dev`(브라우저 음성 인식) · `WS /gateway/ingest`(오디오 생산자). 셋 다 **흘려보내고 끝난다.**

없던 것은 **보관**이다. 올린 파일이 남아 있어야 나중에 다시 듣고, 같은 음성으로 재처리해 비교할 수 있다.
그리고 **팀원 넷이 각자 할 수 있어야 한다**(2026-09-14 사용자 지시) — 정성윤 한 사람의 노트북에서만
되는 절차는 팀 도구가 아니다.

**S3 는 준비돼 있고 코드가 0줄이다.**

| 확인 | 결과 |
|---|---|
| 버킷 `assist-apne2` | 2026-09-08 생성. 2026-09-14 기준 **객체 0개** |
| IAM 인라인 정책 `assist-s3-access` | 2026-09-14 부착 — 그 전에는 `no identity-based policy allows the s3:ListBucket action` 이었다 |
| EC2 에서 `aws s3 ls s3://assist-apne2/` | 성공(빈 출력) — 런북 19-7 이 처음으로 통과 |
| 저장소의 S3 코드 | `origin/main`·`frontend`·`server`·`ai` 네 브랜치에서 `boto3\|presign\|s3_client\|assist-apne2` **0건** |

## 선택지

| | 방법 | 문제 |
|---|---|---|
| A | 브라우저에 AWS 키를 넣는다 | **금지**(SEC-2). 키가 공개 번들에 들어가는 순간 그 페이지를 본 누구나 우리 계정에 무한정 올리고 요금을 태운다 |
| B | 팀원마다 IAM 사용자 + AWS CLI | 키 4벌을 나눠 주고 회수해야 한다. 회수 절차가 없다. 프론트엔드 쪽에 CLI 전제를 강요한다 |
| **C** | **`server` 에 presign 발급 지점 + 브라우저 페이지, 문은 토큰** | 코드가 는다. 발급 지점이 뚫리면 익명 업로드 프록시가 된다 → 4·5번으로 막는다 |
| D | 게이트웨이에 붙인다 | 게이트웨이는 DB 를 쓰지 않는다(`secret.example.yaml`: `server-env` 를 받지 않는다). 보관 목록은 DB 가 필요하다 |

## 결정

**C.** 이유는 **`109` 가 이미 같은 문제를 같은 모양으로 풀었기 때문이다** — 브라우저가 직접
민감한 자원에 닿지 않게 하고, 문마다 비밀 토큰을 요구하고, 토큰이 없으면 전부 거절한다.
팀원은 **주소 하나와 토큰 하나**만 받으면 된다. 그게 「팀원들도 할 수 있어야 한다」의 최소 비용이다.

1. **`server/apps/uploads/` 슬라이스.** 요구 ID **`A-6` — 녹음 파일 입력 · 보관.**

   > **정정 (2026-09-14, 같은 날).** 위 「`server/apps/uploads/` 슬라이스」는 **틀린 전제**였다 —
   > `masking`·`blacklist` 는 **HTTP 가 없는 규칙 스포크**(`domain` + `adapter/outbound` 뿐)이고
   > **라우터는 전부 `hub` 에 있다**(`server/CLAUDE.md` §2, 실측). `.importlinter` 주석도 스포크를
   > *「규칙 기반 판정」* 으로 한정한다. 업로드는 판정이 아니라 **요청 경로**라 `hub` 의 수직 슬라이스가 맞다.
   > 실제로 만든 위치: `hub/app/dtos/upload_dto.py` · `app/ports/{input,output}/upload_*` ·
   > `app/use_cases/upload_interactor.py` · `adapter/outbound/s3/` · `adapter/inbound/api/{schemas,v1}/upload_*` ·
   > `dependencies/upload_provider.py`. 새 root package 가 없으므로 `root_packages`·계약 1 `containers` 는
   > 건드리지 않았고, 대신 **계약 3 에 `boto3` 를 금지 목록으로 넣었다** — `hub.app` 은 S3 를 모른다.
   > 원문은 결정 당시의 판단이라 지우지 않는다(절대 원칙 8).
   A 블록이 「오디오가 시스템에 들어오는 경로」를 담당한다(A-1 스트리밍 · A-3 브라우저 전달 · A-5 통번역).
   파일 업로드는 같은 블록의 입력 방식 하나다. `SEC-1`·`SEC-2`·`COST-1` 이 함께 걸린다.
   ⚠ 새 ID 를 기획서에 추가하는 것이므로 이 기록이 그 경로다(`CLAUDE.md` §1 문서 우선순위).
2. **presigned `POST` 를 쓴다. `PUT` 이 아니다.**
   POST 정책에는 `content-length-range` 조건을 걸 수 있어 **크기 상한을 서버가 강제한다.**
   presigned PUT 은 크기를 못 건다 — 링크 하나로 수십 GB 를 올릴 수 있다. 이게 두 방식의 실질적 차이다.
3. **키는 서버가 만든다.** `uploads/<YYYY-MM-DD>/<무작위>-<정규화한 파일명>`.
   **클라이언트가 준 경로를 그대로 쓰지 않는다** — `../` 나 `datasets/` 를 넣어 다른 프리픽스를 덮어쓸 수 있다.
4. **문은 `UPLOAD_TOKEN` 이고 `Authorization: Bearer` 로만 받는다.** URL 에 비밀을 싣지 않는다(`109` 3번).
   **토큰이 설정돼 있지 않으면 전부 거절한다(fail-closed)** — 게이트웨이와 같은 원칙이다.
   > **잠기지 않은 발급 지점은 익명 업로드 프록시다.** 「브라우저에 키가 없으니 안전하다」는 틀렸다 —
   > 막으려던 시나리오(아무나 올리고 요금을 태운다)가 그대로 재현된다.
5. **만료는 5분**, 프리픽스는 `uploads/` 로 **서버가 고정**한다.
6. **별도 버킷을 만들지 않는다.** IAM 인라인 정책이 `arn:aws:s3:::assist-apne2` **한 버킷으로 좁혀져** 있어
   버킷을 늘리면 정책을 또 고쳐야 하고, 버킷 이름은 전역 고유라 하나 더 잡으면 영구히 묶인다.
   「테스트 파일이 데이터셋 정리에 딸려간다」는 걱정은 프리픽스로 이미 해소된다 —
   수명 주기 규칙 `datasets-to-ia` 는 **`datasets/` 접두어 한정**이라 `uploads/` 에는 걸리지 않는다(런북 5-4).
7. **CORS 허용 오리진은 `https://server.solidbob.cloud` 하나.** `*` 를 쓰지 않는다.
   ngrok 도 필요 없다 — 그 주소는 이미 HTTPS 다(`109`).
8. **버킷의 퍼블릭 액세스 차단은 그대로 「모두 차단」이다.** presigned 요청은 **서명된 인증 요청**이라
   차단 설정과 무관하게 동작한다. 이걸 오해해 차단을 푸는 실수가 흔한데, 전사·음성이 들어가는 버킷이다(SEC-1).
9. **다시 듣기는 GET presign 으로 한다.** 객체를 공개로 만들지 않는다. 목록·재생 링크 모두 같은 토큰 뒤에 둔다.
10. **자체 통화 녹음은 올리지 않는다(절대 원칙 7).** AI Hub 등 저작권·개인정보가 해결된 출처만 올린다.
    `.gitignore` 가 `*.wav`·`*.mp3` 를 막는 것과 같은 이유이며, S3 는 그 예외가 아니다.

## 해결됨 — 파드는 인스턴스 역할을 그대로 쓴다 (2026-09-14 실측)

**추가 자격증명이 필요 없다.** 운영 파드에서 IMDSv2 로 확인했다:

```
토큰 발급 성공
역할: callguard-ec2-role
```

즉 **hop limit 인상도, 전용 IAM 사용자도 불필요**하다 — `108` ③(AWS 정적 키 제거)을 되돌리지 않는다.
`server-env` 에 넣는 것은 `S3_BUCKET`·`AWS_REGION`·`UPLOAD_TOKEN`·`UPLOAD_MAX_BYTES` 넷뿐이고 **비밀은 토큰 하나**다.

> ⚠ **첫 확인 명령은 틀렸다.** IMDSv1 방식(토큰 없이 GET)이라 `HTTP Error 401` 이 났는데,
> 이건 「막혔다」가 아니라 **이 인스턴스가 IMDSv2 를 강제한다**(`HttpTokens: required`)는 뜻이었다.
> 401 이 온 것 자체가 요청이 IMDS 에 **닿았다**는 증거다 — 막혔으면 타임아웃이다.
> 보안상으로는 좋은 설정이다(IMDSv1 이 열려 있으면 SSRF 한 방에 자격증명이 샌다).

아래는 타임아웃이었을 때를 대비해 적어 두었던 갈림길이다. **해당 없음으로 닫는다.**

### (닫힘) 원래의 미해결 ⚠

**이 기록으로 정하지 못했다. 실측이 먼저다.**

`108` ③ 으로 **`server-env` 에서 AWS 정적 키를 제거했다.** 지금 파드에는 자격증명이 없다.
인라인 정책은 **EC2 인스턴스 역할**(`callguard-ec2-role`)에 붙어 있는데, 파드가 그걸 쓰려면
IMDS(`169.254.169.254`)에 닿아야 한다. **EC2 기본 hop limit 이 1** 이라 컨테이너 네트워크를
한 번 더 거치는 파드는 막히는 것이 일반적이다. k3s 에는 EKS 의 IRSA 같은 장치가 없다.

```bash
sudo k3s kubectl -n callguard exec deploy/callguard-server -- \
  python -c "import urllib.request as u; print(u.urlopen('http://169.254.169.254/latest/meta-data/iam/security-credentials/',timeout=2).read()[:60])"
```

| 결과 | 선택 |
|---|---|
| 역할 이름이 찍힌다 | 그대로 쓴다. 추가 자격증명 없음 — **가장 좋다** |
| 타임아웃 | ① hop limit 을 2 로 올린다 → **모든 파드가 노드 역할을 얻는다**(게이트웨이가 뚫리면 S3 까지 간다) · ② `uploads/` 에만 `PutObject`/`GetObject` 를 주는 **전용 IAM 사용자** 키를 `server-env` 에 넣는다 → `108` ③ 을 부분적으로 되돌리는 것이라 **별도 결정 기록이 필요하다** |

**코드는 어느 쪽이든 같다** — boto3 기본 자격증명 체인이 환경변수와 IMDS 를 모두 본다. 갈리는 것은 배포 설정뿐이다.

## 되돌리는 법

- **기능만 끄기**: `server-env` 에서 `UPLOAD_TOKEN` 을 지우고 재시작한다. fail-closed 라 발급 지점이 전부 거절한다(4번).
- **통째로 되돌리기**: `server/apps/uploads/` 삭제 · `.importlinter` 에서 슬라이스 이름 제거 ·
  `server/requirements.txt` 에서 `boto3` 제거 · `kustomization.yaml` 의 `newTag` 를 올려 재배포.
- **올린 파일 지우기**: `aws s3 rm s3://assist-apne2/uploads/ --recursive`.
  ⚠ 버킷 **버전 관리가 비활성화**(런북 5-1)라 되살릴 수 없다.
- **CORS 규칙 제거**: 브라우저 업로드만 막히고 서버 경로는 그대로 돈다.
