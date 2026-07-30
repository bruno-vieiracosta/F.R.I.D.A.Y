from __future__ import annotations

from pathlib import Path

from friday.security.hardening.exceptions import (
    PathSecurityError,
    PathTraversalError,
    SymlinkTraversalError,
)
from friday.security.hardening.models import HardenedPath, HardenedPathPurpose
from friday.security.hardening.validation import (
    reject_path_traversal,
    validate_path_text,
)


def normalize_path(path: Path) -> Path:
    validate_path_text(path)
    return path.expanduser()


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def resolve_within_root(
    root: Path,
    candidate: Path,
    *,
    purpose: HardenedPathPurpose = HardenedPathPurpose.TECHNICAL,
    must_exist: bool = False,
    reject_symlinks: bool = True,
) -> HardenedPath:
    validate_path_text(root, field_name="root")
    validate_path_text(candidate)
    reject_path_traversal(candidate)

    resolved_root = root.expanduser().resolve(strict=False)
    candidate_path = candidate.expanduser()
    if not candidate_path.is_absolute():
        resolved_as_given = candidate_path.resolve(strict=False)
        if is_relative_to(resolved_as_given, resolved_root):
            candidate_path = resolved_as_given
        else:
            candidate_path = resolved_root / candidate_path

    try:
        resolved_path = candidate_path.resolve(strict=must_exist)
    except OSError as error:
        raise PathSecurityError(
            "Path is invalid.",
            technical_message="Path could not be resolved.",
            cause=error,
            metadata={"name": candidate.name},
        ) from error

    if not is_relative_to(resolved_path, resolved_root):
        raise PathTraversalError(
            "Path traversal was rejected.",
            technical_message="Resolved path escapes the authorized root.",
            metadata={"name": candidate.name, "purpose": purpose.value},
        )

    if reject_symlinks:
        _reject_symlink_escape(resolved_root, candidate_path, resolved_path, purpose)

    return HardenedPath(root=resolved_root, path=resolved_path, purpose=purpose)


def _reject_symlink_escape(
    root: Path,
    candidate_path: Path,
    resolved_path: Path,
    purpose: HardenedPathPurpose,
) -> None:
    if not is_relative_to(resolved_path, root):
        raise SymlinkTraversalError(
            "Symlink traversal was rejected.",
            technical_message="Resolved symlink target escapes the authorized root.",
            metadata={"name": candidate_path.name, "purpose": purpose.value},
        )

    current = candidate_path.anchor
    inspected = Path(current) if current else Path()
    for part in candidate_path.parts[1 if current else 0 :]:
        inspected = inspected / part
        if not inspected.exists():
            break
        if inspected.is_symlink():
            target = inspected.resolve(strict=True)
            if not is_relative_to(target, root):
                raise SymlinkTraversalError(
                    "Symlink traversal was rejected.",
                    technical_message="Symlink target escapes the authorized root.",
                    metadata={"name": inspected.name, "purpose": purpose.value},
                )
