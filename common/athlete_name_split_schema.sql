-- =====================================================================
-- Athlete Name Split — schema migration
-- Adds first_name / middle_name / last_name columns to athletes and
-- converts the existing `name` column to a STORED generated column so
-- all existing queries (dashboard, analytics, assessments) continue
-- reading athletes.name without any changes.
--
-- Run ONCE, after athlete_login_schema.sql.
-- =====================================================================

USE bjk_athletes;

-- ---------------------------------------------------------------------
-- Step 1: Add the three new name columns (nullable during migration)
-- ---------------------------------------------------------------------
ALTER TABLE athletes
    ADD COLUMN first_name  VARCHAR(100) NOT NULL DEFAULT '' AFTER athlete_code,
    ADD COLUMN middle_name VARCHAR(100) NOT NULL DEFAULT '' AFTER first_name,
    ADD COLUMN last_name   VARCHAR(100) NOT NULL DEFAULT '' AFTER middle_name;

-- ---------------------------------------------------------------------
-- Step 2: Back-fill first_name / middle_name / last_name from name
--   Heuristic:
--     single word  → first_name only
--     two words    → first_name + last_name
--     three+ words → first_name + middle (everything between) + last_name
-- ---------------------------------------------------------------------
UPDATE athletes
SET
    first_name  = CASE
        WHEN name = '' THEN ''
        WHEN LOCATE(' ', TRIM(name)) = 0
            -- single word
            THEN TRIM(name)
        ELSE
            SUBSTRING_INDEX(TRIM(name), ' ', 1)
    END,

    middle_name = CASE
        WHEN name = '' THEN ''
        WHEN LOCATE(' ', TRIM(name)) = 0
            THEN ''
        WHEN LOCATE(' ', TRIM(name)) = LENGTH(TRIM(name)) - LOCATE(' ', REVERSE(TRIM(name)))
            -- only two words (no middle)
            THEN ''
        ELSE
            -- everything between first and last word
            TRIM(SUBSTRING(
                TRIM(name),
                LOCATE(' ', TRIM(name)) + 1,
                LENGTH(TRIM(name))
                    - LOCATE(' ', TRIM(name))
                    - LOCATE(' ', REVERSE(TRIM(name)))
            ))
    END,

    last_name   = CASE
        WHEN name = '' THEN ''
        WHEN LOCATE(' ', TRIM(name)) = 0
            -- single word → no last_name
            THEN ''
        ELSE
            SUBSTRING_INDEX(TRIM(name), ' ', -1)
    END;

-- Re-enable safe update mode.
SET SQL_SAFE_UPDATES = 1;

-- ---------------------------------------------------------------------
-- Step 3: Convert `name` to a STORED generated column so every existing
--         SELECT athletes.name / SELECT * keeps working automatically.
--         We build the display name as: "first [middle] last"
-- ---------------------------------------------------------------------
ALTER TABLE athletes
    MODIFY COLUMN name VARCHAR(300)
        GENERATED ALWAYS AS (
            TRIM(CONCAT_WS(' ',
                NULLIF(TRIM(first_name),  ''),
                NULLIF(TRIM(middle_name), ''),
                NULLIF(TRIM(last_name),   '')
            ))
        ) STORED;

-- Restore the index that was on name (if it existed — DROP is safe if absent)
-- (The original schema.sql had no explicit index on athletes.name, so nothing
--  extra to rebuild here.)


-- =====================================================================
-- Stored Procedure Updates
-- =====================================================================

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_athlete_create — now takes first_name / middle_name / last_name
--   instead of the old combined p_name.  The generated `name` column
--   is computed automatically, so it is NOT inserted explicitly.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_athlete_create $$
CREATE PROCEDURE sp_athlete_create(
    IN  p_code        VARCHAR(255),
    IN  p_first_name  VARCHAR(100),
    IN  p_middle_name VARCHAR(100),
    IN  p_last_name   VARCHAR(100),
    IN  p_email       VARCHAR(255),
    IN  p_phone       VARCHAR(255),
    IN  p_dob         DATE,
    IN  p_sport       VARCHAR(255),
    IN  p_coach_id    INT,
    IN  p_created_by  INT,
    IN  p_user_id     INT,
    OUT p_id          INT
)
BEGIN
    INSERT INTO athletes
        (athlete_code, first_name, middle_name, last_name,
         email, phone, dob, sport, coach_id, created_by, user_id)
    VALUES
        (p_code, p_first_name, p_middle_name, p_last_name,
         p_email, p_phone, p_dob, p_sport, p_coach_id, p_created_by, p_user_id);
    SET p_id = LAST_INSERT_ID();
END $$

-- ---------------------------------------------------------------------
-- sp_athlete_update — now takes first_name / middle_name / last_name
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_athlete_update $$
CREATE PROCEDURE sp_athlete_update(
    IN p_id           INT,
    IN p_first_name   VARCHAR(100),
    IN p_middle_name  VARCHAR(100),
    IN p_last_name    VARCHAR(100),
    IN p_email        VARCHAR(255),
    IN p_phone        VARCHAR(255),
    IN p_dob          DATE,
    IN p_sport        VARCHAR(255),
    IN p_coach_id     INT
)
BEGIN
    UPDATE athletes
    SET first_name  = p_first_name,
        middle_name = p_middle_name,
        last_name   = p_last_name,
        email       = p_email,
        phone       = p_phone,
        dob         = p_dob,
        sport       = p_sport,
        coach_id    = p_coach_id
    WHERE id = p_id;
END $$

DELIMITER ;
