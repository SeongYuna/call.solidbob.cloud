# 성윤님께 — 음성 데이터셋·모델을 직접 받으시는 법 (2026-09-22)

> 비공개(`_project/` — 사이트에 안 올라감). 작성: 류준
> 관련: `decisions/110`(S3 업로드·IAM) · `121`(모델은 전용 GPU EC2) · `207`(생성 모델 kanana) ·
> `210`(모델을 학습하지 않는다) · 런북 `docs/infra-runbook.md` 5-3(프리픽스)·14-2(모델 받기) ·
> 미결 「AI Hub 71479 원본 20 GB 의 S3 경로」

---

## 0. 한 줄 요약

**제 맥에 있는 파일을 넘겨드리는 게 아니라, 성윤님이 본인 계정으로 직접 받으시는 링크를 드립니다.**
학원이 AWS 계정 관리자라 팀 안에서 자격증명을 만들 수 없다고 하셔서, 제가 올리는 경로를 접었습니다.
**결과적으로 이 방식이 AI Hub 이용정책에도 맞습니다**(§1).

- **음성 데이터셋 6종** — AI Hub 5종 + 서울 열린데이터광장 1종. 합 약 33 GB (§2)
- **모델 4종** — HuggingFace·Ollama 공개 배포라 **승인 절차 없이 바로** 받으십니다 (§3)
- 받으신 뒤 S3 올리는 것은 **EC2 안에서 자격증명 없이** 됩니다 (§5)

---

## 1. 왜 파일을 그대로 안 넘기는지 — AI Hub 이용정책

AI Hub 데이터 이용정책 **5번**: 제공받은 데이터를 *승인받지 않은 다른 법인·단체·개인에게
열람하게 하거나 제공·양도·대여·판매할 수 없다*는 취지의 조항이 있습니다.
(원문은 옮기지 않습니다 — 절대 원칙 6. 출처: https://www.aihub.or.kr/intrcn/guid/usagepolicy.do )

즉 **제 맥의 파일을 성윤님께 복사해 드리는 것 자체가 걸릴 수 있습니다.**
반대로 **성윤님이 본인 AI Hub 계정으로 신청·승인받아 직접 받으시면 아무 문제가 없습니다.**
그래서 링크와 절차만 드립니다.

> **이용정책 1번**도 있습니다 — 이용 시 **한국지능정보사회진흥원의 사업결과임을 밝혀야** 하고,
> 2차적 저작물에도 동일합니다. **발표 자료·보고서에 출처 표기가 필요합니다.**

---

## 2. 음성 데이터셋 — 급한 순

**전부 `Validation`만 받습니다. `Training`은 받지 않습니다** — D-코드당 19~28 GB씩이라
이 프로젝트 용도(STT 검증·측정)에 맞지 않습니다. 근거는 `data/README.md`에 적어 뒀습니다.

| 순 | 데이터셋 | 링크 | 로컬 폴더명 | 크기 | 어디에 쓰나 |
|---|---|---|---|---|---|
| 1 | AI Hub 「교육용 아시아어(중·일어 제외) 사용자의 한국어 음성」 | https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71479 | `aihub-foreign-proficiency-71479` | **21 GB** | **A-5 숙련도 등급별 WER/CER**. 이게 1순위입니다 |
| 2 | AI Hub 「민원(콜센터) 질의-응답」 | https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=98 | `aihub-minwon-qa` | 2.7 GB | 지식베이스·골든셋의 근거. C-5 과잉 마스킹 재측정(실제 발화 20,278건) |
| 3 | 서울 열린데이터광장 「(AI학습데이터) 한국어 공공분야 행정 민원상담 음성 데이터」 | https://data.seoul.go.kr/dataList/OA-22804/L/1/datasetView.do | `seoul-minwon-audio` | 1.3 GB | 다산콜DB wav 6,614건(12.7시간). D-5 통화 온도 |
| 4 | AI Hub 「저음질 전화망 음성」 | https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=571 | `aihub-lowquality-phone` | 3.3 GB | STT 오류 내성(4.2절). 전화망 8 kHz·잡음 포함 |
| 5 | AI Hub 「고객 응대 음성」 | https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71616 | `aihub-krespspeech` | 3.4 GB | 보조. 16 kHz |
| 6 | AI Hub 「상담 음성」 | https://aihub.or.kr/aidata/30711 | `aihub-ktelspeech` | 1.8 GB | 보조. 8 kHz |

> **3번(서울 열린데이터광장)만 AI Hub가 아닙니다** — 로그인·승인 없이 웹에서 바로 받습니다.
> 6번은 옛 URL 형식입니다. 안 열리면 AI Hub 검색창에 **「상담 음성」**으로 찾으시면 됩니다.

**1~3번만 받으셔도 지금 하는 측정은 다 돌아갑니다.** 4~6은 여유 있을 때로 미루셔도 됩니다.

### 폴더 구조

받으신 zip을 `data/raw/<위 폴더명>/validation/` 아래에 풀면 저장소 스크립트가 그대로 찾습니다.
정확한 하위 구조(`label/`·`wav/`·D-코드)는 **`data/README.md`에 데이터셋별로 적혀 있습니다** — 그걸 보고 푸시면 됩니다.

⚠ macOS 기본 압축 유틸리티로 풀면 `D60 2`처럼 **공백+숫자**가 붙는 경우가 있습니다. `D60`으로 바로잡아 주세요.

---

## 3. 모델 — 승인 절차 없음, 바로 받으시면 됩니다

`decisions/210`으로 **학습은 하지 않습니다.** 아래 4종이 운영·측정에 실제로 쓰는 전부입니다.

```bash
pip install -U huggingface_hub

# ① 임베딩 — B-2 하이브리드 검색 (2.1 GB)
huggingface-cli download nlpai-lab/KoE5 --local-dir models/koe5

# ② 리랭커 — B-3 (2.1 GB)
huggingface-cli download BAAI/bge-reranker-v2-m3 --local-dir models/bge-reranker-v2-m3

# ③ NER — C-5 P6 인명 (429 MB)
huggingface-cli download monologg/koelectra-base-v3-naver-ner --local-dir models/koelectra-ner

# ④ 생성 — B-4 서류 목록 카드 (1.4 GB, Apache-2.0)
huggingface-cli download gchrisoh/kanana-1.5-2.1b-instruct-2505-Q4_K_M-GGUF \
  kanana-1.5-2.1b-instruct-2505-q4_k_m.gguf --local-dir models/kanana-1.5-2.1b-instruct-gguf
```

④는 Ollama에 등록하는 단계가 더 있습니다 — **`decisions/207` 아래쪽에 Modelfile까지 그대로 적어 뒀습니다**
(`stop` 토큰을 빼먹으면 `<|eot_id|>`가 출력에 샙니다).

> ⚠ **런북 14-2는 EXAONE을 받습니다 — 그건 옛 구성입니다.**
> `decisions/207`로 **kanana**로 바꿨습니다(환각 96→27, 라이선스도 NC → Apache-2.0).
> 런북 14-2 갱신은 인프라 작업이라 제가 손대지 않았습니다.

### 안 받으셔도 되는 것

제 맥에는 남아 있지만 **지금 구성에서 안 씁니다** — 합쳐서 9.7 GB 아낍니다.

| 모델 | 크기 | 왜 안 쓰나 |
|---|---|---|
| `ko-sroberta-multitask` | 2.4 GB | KoE5로 교체됨 (`decisions/010`) |
| `polyglot-ko-1.3b` | 5.2 GB | 옛 생성 모델 (`decisions/009`) |
| `kcelectra-base` · `klue-roberta-base` · `domain-classifier` | 2.1 GB | 파인튜닝 전제인데 **학습을 안 합니다** (`decisions/210`) |

---

## 4. AI Hub에서 받는 법

### 4-1. 준비 (한 번만)

1. https://www.aihub.or.kr 회원가입 → **휴대폰 실명 인증**
2. 위 표의 데이터셋 페이지 → **데이터 신청** (이용 목적 기재) → **승인 대기**

⚠ **승인에 보통 1~2일 걸립니다.** 여섯 개를 받으실 거면 **오늘 한꺼번에 신청**해 두시는 게 좋습니다.

### 4-2. 받기 — 두 방법

**(A) 웹 다운로드** — 승인 후 데이터셋 페이지에서 zip을 직접 내려받습니다. 간단하지만 21 GB는 브라우저로 버겁습니다.

**(B) `aihubshell` CLI — EC2에 바로 받으실 거면 이쪽을 권합니다**

```bash
# 설치
curl -o aihubshell https://api.aihub.or.kr/api/aihubshell.do
chmod +x aihubshell

# 파일 목록 보기 (datasetkey = 위 표의 dataSetSn)
./aihubshell -mode l -datasetkey 71479 -aihubapikey '<마이페이지에서 발급>'

# 받기 (filekey 는 목록에서 고른 번호, 쉼표로 여러 개)
./aihubshell -mode d -datasetkey 71479 -filekey <번호> -aihubapikey '<키>'
```

- API 키는 AI Hub **마이페이지**에서 발급합니다.
- 다운로드가 끝나면 **분할 파일 병합 → 압축 해제 → zip 삭제**까지 자동으로 합니다.
- 안내 페이지: https://www.aihub.or.kr/devsport/apishell/list.do

> **(B)를 권하는 이유**: EC2에서 바로 받으면 «AI Hub → 노트북 → S3» 왕복이 사라집니다.
> 21 GB를 두 번 옮길 이유가 없습니다.

---

## 5. S3에 올리기 — 자격증명이 필요 없습니다

`decisions/110`에서 실측으로 확인된 것입니다: **운영 EC2에는 `callguard-ec2-role`이 붙어 있어
IMDSv2로 자격증명이 자동 주입됩니다.** 인스턴스 안에서는 키 없이 그냥 됩니다.

```bash
aws s3 ls s3://assist-apne2/            # 되는지 먼저 확인
aws s3 sync data/raw/aihub-foreign-proficiency-71479 \
  s3://assist-apne2/datasets/aihub-71479/ --dryrun
```

프리픽스는 **런북 5-3 구조 그대로** 씁니다:

```
s3://assist-apne2/
├── datasets/aihub-71479/ · aihub-seoul-minwon/ · ...
└── models/                 HF 가중치 미러 — 재다운로드 회피
```

`datasets/` 접두어에는 수명 주기 규칙 `datasets-to-ia`가 걸려 있어 30일 뒤 IA로 내려갑니다(약 45% 절감).
33 GB 기준 Standard 월 $0.8 수준이고 **인바운드 전송은 무료**라 예산에 영향이 거의 없습니다.

---

## 6. 주의 넷

1. **디스크 여유를 먼저 보세요.** 71479는 zip 20 GB, **풀면 29.7 GB**입니다.
   저는 압축을 풀지 않고 필요한 표본만 `unzip`으로 꺼내 썼습니다. 받자마자 S3로 올리고 로컬에서 지우는 순서를 권합니다.
2. **모델을 올릴 GPU EC2가 아직 없습니다** (`decisions/121` — 방침만 섰고 인스턴스는 미생성, `w6-gpu-model-instance` todo).
   그래서 §3 모델은 **S3 `models/` 프리픽스에 미러만 해 두시는 것**도 방법입니다 —
   나중에 GPU 인스턴스를 세울 때 허깅페이스에서 다시 받지 않고 같은 리전 S3에서 당겨오면 훨씬 빠릅니다.
3. **자체 통화 녹음은 올리지 않습니다** (절대 원칙 7 · `decisions/110` 10번). AI Hub 등 출처가 정리된 것만입니다.
4. **버킷 버전 관리가 꺼져 있습니다**(런북 5-1). `aws s3 rm`으로 지우면 **되살릴 수 없습니다.**

---

## 7. 제가 이어서 할 것

- 데이터가 S3에 올라오면 경로를 미결 항목(「AI Hub 71479 원본 20 GB 의 S3 경로」)에 적고 닫겠습니다.
- 71479 무결성 대조용 md5는 `data/raw/aihub-foreign-proficiency-71479/validation/CHECKSUMS.md5`에 있습니다.
  성윤님이 받으신 것과 제 것이 같은 파일인지 이걸로 맞춰 보면 됩니다.
