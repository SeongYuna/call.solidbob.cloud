# data/

이 폴더는 원본 데이터 저장용이며, **`raw/`, `processed/` 하위는 전부 `.gitignore` 처리되어
커밋되지 않는다.** AI Hub 데이터는 재배포 금지 조항이 있어 저장소에 올리면 안 되고,
용량도 커서 어차피 git에 적합하지 않다. 이 README만 커밋 대상이다.

## 구조

```
data/
└── raw/
    ├── aihub-ktelspeech/        AI Hub 「상담 음성」 데이터셋 (aihub.or.kr/aidata/30711)
    │   └── validation/
    │       ├── label/           [라벨] 압축을 D-코드별로 풀어서 둔다 (session/발화 단위 .txt)
    │       │   ├── D60/J91/S00.../*.txt   (7,920 files)
    │       │   ├── D61/J92/S00.../*.txt   (7,282 files)
    │       │   └── D62/J93/S00.../*.txt   (6,036 files)
    │       └── wav/             [원천] 압축을 D-코드별로 풀어서 둔다 (session/발화 단위 .wav)
    │           ├── D60/J91/S00.../*.wav   (7,731 files, 704M)
    │           ├── D61/J92/S00.../*.wav   (7,051 files, 752M)
    │           └── D62/J93/S00.../*.wav   (5,800 files, 689M)
    ├── aihub-krespspeech/       AI Hub 「고객 응대 음성」 데이터셋 (aihub.or.kr/aihubdata/data/view.do?dataSetSn=71616)
    │   └── validation/
    │       ├── label/           [라벨] D50/J01~04, D51/J05~09, D52/J10~14 (session/발화 단위 .txt)
    │       │   ├── D50/         (17,038 files, 67M)
    │       │   ├── D51/         (13,699 files, 54M)
    │       │   └── D52/         (11,467 files, 45M)
    │       └── wav/             [원천] 16bit mono **16,000Hz** — ktelspeech(8,000Hz)와 샘플레이트 다름, 주의
    │           ├── D50/         (8,522 files, 1.1G)
    │           ├── D51/         (6,851 files, 1.3G)
    │           └── D52/         (5,732 files, 1.2G)
    ├── aihub-lowquality-phone/  AI Hub 「저음질 전화망 음성」 데이터셋 (dataSetSn=571) — 실제 상담
    │   └── validation/          환경 잡음 포함, 8,000Hz(전화망 표준)
    │       ├── label/           [VL_D01~04] D-코드별 세션(J01~J19) 구조, .txt+.json (39,916+1,926 files, 171M)
    │       └── wav/             [VS_D01~04] 16bit mono 8,000Hz, .wav 39,916 files (라벨과 1:1 매칭), 3.9G
    └── aihub-minwon-qa/         AI Hub 「민원(콜센터) 질의-응답」 데이터셋 (aihub.or.kr/aidata/30716)
        └── validation/
            ├── label/           도메인별 질의-응답 텍스트 라벨 (수십~수백 KB, 부담 없음)
            │   ├── 금융보험/
            │   ├── 다산콜센터/
            │   ├── 질병관리본부/
            │   └── 쇼핑/
            └── source/          도메인별 원천데이터 (오디오·텍스트 혼재로 추정, 총 약 2.4G)
                ├── 금융보험/    (~440M)
                ├── 다산콜센터/  (~200M)
                ├── 질병관리본부/ (~320M)
                └── 쇼핑/        (~1.4G)
```

> **`aihub-minwon-qa`는 이제 핵심 데이터다 (2026-08-26 갱신).** 이전에는 선택 사항으로
> 적혀 있었으나, 데모 도메인을 이 데이터셋이 다루는 4개 도메인(금융보험·다산콜센터·
> 질병관리본부·쇼핑)으로 한정하기로 확정하면서 지식베이스(`knowledge-base/`)와 골든셋의
> 카테고리·의도 체계가 이 데이터셋에서 나온다. 근거: `_project/decisions/004-데모-도메인-4종-확정.md`,
> [5.1-1절](/docs/05/).

세 데이터셋 모두 **`Training`은 받지 않는다** — 상담 음성은 D-코드당 최대 19GB, 고객
응대 음성은 D-코드당 최대 28GB, 민원 질의응답은 쇼핑 카테고리 하나만도 최대 2GB까지
있어 이 프로젝트 용도(STT 파이프라인 검증·데모)에 전혀 맞지 않는다. `Validation`만으로
충분하다 (데이터셋당 1~3GB 안팎).

ktelspeech·krespspeech는 label과 wav가 같은 D-코드·세션(`S00...`) 구조를 그대로
미러링한다 — 세션 ID로 짝을 맞춰 전사(.txt)와 음성(.wav)을 매칭한다. minwon-qa는
D-코드 대신 도메인명(금융보험 등)으로 label/source가 짝지어진다.

## 받은 파일 넣는 법

1. AI Hub에서 받은 6개 zip(`[라벨]KtelSpeech_valid_D6X_label_0.zip`,
   `[원천]KtelSpeech_valid_D6X_wav_0.zip`, X=0,1,2)을 위 대응 폴더(`label/D6X`, `wav/D6X`)에
   압축 해제한다. macOS 기본 압축 유틸리티로 풀면 이름이 `D60 2`처럼 공백+숫자가 붙는
   경우가 있는데, 경로에 공백이 있으면 스크립트에서 매번 따옴표 처리를 해야 하니
   `D60`으로 바로 잡아준다.
2. 압축 해제 후 원본 zip은 지워도 된다 (공간 절약, 필요하면 AI Hub에서 다시 받을 수 있음).
3. 추가로 다른 데이터셋(예: 서울 열린데이터광장 행정 민원상담 음성)을 받으면
   `data/raw/<데이터셋-slug>/` 형태로 형제 폴더를 만든다.

## 쓰임새

- [5.2절](/docs/05/): STT 파이프라인 동작 검증, 데모용 실제 음성 — 여기서 받은 Validation
  세트(D60~D62, 약 1.1GB)로 충분하다.
- [4.2절](/docs/04/) STT 오류 내성 실험은 이 데이터를 쓰지 않는다 — 텍스트 레벨 합성 오류 주입.
- `server/`·`ai/`(2026-08-26 [Task 1] 스캐폴딩 후 서브도메인 분리), `services/call-mediator` 스캐폴딩 이후
  이 경로를 코드에서 참조한다 — `server/`·`ai/`는 뼈대만 있고 아직 이 데이터를 실제로
  읽는 코드는 없다.

### 서울 열린데이터광장 — 행정 민원상담 음성

```
data/raw/seoul-minwon-audio/
└── 민원상담_음성/
    └── 다산콜DB/
        └── <시나리오번호>_<연령대>_<성별>_<지역>_<민원인|상담사>_<take번호>.wav   (6,614 files, 1.3G)
```

**받는 법** (data.seoul.go.kr/etc/aiEduData.do?menu=n17 — 회원가입·승인 불필요):

1. 파일1(`민원상담_음성.z01`)·파일2(`민원상담_음성.z02`)·파일3(`민원상담_음성.zip`) **셋 다** 받는다.
2. macOS 기본 `unzip`은 이 분할 zip(`.z01`/`.z02`/`.zip`)을 못 읽는다. 터미널에서 합친다:
   ```bash
   cd ~/Downloads
   zip -FF 민원상담_음성.zip --out fixed.zip
   ```
3. 안의 파일명이 EUC-KR/CP949로 되어 있어 macOS `unzip`으로 풀면 한글이 깨진다.
   Python `zipfile`은 정상적으로 읽으므로 이걸로 푼다:
   ```bash
   python3 -c "import zipfile; zipfile.ZipFile('fixed.zip').extractall('data/raw/seoul-minwon-audio')"
   ```
4. `~/Downloads`의 원본 3개 분할 파일과 `fixed.zip`은 지워도 된다.

## 전처리 결과 (`data/processed/`)

청킹·정규화 등 전처리 산출물을 두는 자리다. 아직 생성되지 않았으며, 생성되어도
`raw/`와 동일하게 커밋 대상이 아니다.
