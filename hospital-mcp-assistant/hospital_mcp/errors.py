"""Application-specific exceptions safe to return as structured tool errors."""


class HospitalError(Exception):
    """Base class for expected hospital application errors."""

    error_type = "hospital_error"


class ConfigurationError(HospitalError):
    """Raised when required environment configuration is missing or invalid."""

    error_type = "configuration_error"


class ValidationError(HospitalError):
    """Raised when a tool argument fails validation."""

    error_type = "validation_error"


class NotFoundError(HospitalError):
    """Raised when a requested database record does not exist."""

    error_type = "not_found"


class ConflictError(HospitalError):
    """Raised when an operation conflicts with existing state."""

    error_type = "conflict"

