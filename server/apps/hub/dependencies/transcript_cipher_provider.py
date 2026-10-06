# Requirement: C-5, SEC-1, SEC-2
"""전사 본문 암호화기 — 설정의 `TRANSCRIPT_ENC_KEY` 로 만든다(`decisions/326`).

쓰는 쪽(`transcript_record_provider`)과 읽는 쪽(`transcript_query_provider`·`blacklist_provider`)이
**같은 함수로** 받는다 — 한쪽만 키를 보면 쓴 것을 못 읽거나 평문으로 쓴다.
"""

from __future__ import annotations

from hub.adapter.outbound.transcript_text_cipher import TranscriptTextCipher


def transcript_cipher_of(settings) -> TranscriptTextCipher:
    return TranscriptTextCipher(settings.transcript_enc_key)
