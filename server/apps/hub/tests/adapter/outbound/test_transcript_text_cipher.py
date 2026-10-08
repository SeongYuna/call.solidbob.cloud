# Requirement: C-5, SEC-1, SEC-2, QUA-1
"""전사 본문 암호화(`decisions/326`) — 마스킹본을 AES-256-GCM 으로 싸서 저장하고, 읽을 때 푼다."""

import base64

import pytest

from hub.adapter.outbound.transcript_text_cipher import TranscriptDecryptError, TranscriptTextCipher

KEY = base64.b64encode(bytes(range(32))).decode("ascii")
OTHER_KEY = base64.b64encode(bytes(range(1, 33))).decode("ascii")
MASKED = "제 번호는 *********** 입니다"


def test_키가_있으면_암호문으로_바꾸고_되돌린다():
    cipher = TranscriptTextCipher(KEY)
    sealed = cipher.seal(MASKED)
    assert sealed.startswith(TranscriptTextCipher.PREFIX)
    assert "번호" not in sealed  # 본문이 그대로 비치지 않는다
    assert cipher.unseal(sealed) == MASKED


def test_같은_글도_매번_다른_암호문이다():
    """nonce 를 매번 새로 뽑는다 — 같은 발화가 같은 암호문이면 DB 에서 어느 행끼리 같은 말인지 드러난다."""
    cipher = TranscriptTextCipher(KEY)
    assert cipher.seal(MASKED) != cipher.seal(MASKED)


def test_키가_없으면_그대로_저장한다():
    """키가 없을 때는 지금까지처럼 마스킹본 평문이다 — 어느 쪽이 켜졌는지는 `/health` 가 말한다."""
    cipher = TranscriptTextCipher(None)
    assert cipher.enabled is False
    assert cipher.seal(MASKED) == MASKED


def test_암호화_전에_쌓인_행은_그대로_읽는다():
    """옛 행(접두어 없음)과 새 행이 한 테이블에 섞인다 — 옛 행을 다시 쓰지 않아도 읽힌다."""
    assert TranscriptTextCipher(KEY).unseal(MASKED) == MASKED
    assert TranscriptTextCipher(None).unseal(MASKED) == MASKED


def test_키가_없는데_암호문을_만나면_실패한다():
    """암호문을 그대로 화면에 내보내지 않는다 — 키가 빠진 배포는 조용히 깨지지 않고 드러나야 한다."""
    sealed = TranscriptTextCipher(KEY).seal(MASKED)
    with pytest.raises(TranscriptDecryptError):
        TranscriptTextCipher(None).unseal(sealed)


def test_다른_키로는_풀리지_않는다():
    sealed = TranscriptTextCipher(KEY).seal(MASKED)
    with pytest.raises(TranscriptDecryptError):
        TranscriptTextCipher(OTHER_KEY).unseal(sealed)


def test_암호문이_바뀌면_풀리지_않는다():
    """GCM 인증 태그 — DB 에서 누가 암호문을 고치면 엉뚱한 글이 아니라 실패가 나온다."""
    sealed = TranscriptTextCipher(KEY).seal(MASKED)
    body = bytearray(base64.urlsafe_b64decode(sealed[len(TranscriptTextCipher.PREFIX):]))
    body[-1] ^= 0x01
    tampered = TranscriptTextCipher.PREFIX + base64.urlsafe_b64encode(bytes(body)).decode("ascii")
    with pytest.raises(TranscriptDecryptError):
        TranscriptTextCipher(KEY).unseal(tampered)


@pytest.mark.parametrize("bad", ["짧다", base64.b64encode(b"x" * 16).decode("ascii"), "not-base64!!"])
def test_키_형식이_틀리면_만들_때_실패한다(bad):
    """잘못된 키로 기동하면 조용히 평문 저장으로 떨어지지 않고 서버가 뜨지 않는다(합성 루트가 기동 때 만든다)."""
    with pytest.raises(ValueError) as exc:
        TranscriptTextCipher(bad)
    assert bad not in str(exc.value)  # 키 값을 메시지에 싣지 않는다(SEC-2)


def test_실패_메시지에_본문을_싣지_않는다():
    sealed = TranscriptTextCipher(KEY).seal(MASKED)
    with pytest.raises(TranscriptDecryptError) as exc:
        TranscriptTextCipher(OTHER_KEY).unseal(sealed)
    assert sealed not in str(exc.value)
    assert MASKED not in str(exc.value)
