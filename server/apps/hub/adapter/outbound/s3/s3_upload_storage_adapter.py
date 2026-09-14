# Requirement: A-6, SEC-2
"""S3 어댑터 — presigned POST/GET 발급과 목록. **boto3 를 아는 유일한 곳이다.**

**자격증명을 코드가 다루지 않는다.** boto3 기본 자격증명 체인이 EC2 인스턴스 역할
(`callguard-ec2-role`)을 IMDSv2 로 가져온다 — 2026-09-14 운영 파드에서 확인했다:
토큰 발급 성공 → `역할: callguard-ec2-role`. 그래서 `server-env` 에 AWS 키를 넣지 않는다
(`_project/decisions/108` ③ 을 되돌리지 않아도 된다). 로컬에서는 같은 체인이 `~/.aws` 나
환경변수를 본다 — 코드는 어느 쪽인지 모른다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import boto3
from botocore.config import Config

from hub.app.dtos.upload_dto import DownloadTicket, StoredUpload, UploadTicket
from hub.app.ports.output.upload_storage_port import UploadStoragePort


class S3UploadStorageAdapter(UploadStoragePort):
    def __init__(self, bucket: str, region: str | None = None) -> None:
        self._bucket = bucket
        # 서울 리전은 SigV4 만 받는다. 기본값에 기대지 않고 못박는다 —
        # 서명 버전이 틀리면 presigned URL 이 발급은 되고 업로드에서 403 이 난다(진단이 어렵다).
        self._client = boto3.client(
            "s3", region_name=region, config=Config(signature_version="s3v4")
        )

    async def issue_upload_ticket(
        self, key: str, content_type: str, max_bytes: int, expires_in: int
    ) -> UploadTicket:
        def _call() -> dict:
            return self._client.generate_presigned_post(
                Bucket=self._bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                # ⚠ 여기가 presigned POST 를 쓰는 이유다. `content-length-range` 는 **S3 가**
                #    실제 바이트로 강제한다 — 브라우저가 거짓 크기를 보내도 소용없다.
                #    presigned PUT 에는 이 조건이 없어 링크 하나로 무제한 업로드가 된다.
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, max_bytes],
                ],
                ExpiresIn=expires_in,
            )

        # boto3 는 동기다. 이벤트 루프를 막으면 같은 워커의 전사·마스킹 요청이 함께 멈춘다.
        result = await asyncio.to_thread(_call)
        return UploadTicket(
            url=result["url"], fields=dict(result["fields"]), key=key, expires_in=expires_in
        )

    async def list_objects(self, prefix: str, limit: int) -> list[StoredUpload]:
        def _call() -> dict:
            return self._client.list_objects_v2(
                Bucket=self._bucket, Prefix=prefix, MaxKeys=limit
            )

        result = await asyncio.to_thread(_call)
        return [
            StoredUpload(
                key=item["Key"],
                size=int(item["Size"]),
                last_modified=_as_utc(item["LastModified"]),
            )
            for item in result.get("Contents", ())
            # 프리픽스 자리표시자(0바이트 «폴더»)는 목록에 넣지 않는다.
            if not item["Key"].endswith("/")
        ]

    async def issue_download_ticket(self, key: str, expires_in: int) -> DownloadTicket:
        def _call() -> str:
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )

        url = await asyncio.to_thread(_call)
        return DownloadTicket(url=url, key=key, expires_in=expires_in)


def _as_utc(value: datetime) -> datetime:
    """boto3 는 tz 를 붙여 주지만 스텁·구버전이 naive 를 줄 수 있다. 정렬이 깨지지 않게 맞춘다."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
