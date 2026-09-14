# Requirement: A-6, SEC-1, SEC-2
"""업로드 인터랙터 — **무엇을 허용할지 정하고 키를 만든다.** 판정은 전부 여기 규칙이다.

`_project/decisions/110` 3번: **클라이언트가 준 경로를 그대로 쓰지 않는다.** 파일명에 `../` 나
`datasets/` 를 넣어 다른 프리픽스를 덮어쓰는 것을 막는다 — 같은 버킷에 AI Hub 원본이 산다.
"""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timezone

from hub.app.dtos.upload_dto import (
    DownloadTicket,
    StoredUpload,
    UploadTicket,
    UploadTicketCommand,
)
from hub.app.ports.input.upload_use_case import UploadUseCase
from hub.app.ports.output.upload_storage_port import UploadStoragePort

# 보관 프리픽스. `datasets/`(AI Hub 원본)·`models/`·`goldenset/` 과 섞이지 않게 서버가 고정한다.
# 수명 주기 규칙 `datasets-to-ia` 는 `datasets/` 접두어 한정이라 여기엔 걸리지 않는다(런북 5-4).
UPLOAD_PREFIX = "uploads/"

# 티켓 수명. 짧을수록 좋다 — 유출돼도 금방 죽는다.
TICKET_EXPIRES_IN = 300
DOWNLOAD_EXPIRES_IN = 300

# 음성만 받는다. 절대 원칙 7 은 「자체 통화 녹음 금지」이지 형식 제한이 아니지만,
# 형식을 좁혀 두면 실수로 스프레드시트·문서가 올라가는 것을 막는다.
ALLOWED_CONTENT_TYPES = frozenset({
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/mpeg", "audio/mp3",
    "audio/mp4", "audio/m4a", "audio/x-m4a",
    "audio/flac", "audio/x-flac",
    "audio/ogg", "audio/webm",
})

# 파일명에서 살릴 글자. 한글·공백·따옴표는 S3 키와 Content-Disposition 양쪽에서 말썽이라 바꾼다.
_SAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_NAME = 60

# 살려 주는 확장자. 이 목록 밖은 떼어 버린다 — `evil.wav.exe` 가 버킷에 `.exe` 로 남으면
# 나중에 목록을 보는 사람이 놀란다. 내용을 정하는 것은 어차피 Content-Type 이다.
_AUDIO_EXTS = frozenset({"wav", "mp3", "m4a", "mp4", "flac", "ogg", "webm", "aac", "opus"})


class UploadRejected(ValueError):
    """규칙에 어긋난 요청. 라우터가 400 으로 옮긴다. **본문에 값을 싣지 않는다.**"""


def sanitize_filename(raw: str) -> str:
    """경로를 떼고 안전한 글자만 남긴다. 빈 이름이면 `audio` 로 대체한다.

    `..`·`/`·`\\` 는 경로 조작의 입구다. 여기서 **이름 한 조각으로 눌러버린다** —
    아래 `build_key` 가 그 결과를 프리픽스 뒤에 붙이므로 프리픽스 밖으로 나갈 수 없다.

    **확장자는 따로 뗐다 붙인다.** 한 덩어리로 치면 한글 이름이 확장자를 잡아먹는다 —
    `원본.wav` → `_.wav` → (앞뒤 `._-` 제거) → `wav` 로 **`.wav` 가 이름이 돼 버렸다**
    (2026-09-14 스모크에서 실제로 나왔다). 확장자는 콘솔에서 눈으로 고르는 단서라 살린다.
    """
    name = raw.replace("\\", "/").rsplit("/", 1)[-1]
    stem, dot, suffix = name.rpartition(".")
    if not dot:                      # 확장자가 없다
        stem, suffix = name, ""
    # 확장자는 짧은 영숫자일 때만 인정한다 — `tar.gz` 같은 것도, 한글 확장자도 여기서 걸린다
    ext = f".{suffix.lower()}" if suffix.lower() in _AUDIO_EXTS else ""
    stem = _SAFE_CHARS.sub("_", stem).strip("._-")
    if not stem:
        stem = "audio"
    return stem[: _MAX_NAME - len(ext)] + ext


def build_key(filename: str, now: datetime | None = None) -> str:
    """`uploads/<YYYY-MM-DD>/<무작위 8>-<정규화한 이름>`.

    날짜로 나누는 이유는 콘솔에서 눈으로 찾기 위해서다. 무작위를 앞에 두는 이유는 같은 이름을
    두 사람이 같은 날 올려도 덮어쓰지 않게 하기 위해서다 — **버킷 버전 관리가 꺼져 있어
    덮어쓰면 복구할 수 없다**(런북 5-1).
    """
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    return f"{UPLOAD_PREFIX}{stamp}/{secrets.token_hex(4)}-{sanitize_filename(filename)}"


class UploadInteractor(UploadUseCase):
    def __init__(self, storage: UploadStoragePort, max_bytes: int) -> None:
        self._storage = storage
        self._max_bytes = max_bytes

    async def issue(self, command: UploadTicketCommand) -> UploadTicket:
        content_type = (command.content_type or "").split(";", 1)[0].strip().lower()
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise UploadRejected("음성 파일만 올릴 수 있다")
        if command.content_length <= 0:
            raise UploadRejected("파일 크기를 알 수 없다")
        if command.content_length > self._max_bytes:
            raise UploadRejected(f"파일이 너무 크다 — 상한은 {self._max_bytes} 바이트다")

        # 상한은 여기서 한 번, S3 정책(`content-length-range`)에서 한 번 더 건다.
        # 브라우저가 거짓 크기를 보내도 S3 가 실제 바이트로 거절한다 — 그게 두 겹으로 거는 이유다.
        return await self._storage.issue_upload_ticket(
            key=build_key(command.filename),
            content_type=content_type,
            max_bytes=self._max_bytes,
            expires_in=TICKET_EXPIRES_IN,
        )

    async def list_recent(self, limit: int) -> list[StoredUpload]:
        items = await self._storage.list_objects(prefix=UPLOAD_PREFIX, limit=limit)
        return sorted(items, key=lambda item: item.last_modified, reverse=True)

    async def issue_download(self, key: str) -> DownloadTicket:
        # 보관 프리픽스 밖은 내주지 않는다 — 같은 버킷에 AI Hub 원본과 평가 결과가 산다.
        if not key.startswith(UPLOAD_PREFIX) or ".." in key:
            raise UploadRejected("보관된 파일이 아니다")
        return await self._storage.issue_download_ticket(key=key, expires_in=DOWNLOAD_EXPIRES_IN)
