import boto3
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class ObjectStorageService:
    """MinIO / S3-compatible object storage."""

    def __init__(self):
        self.client = None
        if getattr(settings, "S3_ENDPOINT_URL", "") and getattr(settings, "S3_ACCESS_KEY", ""):
            try:
                self.client = boto3.client(
                    "s3",
                    endpoint_url=settings.S3_ENDPOINT_URL,
                    aws_access_key_id=settings.S3_ACCESS_KEY,
                    aws_secret_access_key=settings.S3_SECRET_KEY,
                )
            except Exception as e:
                logger.error("Failed to initialize S3 client: %s", e)

    def is_available(self) -> bool:
        return self.client is not None

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        return key

    def get_bytes(self, bucket: str, key: str) -> bytes:
        response = self.client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read()

    def presigned_get_url(self, bucket: str, key: str, expires: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires
        )

    def ensure_bucket(self, bucket: str):
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            self.client.create_bucket(Bucket=bucket)
            logger.info("Created bucket: %s", bucket)


def get_storage_service() -> ObjectStorageService:
    return ObjectStorageService()
