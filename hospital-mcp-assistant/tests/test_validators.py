from datetime import datetime, timedelta
import unittest

from hospital_mcp.errors import ValidationError
from hospital_mcp.validators import (
    parse_appointment_datetime,
    validate_patient_id,
    validate_positive_integer,
    validate_required_text,
)


class ValidatorTests(unittest.TestCase):
    def test_patient_id_accepts_letters_numbers_and_hyphens(self) -> None:
        self.assertEqual(validate_patient_id(" AB-101 "), "AB-101")

    def test_patient_id_rejects_sql_like_characters(self) -> None:
        with self.assertRaises(ValidationError):
            validate_patient_id("101' OR 1=1")

    def test_required_text_rejects_blank_value(self) -> None:
        with self.assertRaises(ValidationError):
            validate_required_text("   ", "medicine", 150)

    def test_positive_integer_rejects_boolean(self) -> None:
        with self.assertRaises(ValidationError):
            validate_positive_integer(True, "doctor_id")

    def test_positive_integer_accepts_numeric_string(self) -> None:
        self.assertEqual(validate_positive_integer("7", "doctor_id"), 7)

    def test_appointment_datetime_accepts_future_local_time(self) -> None:
        future = (datetime.now() + timedelta(days=2)).replace(
            second=45, microsecond=123
        )
        parsed = parse_appointment_datetime(
            future.isoformat(sep=" ", timespec="seconds")
        )

        self.assertEqual(parsed.second, 0)
        self.assertEqual(parsed.microsecond, 0)

    def test_appointment_datetime_rejects_past_time(self) -> None:
        past = datetime.now() - timedelta(minutes=1)
        with self.assertRaises(ValidationError):
            parse_appointment_datetime(
                past.isoformat(sep=" ", timespec="seconds")
            )

    def test_appointment_datetime_rejects_wrong_format(self) -> None:
        with self.assertRaises(ValidationError):
            parse_appointment_datetime("tomorrow morning")


if __name__ == "__main__":
    unittest.main()

