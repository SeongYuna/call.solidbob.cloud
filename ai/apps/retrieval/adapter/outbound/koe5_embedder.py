# Requirement: B-2
"""KoE5 임베딩 — 모델 라이브러리를 부르므로 adapter.

모델은 `_project/decisions/010` 이 확정했다(`nlpai-lab/KoE5`, 1024차원) — 다시 고르지 않는다.
받는 법: `scripts/download_models.py` → `models/koe5/`.

## 지키는 것 셋

1. **`query: ` / `passage: ` 접두어.** e5 계열은 비대칭 검색에서 둘을 갈라 쓰도록 학습됐다
   (모델 README 「Do I need to add the prefix」). 빠뜨려도 돌아가지만 점수가 조용히 낮아진다.
2. **mean pooling + L2 정규화.** `modules.json` 이 Transformer → Pooling(mean) → Normalize 다.
   `sentence-transformers` 를 들이지 않고(`ai/requirements.txt` 가 아직 들이지 않았다) 같은 계산을 직접 한다.
3. **잘림을 센다.** 상한은 **512 토큰**이다(`tokenizer_config.json` `model_max_length`).
   ⚠ `w4-dense-vector-index` 티켓의 「128토큰에서 truncation」은 `decisions/010` 이 **ko-sroberta-multitask**
   (옛 후보, `max_seq_length: 128`)에 대해 적은 것이다 — KoE5 의 상한이 아니다. 둘 다 세서 적는다.
   잘린 채로 임베딩하면 점수가 낮을 때 원인을 못 찾으므로, 잘린 수를 `truncated` 로 남긴다.

## 장치

`device=None` 이면 CPU 다. MPS(Apple)·CUDA 는 명시할 때만 쓴다 — **측정값이 어느 장치에서 나왔는지**
기록에 남아야 하는데(§5) 자동 선택이면 그 값이 실행마다 달라질 수 있다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

QUERY_PREFIX = "query: "
PASSAGE_PREFIX = "passage: "


class KoE5Embedder:
    dims = 1024

    def __init__(
        self,
        model_dir: str | Path,
        *,
        device: str | None = None,
        max_length: int = 512,
        batch_size: int = 16,
    ) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        model_dir = Path(model_dir)
        if not (model_dir / "config.json").exists():
            raise FileNotFoundError(f"임베딩 모델이 없다: {model_dir} (scripts/download_models.py)")
        self._torch = torch
        self.device = device or "cpu"
        self._tok = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModel.from_pretrained(str(model_dir)).eval().to(self.device)
        self._max_length = max_length
        self._batch_size = batch_size
        self.model_name = model_dir.name
        self.truncated = 0  # 누적 — 상한을 넘어 잘린 입력 수

    def token_lengths(self, texts: Sequence[str], *, prefix: str = PASSAGE_PREFIX) -> list[int]:
        """접두어·특수 토큰을 포함한 **자르기 전** 토큰 수. 잘림 집계용."""
        return [len(self._tok(prefix + t, truncation=False)["input_ids"]) for t in texts]

    def embed_queries(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed([QUERY_PREFIX + t for t in texts])

    def embed_passages(self, texts: Sequence[str]) -> list[list[float]]:
        return self._embed([PASSAGE_PREFIX + t for t in texts])

    def _embed(self, texts: list[str]) -> list[list[float]]:
        torch = self._torch
        out: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            raw_lengths = [len(self._tok(t, truncation=False)["input_ids"]) for t in batch]
            self.truncated += sum(1 for n in raw_lengths if n > self._max_length)
            enc = self._tok(
                batch, padding=True, truncation=True, max_length=self._max_length, return_tensors="pt"
            ).to(self.device)
            with torch.no_grad():
                hidden = self._model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            out.extend(pooled.cpu().tolist())
        return out
