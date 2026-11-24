"""Tujuan penyimpanan: folder lokal saat uji, Azure Blob saat deployment."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path

import pandas as pd

from .config import ACCOUNT, CONTAINER, DATA_DIR


class LocalSink:
    """Menyimpan ke folder lokal, dipakai untuk uji tanpa Azure."""

    def __init__(self, root: Path | str = DATA_DIR) -> None:
        self.root = Path(root)

    def write_parquet(self, path: str, df: pd.DataFrame) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(target, engine="pyarrow", compression="snappy", index=False)
        return str(target)

    def write_json(self, path: str, payload: dict) -> str:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(target)

    def list(self, prefix: str = "") -> list[str]:
        base = self.root / prefix
        if not base.exists():
            return []
        return sorted(
            str(path.relative_to(self.root)).replace("\\", "/")
            for path in base.rglob("*")
            if path.is_file()
        )


class BlobSink:
    """Menyimpan ke Azure Blob Storage.

    Dua cara autentikasi, dipilih otomatis:
    1. AZURE_STORAGE_CONNECTION_STRING (dipakai di GitHub Actions, nilainya
       disimpan sebagai repository secret).
    2. AzureCliCredential memakai sesi `az login` (dipakai saat uji lokal).
    """

    def __init__(self, account: str = ACCOUNT, container: str = CONTAINER) -> None:
        from azure.storage.blob import BlobServiceClient

        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
        if connection_string:
            self.service = BlobServiceClient.from_connection_string(connection_string)
        elif account:
            from azure.identity import AzureCliCredential

            self.service = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=AzureCliCredential(),
            )
        else:
            raise RuntimeError(
                "Isi AZURE_STORAGE_CONNECTION_STRING atau AZURE_STORAGE_ACCOUNT. "
                "Jalankan dengan --local untuk uji tanpa Azure."
            )

        self.container = container
        self.client = self.service.get_container_client(container)
        if not self.client.exists():
            self.client.create_container()

    def write_parquet(self, path: str, df: pd.DataFrame) -> str:
        buffer = io.BytesIO()
        df.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
        self.client.get_blob_client(path).upload_blob(buffer.getvalue(), overwrite=True)
        return f"{self.container}/{path}"

    def write_json(self, path: str, payload: dict) -> str:
        body = json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")
        self.client.get_blob_client(path).upload_blob(body, overwrite=True)
        return f"{self.container}/{path}"

    def list(self, prefix: str = "") -> list[str]:
        return sorted(blob.name for blob in self.client.list_blobs(name_starts_with=prefix))
