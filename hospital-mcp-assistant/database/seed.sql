USE hospital_mcp;

INSERT INTO patients (patient_id, full_name, age, blood_group)
VALUES
    ('101', 'John Doe', 40, 'O+'),
    ('102', 'Priya Sharma', 29, 'B+'),
    ('103', 'Arjun Rao', 35, 'A-')
ON DUPLICATE KEY UPDATE
    full_name = VALUES(full_name),
    age = VALUES(age),
    blood_group = VALUES(blood_group);

INSERT INTO lab_results
    (lab_result_id, patient_id, test_name, result_text, result_status, tested_at)
VALUES
    (1, '101', 'Blood Sugar', 'Fasting glucose within normal range', 'NORMAL', '2026-07-01 09:00:00'),
    (2, '101', 'Complete Blood Count', 'Haemoglobin and cell counts within normal range', 'NORMAL', '2026-07-05 10:30:00'),
    (3, '102', 'Thyroid Profile', 'TSH slightly elevated; physician review advised', 'ABNORMAL', '2026-07-04 11:15:00')
ON DUPLICATE KEY UPDATE
    patient_id = VALUES(patient_id),
    test_name = VALUES(test_name),
    result_text = VALUES(result_text),
    result_status = VALUES(result_status),
    tested_at = VALUES(tested_at);

INSERT INTO doctors (doctor_id, full_name, specialization, active)
VALUES
    (1, 'Dr. Smith', 'Cardiology', TRUE),
    (2, 'Dr. Adam', 'Neurology', TRUE),
    (3, 'Dr. Brown', 'General Medicine', TRUE),
    (4, 'Dr. Meera Nair', 'Endocrinology', TRUE)
ON DUPLICATE KEY UPDATE
    full_name = VALUES(full_name),
    specialization = VALUES(specialization),
    active = VALUES(active);

INSERT INTO medicines (medicine_id, medicine_name, stock_quantity)
VALUES
    (1, 'Paracetamol', 120),
    (2, 'Insulin', 45),
    (3, 'Amoxicillin', 0),
    (4, 'Metformin', 75)
ON DUPLICATE KEY UPDATE
    medicine_name = VALUES(medicine_name),
    stock_quantity = VALUES(stock_quantity);

INSERT INTO appointments
    (appointment_id, patient_id, doctor_id, appointment_at, status)
VALUES
    (1, '101', 3, '2030-01-15 10:00:00', 'SCHEDULED')
ON DUPLICATE KEY UPDATE
    patient_id = VALUES(patient_id),
    doctor_id = VALUES(doctor_id),
    appointment_at = VALUES(appointment_at),
    status = VALUES(status);

INSERT INTO appointment_audit
    (event_id, appointment_id, event_type, details)
VALUES
    (1, 1, 'SCHEDULED', JSON_OBJECT('source', 'seed_data'))
ON DUPLICATE KEY UPDATE
    appointment_id = VALUES(appointment_id),
    event_type = VALUES(event_type),
    details = VALUES(details);

