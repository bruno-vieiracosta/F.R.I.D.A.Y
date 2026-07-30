from __future__ import annotations

from friday.shared.errors import ErrorCategory, ErrorDescriptor, SecurityError


class SecretManagementError(SecurityError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-SECRET-001",
        category=ErrorCategory.SECURITY,
        public_message="The secret management operation could not be completed.",
    )


class SecretNotFoundError(SecretManagementError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-SECRET-404",
        category=ErrorCategory.SECURITY,
        public_message="The requested secret is not available.",
    )


class SecretProviderUnavailableError(SecretManagementError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-SECRET-002",
        category=ErrorCategory.SECURITY,
        public_message="The configured secret provider is not available.",
    )


class SecretConfigurationError(SecretManagementError):
    descriptor = ErrorDescriptor(
        code="FRIDAY-SECURITY-SECRET-003",
        category=ErrorCategory.SECURITY,
        public_message="The secret provider configuration is invalid.",
    )
