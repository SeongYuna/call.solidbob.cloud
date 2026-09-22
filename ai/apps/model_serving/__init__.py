# Requirement: B-2, B-3, B-4, C-5
"""모델 HTTP 표면 — NER·임베딩·리랭커·생성을 원격에서 부르게 여는 **inbound 어댑터**(`decisions/213`).

`decisions/121` 로 모델이 서버와 다른 머신(전용 GPU EC2)에 간다. 포트(`RetrievalPort`·`MaskingPort` …)는 그대로 두고,
여기서는 모델 쪽 문만 연다. 합성 루트는 `ai/model_server.py` 다 — 이 패키지는 다른 ai 모듈을 import 하지 않는다
(`.importlinter` 계약 2).

⚠ **`server/` 는 이 패키지를 import 하지 않는다** — HTTP 로만 닿는다(`ai/tests/test_model_server.py` 가 검사한다).
"""
