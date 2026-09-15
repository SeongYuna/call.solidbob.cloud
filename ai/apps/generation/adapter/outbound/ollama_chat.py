# Requirement: B-4
"""Ollama `/api/chat` 호출 — 런북 14-3 규약 그대로: **`"think": false` 고정, `stream: false`.**

`think` 를 빠뜨리면 EXAONE 4.0 이 사고 과정 토큰부터 내서 서류 목록 자리에 추론 문장이 들어온다(런북 14-3 · 부록 B-5).
표준 라이브러리(`urllib`)만 쓴다 — HTTP 클라이언트 하나 때문에 의존성을 늘리지 않는다.

**`num_predict=80`** — 서류 목록은 8개 × 이름 한 개면 충분하다. 첫 판(160)은 설명문을 끝까지 써서 p50 1.4초였다.

**재현성**: `temperature 0` · `seed` 고정. 같은 입력이면 같은 출력이 나와야 환각 건수 비교가 성립한다.
"""

from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass

# B-4 기본 모델은 kanana 다(`decisions/207` — 010 의 EXAONE 을 환각 대조로 뒤집었다). Ollama 공식 라이브러리에 없어
# GGUF 를 받아 `ollama create` 로 이 이름을 만든다(결정 기록 「운영 반영」 절차).
DEFAULT_MODEL = "kanana-1.5-2.1b-instruct:q4_k_m"
EXAONE_MODEL = "hf.co/LGAI-EXAONE/EXAONE-4.0-1.2B-GGUF:latest"  # decisions/010 — 대조 재측정용으로 남긴다


@dataclass(frozen=True)
class ChatResult:
    content: str
    prompt_tokens: int
    output_tokens: int
    elapsed_ms: float  # 요청 → 응답 전체(벽시계)
    model: str


class OllamaChat:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        *,
        model: str = DEFAULT_MODEL,
        num_predict: int = 80,
        timeout_s: float = 10.0,
        seed: int = 20260915,
    ) -> None:
        self._url = base_url.rstrip("/") + "/api/chat"
        self.model = model
        self._num_predict = num_predict
        self._timeout = timeout_s
        self._seed = seed

    def chat(self, messages: list[dict[str, str]], *, schema: dict | None = None) -> ChatResult:
        payload = {
            "model": self.model,
            "messages": messages,
            "think": False,  # 런북 14-3 — 빠뜨리지 않는다
            "stream": False,
            "options": {"temperature": 0, "seed": self._seed, "num_predict": self._num_predict},
        }
        if schema is not None:
            payload["format"] = schema  # 출력 모양을 디코딩에서 강제한다(Ollama structured outputs)
        body = json.dumps(payload).encode()
        req = urllib.request.Request(self._url, data=body, headers={"content-type": "application/json"})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read())
        return ChatResult(
            content=data.get("message", {}).get("content", ""),
            prompt_tokens=int(data.get("prompt_eval_count") or 0),
            output_tokens=int(data.get("eval_count") or 0),
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            model=self.model,
        )
