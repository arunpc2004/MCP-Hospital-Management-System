"""Validation helpers shared by repository operations."""

from __future__ import annotations

from datetime import datetime

from .errors import ValidationError


def validate_required_text(value: str, field: str, max_length: int) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field} must be a string")

    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field} is required")
    if len(cleaned) > max_length:
        raise ValidationError(
            f"{field} cannot be longer than {max_length} characters"
        )
    return cleaned


def validate_patient_id(patient_id: str) -> str:
    cleaned = validate_required_text(patient_id, "patient_id", 20)
    if not cleaned.replace("-", "").isalnum():
        raise ValidationError(
            "patient_id may contain only letters, numbers, and hyphens"
        )
    return cleaned


def validate_positive_integer(value: int, field: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{field} must be a positive integer")

    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a positive integer") from exc

    if parsed <= 0:
        raise ValidationError(f"{field} must be a positive integer")
    return parsed


def parse_appointment_datetime(value: str) -> datetime:
    cleaned = validate_required_text(value, "appointment_at", 30)

    try:
        appointment_at = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValidationError(
            "appointment_at must use YYYY-MM-DD HH:MM format"
        ) from exc

    if appointment_at.tzinfo is not None:
        raise ValidationError(
            "appointment_at must not contain a timezone; use hospital local time"
        )

    if appointment_at <= datetime.now():
        raise ValidationError("appointment_at must be in the future")

    return appointment_at.replace(second=0, microsecond=0)

