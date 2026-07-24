-- =============================================================
-- BJK Athletes Management System — Database Schema
-- Target: MySQL 8.x / MariaDB 10.5+
-- (For PostgreSQL: replace AUTO_INCREMENT -> GENERATED ALWAYS AS IDENTITY,
--  ENGINE=InnoDB and ON UPDATE CURRENT_TIMESTAMP need a trigger,
--  ENUM -> CHECK constraint or its own TYPE. BOOLEAN works as-is on both.)
--
-- Note: BOOLEAN columns use no explicit display width, avoiding MySQL 8's
-- "Integer display width is deprecated" warning (1681) that TINYINT(1) triggers.
-- =============================================================

CREATE DATABASE IF NOT EXISTS bjk_athletes
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE bjk_athletes;

-- -------------------------------------------------------------
-- 1. USERS (master)
--    Holds ADMIN and COACH accounts only.
--    SUPER ADMIN is intentionally NOT stored here — it authenticates
--    against hardcoded/env-based credentials in the application layer
--    (see config.py: SUPERADMIN_USERNAME / SUPERADMIN_PASSWORD).
-- -------------------------------------------------------------
CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    username        VARCHAR(50)   NOT NULL UNIQUE,
    password_hash   VARCHAR(255)  NOT NULL,
    role            ENUM('admin', 'coach') NOT NULL,
    name            VARCHAR(100)  NOT NULL,
    email           VARCHAR(120),
    is_archived     BOOLEAN       NOT NULL DEFAULT FALSE,
    created_by      INT NULL,                 -- FK to users.id, NULL if created by super admin
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_archived ON users(is_archived);

-- -------------------------------------------------------------
-- 2. COACHES (master detail — 1:1 extension of users where role='coach')
-- -------------------------------------------------------------
CREATE TABLE coaches (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT NOT NULL UNIQUE,
    specialty       VARCHAR(100),
    is_archived     BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_coaches_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- -------------------------------------------------------------
-- 3. ATHLETES (master)
-- -------------------------------------------------------------
CREATE TABLE athletes (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    athlete_code    VARCHAR(20)   NOT NULL UNIQUE,   -- e.g. ATH-001
    name            VARCHAR(100)  NOT NULL,
    email           VARCHAR(120),
    phone           VARCHAR(20),
    dob             DATE,
    sport           VARCHAR(100),
    coach_id        INT NULL,                        -- FK -> coaches.id
    is_archived     BOOLEAN       NOT NULL DEFAULT FALSE,
    created_by      INT NULL,                        -- FK -> users.id (NULL if created by super admin)
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_athletes_coach
        FOREIGN KEY (coach_id) REFERENCES coaches(id) ON DELETE SET NULL,
    CONSTRAINT fk_athletes_created_by
        FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE INDEX idx_athletes_coach ON athletes(coach_id);
CREATE INDEX idx_athletes_archived ON athletes(is_archived);
CREATE INDEX idx_athletes_sport ON athletes(sport);

-- -------------------------------------------------------------
-- 4. PASSWORD RESET TOKENS (transactional)
-- -------------------------------------------------------------
CREATE TABLE password_reset_tokens (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    token           VARCHAR(255)  NOT NULL UNIQUE,
    user_id         INT NOT NULL,
    expires_at      DATETIME      NOT NULL,
    used            BOOLEAN       NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reset_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE INDEX idx_reset_expires ON password_reset_tokens(expires_at);

-- -------------------------------------------------------------
-- 5. AUDIT LOG (recommended — tracks who created/edited/archived what)
--    actor_username covers 'superadmin' too, since it has no users.id.
-- -------------------------------------------------------------
CREATE TABLE audit_log (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    actor_username  VARCHAR(50)   NOT NULL,
    actor_role      VARCHAR(20)   NOT NULL,     -- superadmin / admin / coach
    action          VARCHAR(50)   NOT NULL,     -- CREATE_ADMIN, ARCHIVE_COACH, CREATE_ATHLETE, ...
    target_type     VARCHAR(20),                -- USER / COACH / ATHLETE
    target_id       INT,
    details         TEXT,
    created_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_audit_actor ON audit_log(actor_username);
CREATE INDEX idx_audit_target ON audit_log(target_type, target_id);
CREATE INDEX idx_audit_created ON audit_log(created_at);

-- -------------------------------------------------------------
-- Seed data (optional) — mirrors the current in-memory defaults
-- Replace the password hashes with real werkzeug generate_password_hash() output.
-- -------------------------------------------------------------
-- INSERT INTO users (username, password_hash, role, name, email, is_archived)
-- VALUES ('admin', '<hash>', 'admin', 'Admin User', 'admin@bjk.com', FALSE);
--
-- INSERT INTO users (username, password_hash, role, name, email, is_archived)
-- VALUES ('coach', '<hash>', 'coach', 'Coach User', 'coach@bjk.com', FALSE);
--
-- INSERT INTO coaches (user_id, specialty, is_archived)
-- SELECT id, 'General', FALSE FROM users WHERE username = 'coach';
