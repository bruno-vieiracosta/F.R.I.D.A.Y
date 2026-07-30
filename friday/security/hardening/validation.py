from __future__ import annotations

from pathlib import Path

from friday.security.hardening.exceptions import PathSecurityError, PathTraversalError


def validate_path_text(path: Path, *, field_name: str = "path") -> None:
    text = str(path)
    if not text.strip():
        raise PathSecurityError(
            "Path is invalid.",
            technical_message="Path text must not be empty.",
            metadata={"field": field_name},
        )

    if "\x00" in text:
        raise PathSecurityError(
            "Path is invalid.",
            technical_message="Path text must not contain null bytes.",
            metadata={"field": field_name},
        )


def reject_path_traversal(path: Path) -> None:
    if ".." in path.parts:
        raise PathTraversalError(
            "Path traversal was rejected.",
            technical_message="Path must not contain parent directory references.",
            metadata={"name": path.name},
        )


def validate_file_name(name: str, *, field_name: str = "name") -> None:
    cleaned = name.strip()
    if not cleaned:
        raise PathSecurityError(
            "File name is invalid.",
            technical_message="File names must not be empty.",
            metadata={"field": field_name},
        )

    candidate = Path(cleaned)
    reject_path_traversal(candidate)
    if candidate.name != cleaned:
        raise PathSecurityError(
            "File name is invalid.",
            technical_message="File names must not include directories.",
            metadata={"field": field_name},
        )
