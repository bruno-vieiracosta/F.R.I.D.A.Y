from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class HardenedPathPurpose(StrEnum):
    BACKUP = "backup"
    CONFIGURATION = "configuration"
    DATABASE = "database"
    SECRET = "secret"
    TEMPORARY = "temporary"
    TECHNICAL = "technical"


AuditCallback = Callable[[str, str, str, Mapping[str, object] | None], None]


@dataclass(frozen=True, slots=True)
class HardenedPath:
    root: Path
    path: Path
    purpose: HardenedPathPurpose

    @property
    def relative_path(self) -> Path:
        return self.path.relative_to(self.root)

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.path.name,
            "purpose": self.purpose.value,
            "relative_path": self.relative_path.as_posix(),
        }
