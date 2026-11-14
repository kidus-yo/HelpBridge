"""Replaceable private document storage.

Default implementation writes under MEDIA_ROOT/private/knowledge and is never
exposed as a public URL.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from django.conf import settings


class DocumentStorage(Protocol):
    def save(self, institution_id: str, document_id: str, filename: str, content: bytes) -> str: ...
    def read(self, storage_ref: str) -> bytes: ...
    def delete(self, storage_ref: str) -> None: ...


class LocalPrivateStorage:
    def __init__(self, root: Path | None = None):
        self.root = Path(root or Path(settings.MEDIA_ROOT) / "private" / "knowledge")

    def save(self, institution_id: str, document_id: str, filename: str, content: bytes) -> str:
        safe_name = os.path.basename(filename).replace("..", "_")
        directory = self.root / str(institution_id) / str(document_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / safe_name
        path.write_bytes(content)
        return str(path)

    def read(self, storage_ref: str) -> bytes:
        path = Path(storage_ref)
        root = self.root.resolve()
        resolved = path.resolve()
        if root not in resolved.parents and resolved != root:
            raise PermissionError("Storage reference is outside the private knowledge root.")
        return resolved.read_bytes()

    def delete(self, storage_ref: str) -> None:
        path = Path(storage_ref)
        if path.exists():
            path.unlink()


def get_document_storage() -> DocumentStorage:
    backend = getattr(settings, "DOCUMENT_STORAGE_BACKEND", "local")
    if backend == "local":
        return LocalPrivateStorage()
    raise RuntimeError(f"Unknown document storage backend: {backend}")
