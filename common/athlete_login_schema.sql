-- =====================================================================
-- Athlete Login — schema migration
-- Lets an athlete log in and see their own dashboard/profile, mirroring
-- how coaches already work (a `users` row with role='coach' + coach.user_id).
--
-- Run this once against bjk_athletes. Safe order: after sports_schema.sql
-- and sports_migration.sql.
-- =====================================================================

USE bjk_athletes;

-- Widen users.role in case it was declared as a restrictive ENUM
-- (e.g. ENUM('admin','coach')) — this makes it accept 'athlete' too,
-- and is a harmless no-op if the column was already VARCHAR.
ALTER TABLE users MODIFY COLUMN role VARCHAR(20) NOT NULL;

-- Link an athlete row to an optional login (users) row. NULL = no login
-- access yet — athletes created before this feature, or ones a coach
-- chooses not to grant login to, simply have user_id = NULL.
ALTER TABLE athletes ADD COLUMN user_id INT NULL AFTER id;
ALTER TABLE athletes ADD CONSTRAINT fk_athlete_user FOREIGN KEY (user_id) REFERENCES users(id);

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_athlete_create — rewritten to accept an optional p_user_id.
-- Every other IN param is unchanged from before; p_user_id is simply
-- appended before the OUT param. The single Python call site
-- (create_athlete() in common/models.py) is updated to match.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_athlete_create $$
CREATE PROCEDURE sp_athlete_create(
    IN p_code VARCHAR(255), IN p_name VARCHAR(255), IN p_email VARCHAR(255),
    IN p_phone VARCHAR(255), IN p_dob DATE, IN p_sport VARCHAR(255),
    IN p_coach_id INT, IN p_created_by INT, IN p_user_id INT,
    OUT p_id INT
)
BEGIN
    INSERT INTO athletes (code, name, email, phone, dob, sport, coach_id, created_by, user_id)
    VALUES (p_code, p_name, p_email, p_phone, p_dob, p_sport, p_coach_id, p_created_by, p_user_id);
    SET p_id = LAST_INSERT_ID();
END $$

-- ---------------------------------------------------------------------
-- sp_athlete_get_by_user_id — looks up an athlete by their login's user id
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_athlete_get_by_user_id $$
CREATE PROCEDURE sp_athlete_get_by_user_id(IN p_user_id INT)
BEGIN
    SELECT * FROM athletes WHERE user_id = p_user_id;
END $$

-- ---------------------------------------------------------------------
-- sp_athlete_link_user — grants login access to an athlete created
-- before this feature existed (or one a coach didn't set up initially)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_athlete_link_user $$
CREATE PROCEDURE sp_athlete_link_user(IN p_athlete_id INT, IN p_user_id INT)
BEGIN
    UPDATE athletes SET user_id = p_user_id WHERE id = p_athlete_id;
END $$

-- ---------------------------------------------------------------------
-- sp_athlete_login_info — explicit, dependency-free lookup of an
-- athlete's login state (whether sp_athlete_get_by_id happens to
-- SELECT * or an explicit column list, this always works).
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_athlete_login_info $$
CREATE PROCEDURE sp_athlete_login_info(IN p_athlete_id INT)
BEGIN
    SELECT a.id AS athlete_id, a.user_id, u.username
    FROM athletes a
    LEFT JOIN users u ON u.id = a.user_id
    WHERE a.id = p_athlete_id;
END $$

DELIMITER ;
