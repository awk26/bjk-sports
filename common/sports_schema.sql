-- =====================================================================
-- Sports Master + Coach/Athlete multi-sport assignment
-- =====================================================================
-- Adds a proper Sports Master table that Super Admin/Admin manage, plus
-- two many-to-many junction tables:
--   coach_sports   -- which sports a coach is assigned to (multi-select)
--   athlete_sports -- which sports an athlete is tracked under (multi-select)
--
-- IMPORTANT: this deliberately does NOT touch the existing `athletes.sport`
-- column or any stored proc that reads it (sp_coach_dashboard_sport_breakdown,
-- sp_superadmin_dashboard_sport_breakdown, sp_org_dashboard_top_athletes,
-- sp_athlete_list, etc). Those keep working exactly as before, reading
-- athletes.sport as a plain string -- the app now keeps that column synced
-- to a comma-joined list of the athlete's selected sport names whenever
-- it's saved via the multi-select form (see routes/*.py), so existing
-- dashboards/breakdowns/filters don't need any changes today. A follow-up
-- pass can rewire those breakdown queries onto athlete_sports directly if
-- true per-sport counting (rather than a combined label for multi-sport
-- athletes) is wanted later.
--
-- Run this once against bjk_athletes, then sports_migration.sql to seed
-- it. Safe to re-run (idempotent CREATE/DROP).

USE bjk_athletes;

CREATE TABLE IF NOT EXISTS sports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    is_archived TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_sports_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS coach_sports (
    coach_id INT NOT NULL,
    sport_id INT NOT NULL,
    PRIMARY KEY (coach_id, sport_id),
    CONSTRAINT fk_coach_sports_coach FOREIGN KEY (coach_id) REFERENCES coaches(id) ON DELETE CASCADE,
    CONSTRAINT fk_coach_sports_sport FOREIGN KEY (sport_id) REFERENCES sports(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS athlete_sports (
    athlete_id INT NOT NULL,
    sport_id INT NOT NULL,
    PRIMARY KEY (athlete_id, sport_id),
    CONSTRAINT fk_athlete_sports_athlete FOREIGN KEY (athlete_id) REFERENCES athletes(id) ON DELETE CASCADE,
    CONSTRAINT fk_athlete_sports_sport FOREIGN KEY (sport_id) REFERENCES sports(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

DELIMITER $$

-- ---- Sports Master CRUD ----

DROP PROCEDURE IF EXISTS sp_sport_create $$
CREATE PROCEDURE sp_sport_create(IN p_name VARCHAR(100), OUT p_id INT)
BEGIN
    INSERT INTO sports (name) VALUES (p_name);
    SET p_id = LAST_INSERT_ID();
END $$

DROP PROCEDURE IF EXISTS sp_sport_update $$
CREATE PROCEDURE sp_sport_update(IN p_id INT, IN p_name VARCHAR(100))
BEGIN
    UPDATE sports SET name = p_name WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS sp_sport_archive $$
CREATE PROCEDURE sp_sport_archive(IN p_id INT, IN p_is_archived TINYINT(1))
BEGIN
    UPDATE sports SET is_archived = p_is_archived WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS sp_sport_get_by_id $$
CREATE PROCEDURE sp_sport_get_by_id(IN p_id INT)
BEGIN
    SELECT id, name, is_archived, created_at FROM sports WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS sp_sport_get_by_name $$
CREATE PROCEDURE sp_sport_get_by_name(IN p_name VARCHAR(100))
BEGIN
    SELECT id, name, is_archived, created_at FROM sports WHERE name = p_name;
END $$

DROP PROCEDURE IF EXISTS sp_sport_list $$
CREATE PROCEDURE sp_sport_list(IN p_is_archived TINYINT(1))
BEGIN
    SELECT id, name, is_archived, created_at
    FROM sports
    WHERE (p_is_archived IS NULL OR is_archived = p_is_archived)
    ORDER BY name;
END $$

-- ---- Coach <-> Sports (multi-select assignment) ----

DROP PROCEDURE IF EXISTS sp_coach_sports_get $$
CREATE PROCEDURE sp_coach_sports_get(IN p_coach_id INT)
BEGIN
    SELECT s.id, s.name
    FROM coach_sports cs
    JOIN sports s ON s.id = cs.sport_id
    WHERE cs.coach_id = p_coach_id
    ORDER BY s.name;
END $$

DROP PROCEDURE IF EXISTS sp_coach_sports_clear $$
CREATE PROCEDURE sp_coach_sports_clear(IN p_coach_id INT)
BEGIN
    DELETE FROM coach_sports WHERE coach_id = p_coach_id;
END $$

DROP PROCEDURE IF EXISTS sp_coach_sports_add $$
CREATE PROCEDURE sp_coach_sports_add(IN p_coach_id INT, IN p_sport_id INT)
BEGIN
    INSERT IGNORE INTO coach_sports (coach_id, sport_id) VALUES (p_coach_id, p_sport_id);
END $$

-- ---- Athlete <-> Sports (multi-select assignment) ----

DROP PROCEDURE IF EXISTS sp_athlete_sports_get $$
CREATE PROCEDURE sp_athlete_sports_get(IN p_athlete_id INT)
BEGIN
    SELECT s.id, s.name
    FROM athlete_sports asp
    JOIN sports s ON s.id = asp.sport_id
    WHERE asp.athlete_id = p_athlete_id
    ORDER BY s.name;
END $$

DROP PROCEDURE IF EXISTS sp_athlete_sports_clear $$
CREATE PROCEDURE sp_athlete_sports_clear(IN p_athlete_id INT)
BEGIN
    DELETE FROM athlete_sports WHERE athlete_id = p_athlete_id;
END $$

DROP PROCEDURE IF EXISTS sp_athlete_sports_add $$
CREATE PROCEDURE sp_athlete_sports_add(IN p_athlete_id INT, IN p_sport_id INT)
BEGIN
    INSERT IGNORE INTO athlete_sports (athlete_id, sport_id) VALUES (p_athlete_id, p_sport_id);
END $$

DELIMITER ;
