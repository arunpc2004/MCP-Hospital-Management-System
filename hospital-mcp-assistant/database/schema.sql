CREATE DATABASE IF NOT EXISTS hospital_mcp
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE hospital_mcp;

CREATE TABLE IF NOT EXISTS patients (
    patient_id VARCHAR(20) PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    age TINYINT UNSIGNED NOT NULL,
    blood_group VARCHAR(5) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_patient_age CHECK (age <= 130)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS lab_results (
    lab_result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL,
    test_name VARCHAR(120) NOT NULL,
    result_text VARCHAR(500) NOT NULL,
    result_status ENUM('NORMAL', 'ABNORMAL', 'PENDING') NOT NULL DEFAULT 'PENDING',
    tested_at DATETIME NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_lab_patient
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_lab_patient_date (patient_id, tested_at DESC)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS doctors (
    doctor_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    specialization VARCHAR(120) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_doctor_specialization (specialization, active)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS appointments (
    appointment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    patient_id VARCHAR(20) NOT NULL,
    doctor_id INT UNSIGNED NOT NULL,
    appointment_at DATETIME NOT NULL,
    status ENUM('SCHEDULED', 'CANCELLED', 'COMPLETED') NOT NULL DEFAULT 'SCHEDULED',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cancelled_at DATETIME NULL,
    CONSTRAINT fk_appointment_patient
        FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_appointment_doctor
        FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_appointment_patient (patient_id, appointment_at DESC),
    INDEX idx_appointment_slot (doctor_id, appointment_at, status)
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS medicines (
    medicine_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    medicine_name VARCHAR(150) NOT NULL UNIQUE,
    stock_quantity INT UNSIGNED NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE = InnoDB;

CREATE TABLE IF NOT EXISTS appointment_audit (
    event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    appointment_id BIGINT UNSIGNED NOT NULL,
    event_type ENUM('SCHEDULED', 'CANCELLED') NOT NULL,
    event_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details JSON NULL,
    CONSTRAINT fk_audit_appointment
        FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_audit_appointment (appointment_id, event_at DESC)
) ENGINE = InnoDB;

