import io
from typing import BinaryIO

from minio import Minio
from minio.commonconfig import Tags

from shared.config import get_settings


class MinioClient:
    """Обёртка над MinIO SDK с типовыми операциями для проекта."""

    def __init__(self) -> None:
        settings = get_settings()
        self.bucket = settings.minio_bucket
        self.client = Minio(
            self._resolve_endpoint(
                settings.minio_endpoint, settings.minio_endpoint_local
            ),
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_secure,
        )

    @staticmethod
    def _resolve_endpoint(in_docker: str, on_host: str) -> str:
        """Выбирает endpoint MinIO в зависимости от окружения."""
        from pathlib import Path

        if Path("/.dockerenv").exists():
            return in_docker
        return on_host

    @staticmethod
    def _to_tags(tags: dict[str, str]) -> Tags:
        """Конвертирует обычный dict в minio Tags."""
        result = Tags.new_object_tags()
        for k, v in tags.items():
            result[k] = v
        return result

    def ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_bytes(
        self,
        key: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
        tags: dict[str, str] | None = None,
    ) -> str:
        """Загружает объект в бакет с тегами (теги ставятся сразу при загрузке)."""
        if isinstance(data, bytes):
            data = io.BytesIO(data)

        length = self._get_length(data)

        self.client.put_object(
            self.bucket,
            key,
            data,
            length=length,
            content_type=content_type,
            tags=self._to_tags(tags) if tags else None,
        )

        return key

    def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        try:
            self.client.remove_object(self.bucket, key)
        except Exception:
            pass

    def delete_many(self, keys: list[str]) -> None:
        if not keys:
            return
        from minio.deleteobjects import DeleteObject

        errors = self.client.remove_objects(
            self.bucket, [DeleteObject(k) for k in keys]
        )
        for _ in errors:
            pass

    def set_tags(self, key: str, tags: dict[str, str]) -> None:
        """Устанавливает теги (полностью заменяет существующие)."""
        self.client.set_object_tags(self.bucket, key, self._to_tags(tags))

    def get_tags(self, key: str) -> dict[str, str]:
        try:
            tags = self.client.get_object_tags(self.bucket, key)
            return dict(tags) if tags else {}
        except Exception:
            return {}

    def make_public_url(self, key: str) -> str:
        settings = get_settings()
        return f"{settings.minio_public_url}/{self.bucket}/{key}"

    @staticmethod
    def _get_length(data: BinaryIO) -> int:
        if hasattr(data, "getbuffer"):
            return len(data.getbuffer())
        current = data.tell()
        data.seek(0, 2)
        length = data.tell()
        data.seek(current)
        return length


# Синглтон
_client: MinioClient | None = None


def get_minio() -> MinioClient:
    global _client
    if _client is None:
        _client = MinioClient()
    return _client