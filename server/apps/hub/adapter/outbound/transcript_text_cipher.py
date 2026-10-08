# Requirement: C-5, SEC-1, SEC-2
"""전사 본문(`transcript_segment.text`) 암호화 — 마스킹본을 AES-256-GCM 으로 싸서 저장한다(`decisions/326`).

**마스킹이 먼저다.** 여기 들어오는 글은 이미 MaskingPort 를 거친 마스킹본이다. 암호화는 그 위의 한 겹이다 —
DB 접속 권한이나 덤프가 새도 ① 마스킹이 놓친 값(오류 전사에서 실측으로 샌다) ② 패턴 밖 상담 내용이 읽히지 않게 한다.
RDS 디스크 암호화(런북)는 DB 에 접속한 사람에게는 평문을 보여 주므로 이것과 지키는 자리가 다르다.

- 저장 형식: `enc:v1:` + urlsafe-base64(nonce 12바이트 + 암호문 + 태그). `text` 컬럼(TEXT) 그대로 담긴다 — 스키마 변경 없음
- **키가 없으면 그대로 둔다** — 지금까지처럼 마스킹본 평문이다. 켜졌는지는 `/health` 의 `transcript_encryption` 이 말한다
- **접두어가 없는 행은 그대로 읽는다** — 암호화 전에 쌓인 행이다. 옛 행을 다시 쓰지 않는다
- 키 형식이 틀리면 만들 때 `ValueError` — 합성 루트가 기동 때 한 번 만들어 보므로 서버가 뜨지 않는다
- **키를 잃으면 암호화된 행은 되돌릴 수 없다.** 키는 운영 시크릿 `server-env` 의 `TRANSCRIPT_ENC_KEY` 하나다
- 예외 메시지에 키·본문·암호문을 싣지 않는다(SEC-1·SEC-2)
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_KEY_BYTES = 32  # AES-256
_NONCE_BYTES = 12  # GCM 권장 길이


class TranscriptDecryptError(Exception):
    """암호문을 풀 수 없다 — 키가 없거나 다르거나 암호문이 바뀌었다."""


class TranscriptTextCipher:
    PREFIX = "enc:v1:"

    def __init__(self, key: str | None) -> None:
        self._aead = AESGCM(_decode_key(key)) if key else None

    @property
    def enabled(self) -> bool:
        return self._aead is not None

    def seal(self, text: str) -> str:
        if self._aead is None:
            return text
        nonce = os.urandom(_NONCE_BYTES)
        body = self._aead.encrypt(nonce, text.encode("utf-8"), None)
        return self.PREFIX + base64.urlsafe_b64encode(nonce + body).decode("ascii")

    def unseal(self, stored: str) -> str:
        if not stored.startswith(self.PREFIX):
            return stored  # 암호화 전에 쌓인 행
        if self._aead is None:
            raise TranscriptDecryptError("암호화된 전사인데 TRANSCRIPT_ENC_KEY 가 설정되지 않았다")
        try:
            raw = base64.urlsafe_b64decode(stored[len(self.PREFIX):])
            plain = self._aead.decrypt(raw[:_NONCE_BYTES], raw[_NONCE_BYTES:], None)
        except (InvalidTag, binascii.Error, ValueError) as exc:
            raise TranscriptDecryptError("전사를 복호화하지 못했다 — 키가 다르거나 저장된 값이 바뀌었다") from exc
        return plain.decode("utf-8")


def _decode_key(key: str) -> bytes:
    try:
        raw = base64.b64decode(key, validate=True)
    except (binascii.Error, ValueError):
        raw = b""
    if len(raw) != _KEY_BYTES:
        # 값은 싣지 않는다 — 형식만 알려 준다(SEC-2)
        raise ValueError("TRANSCRIPT_ENC_KEY 는 base64 로 적은 32바이트여야 한다 (openssl rand -base64 32)")
    return raw
