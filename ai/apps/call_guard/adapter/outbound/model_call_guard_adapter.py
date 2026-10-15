# Requirement: C-6
"""`CallGuardPort` 구현 — 규칙 사전 위에 **학습한 폭언 분류기**를 얹는다(`decisions/223`).

- 규칙이 먼저 판정한다. 규칙 결과는 그대로 나간다(분류기가 지우지 못한다 — 위기 신호 `distress` 도 규칙 몫 그대로)
- 규칙이 폭언을 못 잡은 발화만 분류기가 본다. 폭언이면 `insult` 한 건을 **더한다**(재현율 우선 — 원칙 3 과 같은 방향)
- 분류기 입력은 가림 표시를 지운 마스킹본이다(`mask_tokens.strip_mask_tokens`) · `phrase` 는 받은 마스킹본 그대로(MANUAL-5.5)
- 분류기가 실패하면 규칙 결과만 나간다
- 판정 근거: 분류기는 문장 단위라 「걸린 낱말」 이 없다 — `span` 은 발화 전체다

모델: `models/call-guard-kcelectra-v2`(KcELECTRA-base 미세조정 · kocohub CC-BY-SA + 통화 정상 발화). 경로는 합성 루트가 넘긴다.
"""
from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

from hub.app.dtos.call_guard_dto import ABUSE_CATEGORIES, CallGuardFlag
from hub.app.ports.output.call_guard_port import CallGuardPort

from ...domain.services.mask_tokens import strip_mask_tokens

log = logging.getLogger(__name__)
CLASSIFIER_SOURCE_DOC = "DASAN-MANUAL-5.1"


class KcElectraAbuseClassifier:
    """`(text) -> bool`. CPU. 토크나이저를 스레드끼리 나눠 쓰지 않게 락을 건다(10-08 부하 시험의 임베딩 토크나이저 사고와 같은 이유)."""

    def __init__(self, model_dir: str | Path) -> None:
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        model_dir = Path(model_dir)
        if not (model_dir / "config.json").exists():
            raise FileNotFoundError(f"폭언 분류 모델이 없다: {model_dir}")
        self._torch = torch
        self._tok = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval()
        self._lock = threading.Lock()
        self.model_name = model_dir.name
        self(".")  # 예열

    def __call__(self, text: str) -> bool:
        with self._lock, self._torch.no_grad():
            enc = self._tok([text or "."], truncation=True, max_length=128, return_tensors="pt")
            return bool(self._model(**enc).logits.argmax(-1).item() == 1)


class ModelCallGuardAdapter(CallGuardPort):
    def __init__(self, rule: CallGuardPort, classify: Callable[[str], bool] | None) -> None:
        self._rule = rule
        self._classify = classify
        self.classifier_failures = 0

    async def detect(self, customer_utterance: str) -> list[CallGuardFlag]:
        flags = await self._rule.detect(customer_utterance)
        if self._classify is None or any(f.category in ABUSE_CATEGORIES for f in flags):
            return flags
        cleaned = strip_mask_tokens(customer_utterance)
        if not cleaned:
            return flags
        try:
            abusive = self._classify(cleaned)
        except Exception as e:  # noqa: BLE001 — 분류기가 죽어도 규칙 결과는 나간다
            self.classifier_failures += 1
            log.warning("폭언 분류기 실패 — 규칙 결과만: %s", type(e).__name__)
            return flags
        if abusive:
            flags = [*flags, CallGuardFlag(category="insult", phrase=customer_utterance, source_doc_id=CLASSIFIER_SOURCE_DOC,
                                           span=(0, len(customer_utterance)))]
        return flags
