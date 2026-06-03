"""Upload forecast CSV reports to S3-compatible storage, with inline fallback."""

from __future__ import annotations

import base64
import logging

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings

logger = logging.getLogger("shelfmind.s3_reports")


def upload_report_csv(key: str, body: bytes) -> dict:
    """Return {key, download_url, storage} where storage is 's3' or 'inline'."""
    settings = get_settings()
    if settings.s3_enabled:
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint or None,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                config=Config(signature_version="s3v4"),
            )
            s3.put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=body,
                ContentType="text/csv",
            )
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.s3_bucket, "Key": key},
                ExpiresIn=3600,
            )
            return {"key": key, "download_url": url, "storage": "s3"}
        except (BotoCoreError, ClientError, OSError) as exc:
            logger.warning("S3 upload failed (%s), using inline CSV download", exc)

    encoded = base64.b64encode(body).decode("ascii")
    return {
        "key": key,
        "download_url": f"data:text/csv;base64,{encoded}",
        "storage": "inline",
    }
