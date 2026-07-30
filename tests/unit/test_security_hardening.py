import logging
import os
import shutil
from pathlib import Path

import pytest

from friday.security.hardening import (
    FilesystemSecurityError,
    HardenedPathPurpose,
    PathSecurityError,
    PathTraversalError,
    PermissionSecurityError,
    SecureFilesystem,
    SecurityPolicy,
    SymlinkTraversalError,
    ensure_readable_file,
    ensure_writable_directory,
    is_relative_to,
    normalize_path,
    resolve_within_root,
    validate_file_name,
    validate_path_text,
)


class RecordingAuditCallback:
    def __init__(self) -> None:
        self.operations: list[str] = []
        self.metadata: list[dict[str, object]] = []

    def __call__(
        self,
        operation: str,
        level: str,
        message: str,
        metadata: dict[str, object] | None,
    ) -> None:
        self.operations.append(f"{level}:{operation}:{message}")
        self.metadata.append(dict(metadata or {}))


def _filesystem(root: Path) -> tuple[SecureFilesystem, RecordingAuditCallback]:
    audit = RecordingAuditCallback()
    return (
        SecureFilesystem(
            policy=SecurityPolicy((root,)),
            logger=logging.getLogger("friday.tests.hardening"),
            audit_callback=audit,
        ),
        audit,
    )


@pytest.mark.unit
def test_paths_are_normalized_and_resolved_inside_root(
    temporary_directory: Path,
) -> None:
    root = temporary_directory / "root"
    root.mkdir()
    file_path = root / "nested" / "file.txt"

    hardened = resolve_within_root(
        root,
        Path("nested") / "file.txt",
        purpose=HardenedPathPurpose.CONFIGURATION,
    )

    assert normalize_path(root) == root
    assert hardened.root == root.resolve(strict=False)
    assert hardened.path == file_path.resolve(strict=False)
    assert hardened.relative_path == Path("nested") / "file.txt"
    assert is_relative_to(hardened.path, hardened.root) is True


@pytest.mark.unit
def test_absolute_paths_are_allowed_only_inside_root(temporary_directory: Path) -> None:
    root = temporary_directory / "root"
    root.mkdir()
    inside = root / "file.txt"
    outside = temporary_directory / "outside.txt"

    assert resolve_within_root(root, inside).path == inside.resolve(strict=False)
    with pytest.raises(PathTraversalError, match="Path traversal"):
        resolve_within_root(root, outside.resolve(strict=False))


@pytest.mark.unit
def test_path_traversal_variants_are_rejected(temporary_directory: Path) -> None:
    root = temporary_directory / "root"
    root.mkdir()

    for candidate in [
        Path("..") / "escape.txt",
        Path("nested") / ".." / ".." / "escape.txt",
        Path("nested") / "..\\escape.txt",
    ]:
        with pytest.raises(PathTraversalError, match="Path traversal"):
            resolve_within_root(root, candidate)


@pytest.mark.unit
def test_file_names_reject_directories_and_traversal() -> None:
    validate_file_name("manifest.json")

    with pytest.raises(PathSecurityError, match="Path is invalid"):
        validate_path_text(Path(" "))

    with pytest.raises(PathSecurityError, match="Path is invalid"):
        validate_path_text(Path("bad\x00path"))

    with pytest.raises(PathSecurityError, match="File name is invalid"):
        validate_file_name(" ")

    with pytest.raises(PathSecurityError, match="File name is invalid"):
        validate_file_name("nested/manifest.json")

    with pytest.raises(PathTraversalError, match="Path traversal"):
        validate_file_name("../manifest.json")


@pytest.mark.unit
def test_symlink_traversal_is_rejected_when_supported(
    temporary_directory: Path,
) -> None:
    root = temporary_directory / "root"
    root.mkdir()
    outside = temporary_directory / "outside"
    outside.mkdir()
    link = root / "outside-link"

    try:
        os.symlink(outside, link, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlink creation is not available: {error}")

    with pytest.raises((PathTraversalError, SymlinkTraversalError)):
        resolve_within_root(root, link, must_exist=True)


@pytest.mark.unit
def test_symlink_inside_root_is_allowed_when_supported(
    temporary_directory: Path,
) -> None:
    root = temporary_directory / "root"
    target = root / "target"
    target.mkdir(parents=True)
    link = root / "inside-link"

    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Symlink creation is not available: {error}")

    hardened = resolve_within_root(root, link, must_exist=True)

    assert hardened.path == target.resolve(strict=True)


@pytest.mark.unit
def test_security_policy_rejects_roots_outside_allowed_area(
    temporary_directory: Path,
) -> None:
    policy = SecurityPolicy((temporary_directory / "allowed",))

    with pytest.raises(PathSecurityError, match="Security policy is invalid"):
        SecurityPolicy(())

    with pytest.raises(PathSecurityError, match="Path root is not allowed"):
        policy.authorize(temporary_directory / "outside", Path("file.txt"))


@pytest.mark.unit
def test_missing_existing_path_requirement_is_reported_as_security_error(
    temporary_directory: Path,
) -> None:
    root = temporary_directory / "root"
    root.mkdir()

    with pytest.raises(PathSecurityError, match="Path is invalid"):
        resolve_within_root(root, Path("missing.txt"), must_exist=True)


@pytest.mark.unit
def test_secure_filesystem_creates_reads_writes_and_removes(
    temporary_directory: Path,
) -> None:
    filesystem, audit = _filesystem(temporary_directory)

    filesystem.ensure_directory(
        temporary_directory,
        Path("technical"),
        purpose=HardenedPathPurpose.TECHNICAL,
    )
    filesystem.atomic_write_text(
        temporary_directory,
        Path("technical") / "metadata.json",
        '{"status":"ok"}',
        purpose=HardenedPathPurpose.TECHNICAL,
    )
    content = filesystem.read_text(
        temporary_directory,
        Path("technical") / "metadata.json",
        purpose=HardenedPathPurpose.TECHNICAL,
    )

    assert content == '{"status":"ok"}'
    assert (temporary_directory / "technical" / "metadata.json").is_file()
    filesystem.remove_tree(
        temporary_directory,
        Path("technical"),
        purpose=HardenedPathPurpose.TECHNICAL,
    )
    assert not (temporary_directory / "technical").exists()
    assert any("atomic_file_written" in operation for operation in audit.operations)


@pytest.mark.unit
def test_secure_filesystem_preserves_original_when_atomic_write_fails(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem, _audit = _filesystem(temporary_directory)
    target = temporary_directory / "file.txt"
    target.write_text("original", encoding="utf-8")

    def fail_write_text(
        self: Path,
        content: str,
        encoding: str | None = None,
    ) -> int:
        raise OSError("write failed")

    monkeypatch.setattr(Path, "write_text", fail_write_text)
    with pytest.raises(FilesystemSecurityError, match="written atomically"):
        filesystem.atomic_write_text(temporary_directory, Path("file.txt"), "new")

    assert target.read_text(encoding="utf-8") == "original"


@pytest.mark.unit
def test_secure_filesystem_wraps_directory_creation_failures(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem, _audit = _filesystem(temporary_directory)

    def fail_mkdir(
        self: Path,
        mode: int = 0o777,
        parents: bool = False,
        exist_ok: bool = False,
    ) -> None:
        raise OSError("mkdir failed")

    monkeypatch.setattr(Path, "mkdir", fail_mkdir)

    with pytest.raises(FilesystemSecurityError, match="Directory could not"):
        filesystem.ensure_directory(temporary_directory, Path("unavailable"))


@pytest.mark.unit
def test_secure_filesystem_wraps_read_failures(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem, _audit = _filesystem(temporary_directory)
    target = temporary_directory / "file.txt"
    target.write_text("content", encoding="utf-8")

    def fail_read_text(self: Path, encoding: str | None = None) -> str:
        raise OSError("read failed")

    monkeypatch.setattr(Path, "read_text", fail_read_text)

    with pytest.raises(FilesystemSecurityError, match="File could not be read"):
        filesystem.read_text(temporary_directory, Path("file.txt"))


@pytest.mark.unit
def test_secure_filesystem_copies_files_inside_authorized_roots(
    temporary_directory: Path,
) -> None:
    source_root = temporary_directory / "source"
    destination_root = temporary_directory / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "database.sqlite").write_text("database", encoding="utf-8")
    filesystem = SecureFilesystem(
        policy=SecurityPolicy((source_root, destination_root)),
        logger=logging.getLogger("friday.tests.hardening"),
    )

    filesystem.copy_file(
        source_root,
        Path("database.sqlite"),
        destination_root,
        Path("database.sqlite"),
    )

    assert (destination_root / "database.sqlite").read_text(encoding="utf-8") == (
        "database"
    )


@pytest.mark.unit
def test_secure_filesystem_wraps_copy_failures(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_root = temporary_directory / "source"
    destination_root = temporary_directory / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "database.sqlite").write_text("database", encoding="utf-8")
    filesystem, _audit = _filesystem(temporary_directory)

    def fail_copy2(source: Path, destination: Path) -> Path:
        raise OSError("copy failed")

    monkeypatch.setattr(shutil, "copy2", fail_copy2)

    with pytest.raises(FilesystemSecurityError, match="File could not be copied"):
        filesystem.copy_file(
            source_root,
            Path("database.sqlite"),
            destination_root,
            Path("database.sqlite"),
        )


@pytest.mark.unit
def test_secure_filesystem_rejects_root_removal_and_wraps_remove_failures(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filesystem, _audit = _filesystem(temporary_directory)
    removable = temporary_directory / "removable"
    removable.mkdir()

    with pytest.raises(FilesystemSecurityError, match="Directory removal"):
        filesystem.remove_tree(temporary_directory, Path("."))

    def fail_rmtree(path: Path) -> None:
        raise OSError("remove failed")

    monkeypatch.setattr(shutil, "rmtree", fail_rmtree)

    with pytest.raises(FilesystemSecurityError, match="Directory could not"):
        filesystem.remove_tree(temporary_directory, Path("removable"))


@pytest.mark.unit
def test_permissions_reject_missing_file_and_non_directory(
    temporary_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing_file = temporary_directory / "missing.txt"
    existing_file = temporary_directory / "file.txt"
    existing_file.write_text("content", encoding="utf-8")

    with pytest.raises(PermissionSecurityError, match="Readable file is required"):
        ensure_readable_file(missing_file)

    with pytest.raises(PermissionSecurityError, match="Writable directory is required"):
        ensure_writable_directory(existing_file)

    def deny_access(path: Path, mode: int) -> bool:
        return False

    monkeypatch.setattr(os, "access", deny_access)

    with pytest.raises(PermissionSecurityError, match="Readable file is required"):
        ensure_readable_file(existing_file)

    with pytest.raises(PermissionSecurityError, match="Writable directory is required"):
        ensure_writable_directory(temporary_directory)


@pytest.mark.unit
def test_blocked_operations_are_logged_and_audited_without_sensitive_content(
    temporary_directory: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    filesystem, audit = _filesystem(temporary_directory)

    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(PathTraversalError),
    ):
        filesystem.atomic_write_text(
            temporary_directory,
            Path("..") / "secret-token.txt",
            "content-that-must-not-leak",
        )

    assert "Security hardening policy rejected operation" in caplog.text
    assert "content-that-must-not-leak" not in caplog.text
    assert "operation_rejected" in audit.operations[0]
    assert "content-that-must-not-leak" not in str(audit.metadata)
