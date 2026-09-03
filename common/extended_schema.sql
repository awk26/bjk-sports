-- =====================================================================
-- BJK Athletes Management System — Extended Schema Reference
-- Note: Python app startup (models.ensure_schema_extensions()) automatically
-- applies all extended columns and tables to your MySQL database.
-- =====================================================================

USE bjk_athletes;

-- ---------------------------------------------------------------------
-- 1. ATHLETES TABLE EXTENSION
-- If columns already exist, individual statements will be skipped by MySQL.
-- ---------------------------------------------------------------------
-- ALTER TABLE athletes ADD COLUMN height DECIMAL(5,2) NULL;
-- ALTER TABLE athletes ADD COLUMN weight DECIMAL(5,2) NULL;
-- ALTER TABLE athletes ADD COLUMN parent_name VARCHAR(255) NULL;
-- ALTER TABLE athletes ADD COLUMN father_name VARCHAR(255) NULL;
-- ALTER TABLE athletes ADD COLUMN mother_name VARCHAR(255) NULL;
-- ALTER TABLE athletes ADD COLUMN address_line1 VARCHAR(255) NULL;
-- ALTER TABLE athletes ADD COLUMN address_line2 VARCHAR(255) NULL;
-- ALTER TABLE athletes ADD COLUMN city VARCHAR(100) NULL;
-- ALTER TABLE athletes ADD COLUMN state VARCHAR(100) NULL;
-- ALTER TABLE athletes ADD COLUMN postal_code VARCHAR(20) NULL;
-- ALTER TABLE athletes ADD COLUMN physical_params TEXT NULL;
-- ALTER TABLE athletes ADD COLUMN gender VARCHAR(20) NULL;
-- ALTER TABLE athletes ADD COLUMN blood_group VARCHAR(10) NULL;
-- ALTER TABLE athletes ADD COLUMN emergency_contact_name VARCHAR(100) NULL;
-- ALTER TABLE athletes ADD COLUMN emergency_contact_phone VARCHAR(20) NULL;
-- ALTER TABLE athletes ADD COLUMN sporting_experience_years VARCHAR(50) NULL;
-- ALTER TABLE athletes ADD COLUMN sport_discipline VARCHAR(100) NULL;
-- ALTER TABLE athletes ADD COLUMN level_of_participation VARCHAR(50) NULL;
-- ALTER TABLE athletes ADD COLUMN previous_achievements TEXT NULL;
-- ALTER TABLE athletes ADD COLUMN nationality VARCHAR(50) NULL;
-- ALTER TABLE athletes ADD COLUMN id_proof_type VARCHAR(50) NULL;
-- ALTER TABLE athletes ADD COLUMN id_proof_number VARCHAR(50) NULL;
-- ALTER TABLE athletes ADD COLUMN school_name VARCHAR(150) NULL;
-- ALTER TABLE athletes ADD COLUMN school_grade VARCHAR(20) NULL;
-- ALTER TABLE athletes ADD COLUMN admission_date DATE NULL;
-- ALTER TABLE athletes ADD COLUMN medical_notes TEXT NULL;

-- ---------------------------------------------------------------------
-- 2. COACHES TABLE EXTENSION
-- ---------------------------------------------------------------------
-- ALTER TABLE coaches ADD COLUMN gender VARCHAR(20) NULL;
-- ALTER TABLE coaches ADD COLUMN dob DATE NULL;
-- ALTER TABLE coaches ADD COLUMN phone VARCHAR(20) NULL;
-- ALTER TABLE coaches ADD COLUMN address_line1 VARCHAR(255) NULL;
-- ALTER TABLE coaches ADD COLUMN address_line2 VARCHAR(255) NULL;
-- ALTER TABLE coaches ADD COLUMN city VARCHAR(100) NULL;
-- ALTER TABLE coaches ADD COLUMN state VARCHAR(100) NULL;
-- ALTER TABLE coaches ADD COLUMN postal_code VARCHAR(20) NULL;
-- ALTER TABLE coaches ADD COLUMN education TEXT NULL;
-- ALTER TABLE coaches ADD COLUMN certifications TEXT NULL;
-- ALTER TABLE coaches ADD COLUMN additional_info TEXT NULL;
-- ALTER TABLE coaches ADD COLUMN achievements TEXT NULL;

-- ---------------------------------------------------------------------
-- 3. EVENTS TABLE CREATION (Safe to run anytime)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    event_name      VARCHAR(255)  NOT NULL,
    description     TEXT NULL,
    event_date      DATE NOT NULL,
    end_date        DATE NULL,
    location        VARCHAR(255)  NOT NULL,
    level           ENUM('District', 'State', 'National', 'International') NOT NULL DEFAULT 'District',
    created_by      INT NULL,
    is_archived     BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_events_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Create indexes if table was just created
SET @dbname = DATABASE();
SET @tablename = 'events';

-- Verification Query: Run this to inspect all columns in your athletes table:
-- SHOW COLUMNS FROM athletes;
