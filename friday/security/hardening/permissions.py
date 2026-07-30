from __future__ import annotations

import os
from pathlib import Path

from friday.security.hardening.exceptions import PermissionSecurityError


def ensure_readable_file(path: Path) -> None:
    if not path.is_file():
        raise PermissionSecurityError(
            "Readable file is required.",
            technical_message="Path must point to an existing file.",
            metadata={"name": path.name},
        )

    if not os.access(path, os.R_OK):
        raise PermissionSecurityError(
            "Readable file is required.",
            technical_message="Path does not have read access.",
            metadata={"name": path.name},
        )


def ensure_writable_directory(path: Path) -> None:
    if not path.is_dir():
        raise PermissionSecurityError(
            "Writable directory is required.",
            technical_message="Path must point to an existing directory.",
            metadata={"name": path.name},
        )

    if not os.access(path, os.W_OK):
        raise PermissionSecurityError(
            "Writable directory is required.",
            technical_message="Path does not have write access.",
            metadata={"name": path.name},
        )
