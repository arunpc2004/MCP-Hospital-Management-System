"""Parameterized SQL operations used by the hospital MCP tools."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, ContextManager, Iterator, Protocol

from .errors import ConflictError, NotFoundError
from .validators import (
    parse_appointment_datetime,
    validate_patient_id,
    validate_positive_integer,
    validate_required_text,
)


class ConnectionProvider(Protocol):
    def connection(self) -> ContextManager[Any]: ...


@contextmanager
def _dictionary_cursor(connection: Any) -> Iterator[Any]:
    cursor = connection.cursor(dictionary=True)
    try:
        yield cursor
    finally:
        cursor.close()


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_value(value) for key, value in row.items()}


class HospitalRepository:
    """Hospital data access layer with no LLM or MCP dependencies."""

    def __init__(self, database: ConnectionProvider) -> None:
        self._database = database

    def get_patient_details(self, patient_id: str) -> dict[str, Any]:
        patient_id = validate_patient_id(patient_id)

        query = """
            SELECT patient_id, full_name, age, blood_group, created_at
            FROM patients
            WHERE patient_id = %s
        """

        with self._database.connection() as connection:
            with _dictionary_cursor(connection) as cursor:
                cursor.execute(query, (patient_id,))
                patient = cursor.fetchone()

        if patient is None:
            raise NotFoundError(f"No patient found with ID {patient_id}")
        return _serialize_row(patient)

    def get_lab_results(self, patient_id: str) -> list[dict[str, Any]]:
        patient_id = validate_patient_id(patient_id)

        patient_query = "SELECT patient_id FROM patients WHERE patient_id = %s"
        results_query = """
            SELECT
                lab_result_id,
                patient_id,
                test_name,
                result_text,
                result_status,
                tested_at
            FROM lab_results
            WHERE patient_id = %s
            ORDER BY tested_at DESC
        """

        with self._database.connection() as connection:
            with _dictionary_cursor(connection) as cursor:
                cursor.execute(patient_query, (patient_id,))
                if cursor.fetchone() is None:
                    raise NotFoundError(f"No patient found with ID {patient_id}")

                cursor.execute(results_query, (patient_id,))
                results = cursor.fetchall()

        return [_serialize_row(result) for result in results]

    def search_doctor(self, specialization: str) -> list[dict[str, Any]]:
        specialization = validate_required_text(
            specialization, "specialization", 120
        )

        query = """
            SELECT doctor_id, full_name, specialization
            FROM doctors
            WHERE active = TRUE
              AND specialization LIKE %s
            ORDER BY full_name
        """

        with self._database.connection() as connection:
            with _dictionary_cursor(connection) as cursor:
                cursor.execute(query, (f"%{specialization}%",))
                doctors = cursor.fetchall()

        return [_serialize_row(doctor) for doctor in doctors]

    def check_medicine_stock(self, medicine: str) -> dict[str, Any]:
        medicine = validate_required_text(medicine, "medicine", 150)

        query = """
            SELECT medicine_id, medicine_name, stock_quantity, updated_at
            FROM medicines
            WHERE LOWER(medicine_name) = LOWER(%s)
        """

        with self._database.connection() as connection:
            with _dictionary_cursor(connection) as cursor:
                cursor.execute(query, (medicine,))
                stock = cursor.fetchone()

        if stock is None:
            raise NotFoundError(f"Medicine '{medicine}' was not found")

        serialized = _serialize_row(stock)
        serialized["in_stock"] = serialized["stock_quantity"] > 0
        return serialized

    def schedule_appointment(
        self,
        patient_id: str,
        doctor_id: int,
        appointment_at: str,
    ) -> dict[str, Any]:
        patient_id = validate_patient_id(patient_id)
        doctor_id = validate_positive_integer(doctor_id, "doctor_id")
        parsed_time = parse_appointment_datetime(appointment_at)

        with self._database.connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                connection.start_transaction()

                cursor.execute(
                    "SELECT patient_id FROM patients WHERE patient_id = %s FOR UPDATE",
                    (patient_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError(f"No patient found with ID {patient_id}")

                cursor.execute(
                    """
                    SELECT doctor_id, full_name, specialization
                    FROM doctors
                    WHERE doctor_id = %s AND active = TRUE
                    FOR UPDATE
                    """,
                    (doctor_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError(
                        f"No active doctor found with ID {doctor_id}"
                    )

                cursor.execute(
                    """
                    SELECT appointment_id
                    FROM appointments
                    WHERE doctor_id = %s
                      AND appointment_at = %s
                      AND status = 'SCHEDULED'
                    FOR UPDATE
                    """,
                    (doctor_id, parsed_time),
                )
                if cursor.fetchone() is not None:
                    raise ConflictError(
                        "The doctor already has an appointment at that time"
                    )

                cursor.execute(
                    """
                    INSERT INTO appointments
                        (patient_id, doctor_id, appointment_at, status)
                    VALUES (%s, %s, %s, 'SCHEDULED')
                    """,
                    (patient_id, doctor_id, parsed_time),
                )
                appointment_id = cursor.lastrowid

                cursor.execute(
                    """
                    INSERT INTO appointment_audit
                        (appointment_id, event_type, details)
                    VALUES (%s, 'SCHEDULED', JSON_OBJECT('source', 'mcp_tool'))
                    """,
                    (appointment_id,),
                )

                cursor.execute(
                    """
                    SELECT
                        a.appointment_id,
                        a.patient_id,
                        p.full_name AS patient_name,
                        a.doctor_id,
                        d.full_name AS doctor_name,
                        d.specialization,
                        a.appointment_at,
                        a.status
                    FROM appointments AS a
                    JOIN patients AS p ON p.patient_id = a.patient_id
                    JOIN doctors AS d ON d.doctor_id = a.doctor_id
                    WHERE a.appointment_id = %s
                    """,
                    (appointment_id,),
                )
                appointment = cursor.fetchone()
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

        return _serialize_row(appointment)

    def cancel_appointment(self, appointment_id: int) -> dict[str, Any]:
        appointment_id = validate_positive_integer(
            appointment_id, "appointment_id"
        )

        with self._database.connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                connection.start_transaction()
                cursor.execute(
                    """
                    SELECT appointment_id, status
                    FROM appointments
                    WHERE appointment_id = %s
                    FOR UPDATE
                    """,
                    (appointment_id,),
                )
                current = cursor.fetchone()

                if current is None:
                    raise NotFoundError(
                        f"No appointment found with ID {appointment_id}"
                    )
                if current["status"] == "COMPLETED":
                    raise ConflictError("A completed appointment cannot be cancelled")

                already_cancelled = current["status"] == "CANCELLED"
                if not already_cancelled:
                    cursor.execute(
                        """
                        UPDATE appointments
                        SET status = 'CANCELLED', cancelled_at = NOW()
                        WHERE appointment_id = %s
                        """,
                        (appointment_id,),
                    )
                    cursor.execute(
                        """
                        INSERT INTO appointment_audit
                            (appointment_id, event_type, details)
                        VALUES (%s, 'CANCELLED', JSON_OBJECT('source', 'mcp_tool'))
                        """,
                        (appointment_id,),
                    )

                cursor.execute(
                    """
                    SELECT
                        a.appointment_id,
                        a.patient_id,
                        p.full_name AS patient_name,
                        a.doctor_id,
                        d.full_name AS doctor_name,
                        a.appointment_at,
                        a.status,
                        a.cancelled_at
                    FROM appointments AS a
                    JOIN patients AS p ON p.patient_id = a.patient_id
                    JOIN doctors AS d ON d.doctor_id = a.doctor_id
                    WHERE a.appointment_id = %s
                    """,
                    (appointment_id,),
                )
                appointment = cursor.fetchone()
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

        result = _serialize_row(appointment)
        result["already_cancelled"] = already_cancelled
        return result

