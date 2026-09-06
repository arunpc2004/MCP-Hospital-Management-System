"""Hospital business operations exposed through the official MCP server."""

from __future__ import annotations

from collections.abc import Callable
import logging
from threading import Lock
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_database_settings
from .db import MySQLDatabase
from .errors import HospitalError
from .repository import HospitalRepository


logger = logging.getLogger(__name__)

_repository: HospitalRepository | None = None
_repository_lock = Lock()


def _get_repository() -> HospitalRepository:
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                database = MySQLDatabase(load_database_settings())
                _repository = HospitalRepository(database)
    return _repository


def _execute(operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        return {"success": True, "data": operation()}
    except HospitalError as exc:
        return {
            "success": False,
            "error": {
                "type": exc.error_type,
                "message": str(exc),
            },
        }
    except Exception:
        logger.exception("Unexpected hospital tool failure")
        return {
            "success": False,
            "error": {
                "type": "internal_error",
                "message": "The hospital service could not complete the request",
            },
        }


def get_patient_details(patient_id: str) -> dict[str, Any]:
    """Retrieve one patient by their unique patient ID."""

    return _execute(lambda: _get_repository().get_patient_details(patient_id))


def get_lab_results(patient_id: str) -> dict[str, Any]:
    """Retrieve all lab results for a patient, newest result first."""

    return _execute(lambda: _get_repository().get_lab_results(patient_id))


def search_doctor(specialization: str) -> dict[str, Any]:
    """Search active doctors by a full or partial specialization name."""

    return _execute(lambda: _get_repository().search_doctor(specialization))


def check_medicine_stock(medicine: str) -> dict[str, Any]:
    """Check the current stock quantity for an exact medicine name."""

    return _execute(lambda: _get_repository().check_medicine_stock(medicine))


def schedule_appointment(
    patient_id: str,
    doctor_id: int,
    appointment_at: str,
) -> dict[str, Any]:
    """Schedule an appointment using hospital-local YYYY-MM-DD HH:MM time."""

    return _execute(
        lambda: _get_repository().schedule_appointment(
            patient_id, doctor_id, appointment_at
        )
    )


def cancel_appointment(appointment_id: int) -> dict[str, Any]:
    """Cancel a scheduled appointment using its unique appointment ID."""

    return _execute(lambda: _get_repository().cancel_appointment(appointment_id))


def register_tools(mcp: FastMCP) -> None:
    """Register all hospital functions with a FastMCP server instance."""

    for tool in (
        get_patient_details,
        get_lab_results,
        search_doctor,
        check_medicine_stock,
        schedule_appointment,
        cancel_appointment,
    ):
        mcp.tool()(tool)

