# Requirement: C-5
"""`monologg/koelectra-base-v3-naver-ner` 로 토큰 태그를 낸다. 모델 라이브러리를 부르므로 adapter.

모델 선택은 `_project/decisions/010`(NER `koelectra-ner` 유지)이다 — 여기서 다시 고르지 않는다.
받는 법: `scripts/download_models.py` → `models/koelectra-ner/`.

**CPU 로 돈다.** 2026-09-15 실측(Apple M 계열 CPU, 발화 1건 20~40자) 예열 뒤 **11~14ms**,
첫 호출만 약 1초다. 그래서 생성자에서 한 번 예열한다 — 첫 통화의 첫 발화가 1초 늦으면
자막이 그만큼 밀린다. GPU 를 쓰지 않는 이유: 운영 T4 는 Ollama 와 나눠 쓴다(런북 11장).

**라벨 표기**: 이 모델은 `PER-B`·`PER-I` 처럼 **유형 뒤에** BIO 를 붙이고, 서브워드마다
`-B` 를 주는 경우가 많다. 그래서 BIO 를 믿고 경계를 만들지 않고 유형만 떼어 넘긴다 —
경계는 `domain/services/spans.py` 의 규칙이 만든다.
"""

from __future__ import annotations

from pathlib import Path

from ...domain.value_objects.entity import TokenTag


def _entity_type(label: str) -> str:
    for sep in ("-", "_"):
        if sep in label:
            a, b = label.split(sep, 1)
            return b if a in {"B", "I"} else a
    return label


class KoElectraNerTagger:
    """`tag(text) -> list[TokenTag]`. 스레드 안전하지 않다 — 요청마다 부르면 `torch` 가 알아서 막는다."""

    def __init__(self, model_dir: str | Path, *, max_length: int = 256, warmup: bool = True) -> None:
        import torch
        from transformers import AutoModelForTokenClassification, AutoTokenizer

        model_dir = Path(model_dir)
        if not (model_dir / "config.json").exists():
            raise FileNotFoundError(f"NER 모델이 없다: {model_dir} (scripts/download_models.py)")
        self._torch = torch
        self._tok = AutoTokenizer.from_pretrained(str(model_dir))
        self._model = AutoModelForTokenClassification.from_pretrained(str(model_dir)).eval()
        self._id2label = self._model.config.id2label
        self._max_length = max_length
        self.model_name = model_dir.name
        if warmup:
            self.tag("예열 문장입니다")

    # 긴 발화는 글자 창으로 나눠 태깅한다. `truncation` 에만 맡기면 **뒷부분을 아예 안 본다** —
    # 거기 있는 이름은 조용히 누락된다. 창을 겹쳐 경계에 걸린 이름도 한쪽 창에서는 온전히 보이게 한다.
    _WINDOW_CHARS = 120
    _WINDOW_OVERLAP = 20

    def tag(self, text: str) -> list[TokenTag]:
        if not text.strip():
            return []
        if len(text) <= self._WINDOW_CHARS:
            return self._tag_window(text, 0)
        tags: list[TokenTag] = []
        step = self._WINDOW_CHARS - self._WINDOW_OVERLAP
        for base in range(0, len(text), step):
            tags.extend(self._tag_window(text[base : base + self._WINDOW_CHARS], base))
            if base + self._WINDOW_CHARS >= len(text):
                break
        return tags

    def _tag_window(self, text: str, base: int) -> list[TokenTag]:
        enc = self._tok(
            text,
            return_offsets_mapping=True,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
        )
        offsets = enc.pop("offset_mapping")[0].tolist()
        with self._torch.no_grad():
            probs = self._model(**enc).logits[0].softmax(-1)
        scores, ids = probs.max(-1)

        tags: list[TokenTag] = []
        for (start, end), i, s in zip(offsets, ids.tolist(), scores.tolist()):
            if start == end:  # [CLS]·[SEP]
                continue
            label = _entity_type(self._id2label[i])
            if label == "O":
                continue
            tags.append(TokenTag(start=base + start, end=base + end, label=label, score=s))
        return tags
