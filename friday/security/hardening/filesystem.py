from __future__ import annotations

import logging as standard_logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from friday.security.hardening.exceptions import FilesystemSecurityError
from friday.security.hardening.models import (
    AuditCallback,
    HardenedPath,
    HardenedPathPurpose,
)
from friday.security.hardening.permissions import (
    ensure_readable_file,
    ensure_writable_directory,
)
from friday.security.hardening.policies import SecurityPolicy
from friday.shared.errors import FridayError


@dataclass(frozen=True, slots=True)
class SecureFilesystem:
    policy: SecurityPolicy
    logger: standard_logging.Logger
    audit_callback: AuditCallback | None = None

    def ensure_directory(
        self,
        root: Path,
        path: Path,
        *,
        purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
    ) -> HardenedPath:
        hardened = self._authorize(root, path, purpose=purpose)
        try:
            hardened.path.mkdir(parents=True, exist_ok=True)
            ensure_writable_directory(hardened.path)
        except FridayError:
            raise
        except OSError as error:
            raise FilesystemSecurityError(
                "Directory could not be created safely.",
                technical_message="Secure directory creation failed.",
                cause=error,
                metadata=hardened.to_dict(),
            ) from error
        self._record("directory_created", "info", hardened)
        return hardened

    def read_text(
        self,
        root: Path,
        path: Path,
        *,
        purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
    ) -> str:
        hardened = self._authorize(root, path, purpose=purpose, must_exist=True)
        ensure_readable_file(hardened.path)
        try:
            return hardened.path.read_text(encoding="utf-8")
        except OSError as error:
            raise FilesystemSecurityError(
                "File could not be read safely.",
                technical_message="Secure file read failed.",
                cause=error,
                metadata=hardened.to_dict(),
            ) from error

    def atomic_write_text(
        self,
        root: Path,
        path: Path,
        content: str,
        *,
        purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
    ) -> HardenedPath:
        hardened = self._authorize(root, path, purpose=purpose)
        parent = self.ensure_directory(
            root,
            hardened.relative_path.parent,
            purpose=purpose,
        )
        temporary = hardened.path.with_name(f".{hardened.path.name}.tmp")
        try:
            temporary.write_text(content, encoding="utf-8")
            temporary.replace(hardened.path)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise FilesystemSecurityError(
                "File could not be written atomically.",
                technical_message="Secure atomic write failed.",
                cause=error,
                metadata=hardened.to_dict(),
            ) from error

        ensure_writable_directory(parent.path)
        self._record("atomic_file_written", "info", hardened)
        return hardened

    def copy_file(
        self,
        source_root: Path,
        source: Path,
        destination_root: Path,
        destination: Path,
        *,
        purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
    ) -> HardenedPath:
        source_path = self._authorize(
            source_root,
            source,
            purpose=purpose,
            must_exist=True,
        )
        destination_path = self._authorize(
            destination_root,
            destination,
            purpose=purpose,
        )
        ensure_readable_file(source_path.path)
        self.ensure_directory(
            destination_root,
            destination_path.relative_path.parent,
            purpose=purpose,
        )
        try:
            shutil.copy2(source_path.path, destination_path.path)
        except OSError as error:
            raise FilesystemSecurityError(
                "File could not be copied safely.",
                technical_message="Secure file copy failed.",
                cause=error,
                metadata=destination_path.to_dict(),
            ) from error
        self._record("file_copied", "info", destination_path)
        return destination_path

    def remove_tree(
        self,
        root: Path,
        path: Path,
        *,
        purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
    ) -> HardenedPath:
        hardened = self._authorize(root, path, purpose=purpose, must_exist=True)
        if hardened.path == hardened.root:
            raise FilesystemSecurityError(
                "Directory removal was rejected.",
                technical_message="Authorized root itself cannot be removed.",
                metadata=hardened.to_dict(),
            )
        try:
            shutil.rmtree(hardened.path)
        except OSError as error:
            raise FilesystemSecurityError(
                "Directory could not be removed safely.",
                technical_message="Secure directory removal failed.",
                cause=error,
                metadata=hardened.to_dict(),
            ) from error
        self._record("directory_removed", "info", hardened)
        return hardened

    def _authorize(
        self,
        root: Path,
        path: Path,
        *,
        purpose: HardenedPathPurpose,
        must_exist: bool = False,
    ) -> HardenedPath:
        try:
            return self.policy.authorize(
                root,
                path,
                purpose=purpose,
                must_exist=must_exist,
            )
        except FridayError as error:
            metadata = {"name": path.name, "purpose": purpose.value}
            self.logger.warning(
                "Security hardening policy rejected operation",
                extra={"hardening_error": error.to_log_dict()},
            )
            if self.audit_callback is not None:
                self.audit_callback(
                    "operation_rejected",
                    "warning",
                    "Security hardening policy rejected operation",
                    metadata,
                )
            raise

    def _record(self, operation: str, level: str, path: HardenedPath) -> None:
        self.logger.info(
            "Security hardening policy applied",
            extra={"hardening": path.to_dict() | {"operation": operation}},
        )
        if self.audit_callback is None:
            return
        self.audit_callback(
            operation,
            level,
            "Security hardening policy applied",
            path.to_dict(),
        )
