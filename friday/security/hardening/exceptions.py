from __future__ import annotations

from friday.shared.errors import ErrorCategory, ErrorDescriptor, SecurityError


class HardeningError(SecurityError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-HARDENING-001",
        category=ErrorCategory.SECURITY,
        public_message="The platform security policy rejected the operation.",
    )


class PathSecurityError(HardeningError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-PATH-001",
        category=ErrorCategory.SECURITY,
        public_message="The path is not allowed by the platform security policy.",
    )


class PathTraversalError(PathSecurityError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-PATH-TRAVERSAL",
        category=ErrorCategory.SECURITY,
        public_message="Path traversal was rejected.",
    )


class SymlinkTraversalError(PathSecurityError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-SYMLINK-TRAVERSAL",
        category=ErrorCategory.SECURITY,
        public_message="Symlink traversal was rejected.",
    )


class PermissionSecurityError(HardeningError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-PERMISSION-001",
        category=ErrorCategory.SECURITY,
        public_message="The path does not have the required access permissions.",
    )


class FilesystemSecurityError(HardeningError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-FILESYSTEM-001",
        category=ErrorCategory.SECURITY,
        public_message="The secure filesystem operation could not be completed.",
    )
