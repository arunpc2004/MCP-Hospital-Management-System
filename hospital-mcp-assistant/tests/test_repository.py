from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator
import unittest

from hospital_mcp.errors import NotFoundError
from hospital_mcp.repository import HospitalRepository


class FakeCursor:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self.row = row
        self.executions: list[tuple[str, tuple[Any, ...]]] = []
        self.closed = False

    def execute(self, query: str, parameters: tuple[Any, ...]) -> None:
        self.executions.append((query, parameters))

    def fetchone(self) -> dict[str, Any] | None:
        return self.row

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor

    def cursor(self, dictionary: bool = False) -> FakeCursor:
        if not dictionary:
            raise AssertionError("Repository should request a dictionary cursor")
        return self.fake_cursor


class FakeDatabase:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_connection = FakeConnection(cursor)

    @contextmanager
    def connection(self) -> Iterator[FakeConnection]:
        yield self.fake_connection


class RepositoryTests(unittest.TestCase):
    def test_get_patient_details_uses_parameterized_query(self) -> None:
        cursor = FakeCursor(
            {
                "patient_id": "101",
                "full_name": "John Doe",
                "age": 40,
                "blood_group": "O+",
                "created_at": datetime(2026, 7, 1, 10, 30),
            }
        )
        repository = HospitalRepository(FakeDatabase(cursor))

        patient = repository.get_patient_details("101")

        self.assertEqual(patient["full_name"], "John Doe")
        self.assertEqual(patient["created_at"], "2026-07-01 10:30:00")
        self.assertEqual(cursor.executions[0][1], ("101",))
        self.assertIn("WHERE patient_id = %s", cursor.executions[0][0])
        self.assertTrue(cursor.closed)

    def test_get_patient_details_raises_not_found(self) -> None:
        repository = HospitalRepository(FakeDatabase(FakeCursor(None)))

        with self.assertRaises(NotFoundError):
            repository.get_patient_details("999")


if __name__ == "__main__":
    unittest.main()

