from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.security.hardening.exceptions import PathSecurityError
from friday.security.hardening.models import HardenedPath, HardenedPathPurpose
from friday.security.hardening.paths import is_relative_to, resolve_within_root


@dataclass(frozen=True, slots=True)
class SecurityPolicy:
    allowed_roots: tuple[Path, ...]
    reject_symlinks: bool = True

    def __post_init__(self) -> None:
        roots = tuple(
            dict.fromkeys(
                root.expanduser().resolve(strict=False) for root in self.allowed_roots
            )
        )
        if not roots:
            raise PathSecurityError(
                "Security policy is invalid.",
                technical_message="At least one authorized root must be configured.",
            )
        object.__setattr__(self, "allowed_roots", roots)

    def authorize(
        self,
        root: Path,
        candidate: Path,
        *,
        purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
        must_exist: bool = False,
    ) -> HardenedPath:
        normalized_root = root.expanduser().resolve(strict=False)
        root_is_allowed = any(
            is_relative_to(normalized_root, allowed) for allowed in self.allowed_roots
        )
        if not root_is_allowed:
            raise PathSecurityError(
                "Path root is not allowed.",
                technical_message="Requested root is outside the configured roots.",
                metadata={"name": normalized_root.name, "purpose": purpose.value},
            )

        return resolve_within_root(
            normalized_root,
            candidate,
            purpose=purpose,
            must_exist=must_exist,
            reject_symlinks=self.reject_symlinks,
        )


def build_default_security_policy(
    *,
    data_directory: Path,
    logs_directory: Path,
    backups_directory: Path,
    temporary_directory: Path,
    database_path: Path,
    secrets_file_path: Path,
) -> SecurityPolicy:
    return SecurityPolicy(
        allowed_roots=(
            data_directory,
            logs_directory,
            backups_directory,
            temporary_directory,
            database_path.parent,
            secrets_file_path.parent,
        )
    )
