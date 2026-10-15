"""모델 가중치를 data/README.md와 같은 방식으로 models/ 아래에 받아둔다.
크기가 커서 커밋 대상이 아니다 (.gitignore 참고). 필요할 때 다시 실행하면 된다.

생성 모델(B-4)은 여기 없다 — exaone-4.0-1.2b(Ollama 서빙)로 받는다:
    ollama pull hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF
(HuggingFace snapshot_download 대상 아님). 반드시 `think: false` 옵션과 `/api/chat`
엔드포인트로 호출할 것 — 기본(thinking 켜짐) 상태로는 250토큰 예산을 추론에 다 쓰고
실제 답을 못 낸다(Qwen3와 같은 실패 모드, 실측 확인됨). `/api/generate`에서는
`think:false`가 반영되지 않았다.

생성 대조군(6주차, 환각 건수 비교용) `kanana-1.5-2.1b-instruct`도 여기 없다 —
Ollama 공식 라이브러리·`hf.co/kakaocorp/...-GGUF` 둘 다 2026-08-26 기준 못 찾았다.
6주차 착수 시 다시 확인.

`_project/decisions/010-AI-모델-구성-확정.md` 참고. 이전 구성(ko-sroberta-multitask
단독 임베딩, polyglot-ko-1.3b 생성, exaone3.5:2.4b 생성)은 `_project/decisions/009`에
남아 있다 — 전부 이 파일 갱신 이전 상태이므로 로컬에 남아 있어도 지워도 된다.
"""

import os
from huggingface_hub import snapshot_download

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

TARGETS = [
    # (허깅페이스 repo id, 로컬 폴더명, 용도)
    ("nlpai-lab/KoE5", "koe5", "임베딩 — B-2 하이브리드 검색 dense_vector (2026-08-26, ko-sroberta-multitask 대체: 512토큰 지원, 1024차원)"),
    ("beomi/KcELECTRA-base", "kcelectra-base", "컴플라이언스 분류기 베이스 — C-1~C-4·B-0 파인튜닝 대상. 댓글 코퍼스라 STT 오탈자에 강함"),
    ("klue/roberta-base", "klue-roberta-base", "분류기 대조군 — 5주차 오류 내성 실험에서 KcELECTRA와 비교"),
    ("monologg/koelectra-base-v3-naver-ner", "koelectra-ner", "옛 NER — 학습 데이터 동의서가 상업 이용 금지(decisions/222). 비교·되돌리기용으로만 남긴다"),
    ("vmaca123/korean-pii-ner-v3", "korean-pii-ner-v3", "NER — C-5 P6(이름)·P7(주소). KLUE 기반 CC-BY-SA-4.0 (decisions/222)"),
]

for repo_id, local_name, purpose in TARGETS:
    dest = os.path.join(MODELS_DIR, local_name)
    print(f"\n=== {repo_id} -> models/{local_name} ({purpose}) ===")
    snapshot_download(repo_id=repo_id, local_dir=dest)
    print(f"완료: {dest}")

print("\n전체 다운로드 완료")
