# Requirement: A-6, SEC-1, QUA-1
"""업로드 규칙 — 키 생성·경로 조작 차단·형식/크기 거절. **여기가 판정의 전부다.**"""

import asyncio
from datetime import datetime, timezone

import pytest

from hub.app.dtos.upload_dto import DownloadTicket, StoredUpload, UploadTicket, UploadTicketCommand
from hub.app.ports.output.upload_storage_port import UploadStoragePort
from hub.app.use_cases.upload_interactor import (
    UPLOAD_PREFIX,
    UploadInteractor,
    UploadRejected,
    build_key,
    sanitize_filename,
)


class _SpyStorage(UploadStoragePort):
    def __init__(self) -> None:
        self.issued: list[tuple[str, str, int, int]] = []
        self.downloads: list[str] = []
        self.objects: list[StoredUpload] = []

    async def issue_upload_ticket(self, key, content_type, max_bytes, expires_in):
        self.issued.append((key, content_type, max_bytes, expires_in))
        return UploadTicket(url="https://s3.example/b", fields={"key": key}, key=key,
                            expires_in=expires_in)

    async def list_objects(self, prefix, limit):
        return list(self.objects)

    async def issue_download_ticket(self, key, expires_in):
        self.downloads.append(key)
        return DownloadTicket(url="https://s3.example/get", key=key, expires_in=expires_in)


def _cmd(**kw) -> UploadTicketCommand:
    return UploadTicketCommand(
        **{"filename": "call.wav", "content_type": "audio/wav", "content_length": 1024, **kw}
    )


# --- 경로 조작 — `decisions/110` 3번 -------------------------------------------------

@pytest.mark.parametrize(
    "raw",
    ["../../datasets/aihub/x.wav", "/etc/passwd", "..\\..\\models\\w.bin", "datasets/original.wav"],
)
def test_클라이언트가_준_경로는_이름_한_조각으로_눌린다(raw):
    key = build_key(raw)
    assert key.startswith(UPLOAD_PREFIX)
    assert ".." not in key
    # 프리픽스·날짜·파일명 셋뿐이다 — 중간에 다른 디렉터리가 끼지 않는다
    assert key.count("/") == 2


def test_한글과_공백은_안전한_글자로_바뀐다():
    name = sanitize_filename("다산 콜센터 (1).wav")
    assert all(c.isascii() for c in name)
    assert name.endswith(".wav") and "/" not in name and " " not in name


def test_이름이_통째로_지워지면_audio_로_대체한다():
    assert sanitize_filename("../..") == "audio"
    assert sanitize_filename("") == "audio"


def test_같은_이름을_두_번_올려도_키가_다르다():
    now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    assert build_key("a.wav", now) != build_key("a.wav", now)  # 버전 관리가 꺼져 있어 덮으면 끝이다


# --- 형식·크기 ----------------------------------------------------------------------

def test_음성이_아니면_거절한다():
    with pytest.raises(UploadRejected):
        asyncio.run(UploadInteractor(_SpyStorage(), 1000).issue(_cmd(content_type="text/csv")))


def test_상한을_넘으면_거절한다():
    with pytest.raises(UploadRejected):
        asyncio.run(UploadInteractor(_SpyStorage(), 1000).issue(_cmd(content_length=1001)))


def test_크기가_0이면_거절한다():
    with pytest.raises(UploadRejected):
        asyncio.run(UploadInteractor(_SpyStorage(), 1000).issue(_cmd(content_length=0)))


def test_파라미터가_붙은_MIME_도_받는다():
    storage = _SpyStorage()
    asyncio.run(UploadInteractor(storage, 10_000).issue(_cmd(content_type="audio/wav; codecs=1")))
    assert storage.issued[0][1] == "audio/wav"


def test_상한을_저장소에_그대로_넘긴다():
    """S3 정책(`content-length-range`)이 실제 바이트로 한 번 더 막는 근거다."""
    storage = _SpyStorage()
    asyncio.run(UploadInteractor(storage, 777).issue(_cmd(content_length=10)))
    assert storage.issued[0][2] == 777


# --- 다시 듣기 ----------------------------------------------------------------------

@pytest.mark.parametrize("key", ["datasets/aihub/x.wav", "uploads/../datasets/x.wav", "models/w.bin"])
def test_보관_프리픽스_밖은_내주지_않는다(key):
    with pytest.raises(UploadRejected):
        asyncio.run(UploadInteractor(_SpyStorage(), 1000).issue_download(key))


def test_목록은_새_것이_앞이다():
    storage = _SpyStorage()
    storage.objects = [
        StoredUpload("uploads/2026-09-01/a-x.wav", 1, datetime(2026, 9, 1, tzinfo=timezone.utc)),
        StoredUpload("uploads/2026-09-14/b-y.wav", 2, datetime(2026, 9, 14, tzinfo=timezone.utc)),
    ]
    items = asyncio.run(UploadInteractor(storage, 1000).list_recent(10))
    assert [i.size for i in items] == [2, 1]


# --- 확장자 (2026-09-14 스모크에서 잡힌 결함) ------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("원본.wav", "audio.wav"),        # 한글 이름이 확장자를 잡아먹던 자리
        ("../../datasets/원본.wav", "audio.wav"),
        ("x.WAV", "x.wav"),              # 대문자도 같은 파일이다
        ("evil.wav.exe", "evil.wav"),    # 음성 확장자가 아니면 뗀다
        ("noext", "noext"),
    ],
)
def test_확장자를_잃지_않는다(raw, expected):
    assert sanitize_filename(raw) == expected


def test_이름이_길어도_확장자가_잘리지_않는다():
    name = sanitize_filename("a" * 200 + ".mp3")
    assert name.endswith(".mp3") and len(name) <= 60
