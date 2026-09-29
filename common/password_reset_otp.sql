-- =====================================================================
-- Forgot Password via email OTP
--
-- Adds the password_reset_otps table plus the stored procedures the OTP
-- flow calls (see common/models.py -> create_password_otp /
-- verify_password_otp, and routes/auth.py).
--
-- Run once on every environment (dev AND prod). Name the target database on
-- the command line -- this file deliberately contains NO "USE" statement:
--
--   dev :  mysql -h <host> -P <port> -u <user> -p bjk_athletes < common/password_reset_otp.sql
--   prod:  mysql -h <host> -P <port> -u <user> -p bjksports    < common/password_reset_otp.sql
--
-- (Every other .sql file in this repo hardcodes "USE bjk_athletes", which
-- silently targets the DEV database even when you meant to run it against
-- prod. Hence no USE here: whatever database you name is the one that gets
-- changed, and nothing else can.)
--
-- Safe to re-run: the table uses CREATE TABLE IF NOT EXISTS and every
-- procedure is dropped before being recreated.
--
-- NOTE ON COLLATION: the collation is stated explicitly here. Stored
-- procedure string parameters inherit the *database* collation, so a table
-- left on a different collation makes "col = p_param" fail at runtime with
-- ERROR 1267 (that is exactly what broke the sports tables). Keep this in
-- step with the rest of the schema: utf8mb4 / utf8mb4_unicode_ci.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Table
--
-- The OTP itself is never stored. Only a werkzeug password hash of it is
-- kept, so a leaked database row cannot be replayed as a valid code.
-- `attempts` caps guessing: a 6-digit code is only 1,000,000 options, so
-- the attempt limit is what actually makes it safe.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS password_reset_otps (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    otp_hash    VARCHAR(255)  NOT NULL,
    expires_at  DATETIME      NOT NULL,
    attempts    TINYINT       NOT NULL DEFAULT 0,
    used        TINYINT(1)    NOT NULL DEFAULT 0,
    created_at  TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_reset_otp_user (user_id),
    KEY idx_reset_otp_expires (expires_at),
    CONSTRAINT fk_reset_otp_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- If the table already existed on another collation, bring it in line.
ALTER TABLE password_reset_otps
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_user_get_by_email -- the forgot-password form asks for an email, not
-- a username, so this is the lookup that starts the flow. Archived users
-- are excluded: a deactivated account must not be resettable.
--
-- users.email has no UNIQUE constraint, so this can in principle return
-- more than one row; the caller takes the first (lowest id).
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_user_get_by_email $$
CREATE PROCEDURE sp_user_get_by_email(IN p_email VARCHAR(120))
BEGIN
    SELECT * FROM users
     WHERE email = p_email
       AND is_archived = 0
     ORDER BY id
     LIMIT 1;
END $$

-- ---------------------------------------------------------------------
-- sp_reset_otp_invalidate_for_user -- burns any outstanding codes for the
-- user. Called before issuing a new one so only the newest code works.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_reset_otp_invalidate_for_user $$
CREATE PROCEDURE sp_reset_otp_invalidate_for_user(IN p_user_id INT)
BEGIN
    UPDATE password_reset_otps
       SET used = 1
     WHERE user_id = p_user_id
       AND used = 0;
END $$

DROP PROCEDURE IF EXISTS sp_reset_otp_create $$
CREATE PROCEDURE sp_reset_otp_create(
    IN  p_user_id    INT,
    IN  p_otp_hash   VARCHAR(255),
    IN  p_expires_at DATETIME,
    OUT p_id         INT
)
BEGIN
    INSERT INTO password_reset_otps (user_id, otp_hash, expires_at)
    VALUES (p_user_id, p_otp_hash, p_expires_at);
    SET p_id = LAST_INSERT_ID();
END $$

-- ---------------------------------------------------------------------
-- sp_reset_otp_get_active -- the newest code for this user that is still
-- unused, unexpired and under the attempt limit. Returns no rows when
-- there is nothing valid, which the caller treats as "cannot verify".
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_reset_otp_get_active $$
CREATE PROCEDURE sp_reset_otp_get_active(IN p_user_id INT, IN p_max_attempts INT)
BEGIN
    SELECT id, user_id, otp_hash, expires_at, attempts, used, created_at
      FROM password_reset_otps
     WHERE user_id = p_user_id
       AND used = 0
       AND expires_at > NOW()
       AND attempts < p_max_attempts
     ORDER BY id DESC
     LIMIT 1;
END $$

DROP PROCEDURE IF EXISTS sp_reset_otp_bump_attempts $$
CREATE PROCEDURE sp_reset_otp_bump_attempts(IN p_id INT)
BEGIN
    UPDATE password_reset_otps
       SET attempts = attempts + 1
     WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS sp_reset_otp_mark_used $$
CREATE PROCEDURE sp_reset_otp_mark_used(IN p_id INT)
BEGIN
    UPDATE password_reset_otps SET used = 1 WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS sp_reset_otp_delete_expired $$
CREATE PROCEDURE sp_reset_otp_delete_expired()
BEGIN
    DELETE FROM password_reset_otps
     WHERE expires_at < NOW() - INTERVAL 1 DAY;
END $$

DELIMITER ;

-- Verification:
--   SHOW COLUMNS FROM password_reset_otps;
--   SELECT ROUTINE_NAME FROM information_schema.ROUTINES
--    WHERE ROUTINE_SCHEMA = 'bjk_athletes' AND ROUTINE_NAME LIKE '%otp%';
