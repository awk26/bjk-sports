-- =====================================================================
-- Fix: sp_user_create rejects role = 'athlete'
-- ---------------------------------------------------------------------
-- The ENUM('admin','coach') on sp_user_create's own p_role PARAMETER
-- (separate from the users.role table column, which was already
-- widened) is what's rejecting 'athlete'. This recreates the procedure
-- identically, just with p_role widened to VARCHAR(20).
--
-- Run this the same way you ran athlete_login_schema.sql /
-- athlete_name_split_schema.sql, e.g.:
--   mysql -h <HOST_JIA> -P <PORT_JIA> -u <USER_JIA> -p <DB_NAME_JIA> < "common\fix_sp_user_create_role.sql"
-- =====================================================================

USE bjk_athletes;

DROP PROCEDURE IF EXISTS sp_user_create;

DELIMITER $$
CREATE PROCEDURE sp_user_create(
    IN p_username VARCHAR(50),
    IN p_password_hash VARCHAR(255),
    IN p_role VARCHAR(20),
    IN p_name VARCHAR(100),
    IN p_email VARCHAR(120),
    IN p_created_by INT,
    OUT p_user_id INT
)
BEGIN
    INSERT INTO users (username, password_hash, role, name, email, created_by)
    VALUES (p_username, p_password_hash, p_role, p_name, p_email, p_created_by);
    SET p_user_id = LAST_INSERT_ID();
END $$
DELIMITER ;

-- Verification: this should now print p_role as varchar(20), not an enum.
-- Look for this in your terminal output after running the file.
SELECT
    SPECIFIC_NAME,
    PARAMETER_NAME,
    DTD_IDENTIFIER
FROM information_schema.PARAMETERS
WHERE SPECIFIC_SCHEMA = 'bjk_athletes'
  AND SPECIFIC_NAME = 'sp_user_create'
  AND PARAMETER_NAME = 'p_role';
