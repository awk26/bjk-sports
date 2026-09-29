-- =====================================================================
--  BJK Athletes -- FULL PRODUCTION SCHEMA (tables + stored procedures)
--
--  Generated from the live application database, so every procedure here
--  matches exactly what common/models.py calls at runtime.
--
--  Contents: 10 tables, 0 views, 63 stored procedures/functions, 0 triggers.
--  No table data is included.
--
--  DEFINER clauses have been stripped, so the routines are created as
--  whoever runs this file -- load it as the account that will own the
--  production schema.
--
--  Usage (creates the database if it doesn't exist):
--    mysql -h <host> -P <port> -u <user> -p < bjk_athletes_full_schema.sql
--
--  SAFE TO RE-RUN, and non-destructive:
--    * tables use CREATE TABLE IF NOT EXISTS -- existing tables and their
--      data are left untouched
--    * procedures are dropped and recreated -- they hold no data, so this
--      just refreshes them to the current version
--
--  Because tables are only created when absent, this file does NOT migrate
--  an older existing schema (it won't add a column to a table that already
--  exists). It is intended for standing up a fresh production database; the
--  app additionally self-heals missing columns at startup via
--  models.ensure_schema_extensions().
-- =====================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------
-- PART 1: database
--
-- The ALTER DATABASE is NOT redundant. "CREATE DATABASE IF NOT EXISTS ...
-- COLLATE ..." silently ignores the COLLATE clause when the database
-- already exists, leaving it on the server default (utf8mb4_0900_ai_ci on
-- MySQL 8). Stored-procedure string parameters permanently inherit the
-- database collation at CREATE time, so a wrong collation here makes every
-- "WHERE varchar_col = p_param" fail at runtime with
--   ERROR 1267: Illegal mix of collations ... for operation '='
-- ALTER DATABASE forces it either way, and must run BEFORE part 3.
-- ---------------------------------------------------------------------
CREATE DATABASE IF NOT EXISTS `bjksports`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER DATABASE `bjksports`
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `bjksports`;

-- ---------------------------------------------------------------------
-- PART 2: tables  (in foreign-key dependency order)
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` int DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `fk_users_created_by` (`created_by`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_archived` (`is_archived`),
  CONSTRAINT `fk_users_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `coaches` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `specialty` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `gender` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dob` date DEFAULT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address_line1` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address_line2` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `postal_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `education` text COLLATE utf8mb4_unicode_ci,
  `certifications` text COLLATE utf8mb4_unicode_ci,
  `additional_info` text COLLATE utf8mb4_unicode_ci,
  `achievements` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `fk_coaches_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `athletes` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `athlete_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `middle_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `last_name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `name` varchar(300) COLLATE utf8mb4_unicode_ci GENERATED ALWAYS AS (trim(concat_ws(_utf8mb4' ',nullif(trim(`first_name`),_utf8mb4''),nullif(trim(`middle_name`),_utf8mb4''),nullif(trim(`last_name`),_utf8mb4'')))) STORED,
  `email` varchar(120) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dob` date DEFAULT NULL,
  `height` decimal(5,2) DEFAULT NULL,
  `weight` decimal(5,2) DEFAULT NULL,
  `parent_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `father_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mother_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address_line1` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `address_line2` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `postal_code` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `physical_params` json DEFAULT NULL,
  `sport` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coach_id` int DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` int DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `gender` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blood_group` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `emergency_contact_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `emergency_contact_phone` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sporting_experience_years` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sport_discipline` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `level_of_participation` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `previous_achievements` text COLLATE utf8mb4_unicode_ci,
  `nationality` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_proof_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `id_proof_number` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `school_name` varchar(150) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `school_grade` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `admission_date` date DEFAULT NULL,
  `medical_notes` text COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  UNIQUE KEY `athlete_code` (`athlete_code`),
  KEY `fk_athletes_created_by` (`created_by`),
  KEY `idx_athletes_coach` (`coach_id`),
  KEY `idx_athletes_archived` (`is_archived`),
  KEY `idx_athletes_sport` (`sport`),
  KEY `fk_athlete_user` (`user_id`),
  CONSTRAINT `fk_athlete_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_athletes_coach` FOREIGN KEY (`coach_id`) REFERENCES `coaches` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_athletes_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `athlete_assessments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `athlete_id` int NOT NULL,
  `coach_id` int NOT NULL,
  `assessment_date` date NOT NULL,
  `status` enum('Draft','Submitted','Under Review','Approved & Published') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'Draft',
  `calculated_age` int DEFAULT NULL,
  `age_group_focus` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `level` enum('Beginner','Intermediate','Advanced') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sessions_planned` int DEFAULT NULL,
  `sessions_attended` int DEFAULT NULL,
  `attendance_pct` decimal(5,2) DEFAULT NULL,
  `attendance_remarks` text COLLATE utf8mb4_unicode_ci,
  `speed_rating` tinyint DEFAULT NULL,
  `speed_remarks` text COLLATE utf8mb4_unicode_ci,
  `agility_rating` tinyint DEFAULT NULL,
  `agility_remarks` text COLLATE utf8mb4_unicode_ci,
  `balance_rating` tinyint DEFAULT NULL,
  `balance_remarks` text COLLATE utf8mb4_unicode_ci,
  `coordination_rating` tinyint DEFAULT NULL,
  `coordination_remarks` text COLLATE utf8mb4_unicode_ci,
  `strength_rating` tinyint DEFAULT NULL,
  `strength_remarks` text COLLATE utf8mb4_unicode_ci,
  `endurance_rating` tinyint DEFAULT NULL,
  `endurance_remarks` text COLLATE utf8mb4_unicode_ci,
  `technique_rating` tinyint DEFAULT NULL,
  `technique_remarks` text COLLATE utf8mb4_unicode_ci,
  `control_accuracy_rating` tinyint DEFAULT NULL,
  `control_accuracy_remarks` text COLLATE utf8mb4_unicode_ci,
  `footwork_rating` tinyint DEFAULT NULL,
  `footwork_remarks` text COLLATE utf8mb4_unicode_ci,
  `game_awareness_rating` tinyint DEFAULT NULL,
  `game_awareness_remarks` text COLLATE utf8mb4_unicode_ci,
  `decision_making_rating` tinyint DEFAULT NULL,
  `decision_making_remarks` text COLLATE utf8mb4_unicode_ci,
  `follow_instructions_rating` tinyint DEFAULT NULL,
  `follow_instructions_remarks` text COLLATE utf8mb4_unicode_ci,
  `discipline_rating` tinyint DEFAULT NULL,
  `discipline_remarks` text COLLATE utf8mb4_unicode_ci,
  `effort_rating` tinyint DEFAULT NULL,
  `effort_remarks` text COLLATE utf8mb4_unicode_ci,
  `coachability_rating` tinyint DEFAULT NULL,
  `coachability_remarks` text COLLATE utf8mb4_unicode_ci,
  `confidence_rating` tinyint DEFAULT NULL,
  `confidence_remarks` text COLLATE utf8mb4_unicode_ci,
  `team_behaviour_rating` tinyint DEFAULT NULL,
  `team_behaviour_remarks` text COLLATE utf8mb4_unicode_ci,
  `talent_category` enum('Recreational','Developing','Potential Talent','High Potential') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `talent_justification` text COLLATE utf8mb4_unicode_ci,
  `strength_1` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `strength_2` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `strength_3` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `improvement_1` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `improvement_2` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `improvement_3` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idp_technical_action` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idp_technical_responsibility` enum('Athlete','Coach','Parent','Shared (Coach/Athlete)','Shared (Parent/Athlete)') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idp_physical_action` text COLLATE utf8mb4_unicode_ci,
  `idp_physical_responsibility` enum('Athlete','Coach','Parent','Shared (Coach/Athlete)','Shared (Parent/Athlete)') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idp_behavioral_action` text COLLATE utf8mb4_unicode_ci,
  `idp_behavioral_responsibility` enum('Athlete','Coach','Parent','Shared (Coach/Athlete)','Shared (Parent/Athlete)') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parent_name` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parent_feedback` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `overall_progress` enum('Excellent','Good','Average','Need Attention') COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coach_summary_remarks` varchar(1000) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_by` int DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `submitted_at` timestamp NULL DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_assessment_athlete` (`athlete_id`),
  KEY `idx_assessment_coach` (`coach_id`),
  KEY `idx_assessment_status` (`status`),
  CONSTRAINT `fk_assessment_athlete` FOREIGN KEY (`athlete_id`) REFERENCES `athletes` (`id`),
  CONSTRAINT `fk_assessment_coach` FOREIGN KEY (`coach_id`) REFERENCES `coaches` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sports` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sports_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `athlete_sports` (
  `athlete_id` int NOT NULL,
  `sport_id` int NOT NULL,
  PRIMARY KEY (`athlete_id`,`sport_id`),
  KEY `fk_athlete_sports_sport` (`sport_id`),
  CONSTRAINT `fk_athlete_sports_athlete` FOREIGN KEY (`athlete_id`) REFERENCES `athletes` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_athlete_sports_sport` FOREIGN KEY (`sport_id`) REFERENCES `sports` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `audit_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `actor_username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `actor_role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `action` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_type` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `target_id` int DEFAULT NULL,
  `details` text COLLATE utf8mb4_unicode_ci,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_audit_actor` (`actor_username`),
  KEY `idx_audit_target` (`target_type`,`target_id`),
  KEY `idx_audit_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `coach_sports` (
  `coach_id` int NOT NULL,
  `sport_id` int NOT NULL,
  PRIMARY KEY (`coach_id`,`sport_id`),
  KEY `fk_coach_sports_sport` (`sport_id`),
  CONSTRAINT `fk_coach_sports_coach` FOREIGN KEY (`coach_id`) REFERENCES `coaches` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_coach_sports_sport` FOREIGN KEY (`sport_id`) REFERENCES `sports` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text COLLATE utf8mb4_unicode_ci,
  `event_date` date NOT NULL,
  `end_date` date DEFAULT NULL,
  `location` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `level` enum('District','State','National','International') COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'District',
  `created_by` int DEFAULT NULL,
  `is_archived` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `fk_events_created_by` (`created_by`),
  CONSTRAINT `fk_events_created_by` FOREIGN KEY (`created_by`) REFERENCES `users` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `password_reset_tokens` (
  `id` int NOT NULL AUTO_INCREMENT,
  `token` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` int NOT NULL,
  `expires_at` datetime NOT NULL,
  `used` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`),
  KEY `fk_reset_user` (`user_id`),
  KEY `idx_reset_expires` (`expires_at`),
  CONSTRAINT `fk_reset_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- PART 2a: normalise collation on tables that already existed
--
-- CREATE TABLE IF NOT EXISTS above does nothing for a table that is
-- already there, so a table left on another collation would keep it.
-- These CONVERT statements are what actually repair such a database.
-- Harmless (no-op) when the table is already on the target collation.
-- ---------------------------------------------------------------------
ALTER TABLE `users` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `coaches` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `athletes` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `athlete_assessments` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `sports` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `athlete_sports` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `audit_log` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `coach_sports` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `events` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE `password_reset_tokens` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------
-- PART 3: stored procedures & functions
-- ---------------------------------------------------------------------
DELIMITER $$

DROP PROCEDURE IF EXISTS `sp_analytics_athlete_category_trend` $$
CREATE PROCEDURE `sp_analytics_athlete_category_trend`(IN p_athlete_id INT, IN p_coach_id INT)
BEGIN
    SELECT
        assessment_date,
        (speed_rating + agility_rating + balance_rating + coordination_rating +
         strength_rating + endurance_rating) / 6.0                    AS avg_physical,
        (technique_rating + control_accuracy_rating + footwork_rating) / 3.0
                                                                        AS avg_technical,
        (game_awareness_rating + decision_making_rating +
         follow_instructions_rating) / 3.0                            AS avg_tactical,
        (discipline_rating + effort_rating + coachability_rating +
         confidence_rating + team_behaviour_rating) / 5.0             AS avg_behavioral
    FROM athlete_assessments
    WHERE athlete_id = p_athlete_id AND coach_id = p_coach_id
          AND status <> 'Draft' AND is_archived = 0
    ORDER BY assessment_date ASC, id ASC;
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_athlete_kpis` $$
CREATE PROCEDURE `sp_analytics_athlete_kpis`(IN p_athlete_id INT, IN p_coach_id INT)
BEGIN
    SELECT
        COUNT(*)                                                     AS total_assessments,
        SUM(status <> 'Draft')                                       AS finalized_count,
        SUM(status = 'Draft')                                        AS draft_count,
        AVG(attendance_pct)                                          AS avg_attendance_pct,
        AVG(
            CASE WHEN status <> 'Draft' THEN
                (speed_rating + agility_rating + balance_rating + coordination_rating +
                 strength_rating + endurance_rating + technique_rating + control_accuracy_rating +
                 footwork_rating + game_awareness_rating + decision_making_rating +
                 follow_instructions_rating + discipline_rating + effort_rating +
                 coachability_rating + confidence_rating + team_behaviour_rating) / 17.0
            ELSE NULL END
        )                                                             AS avg_overall_rating
    FROM athlete_assessments
    WHERE athlete_id = p_athlete_id AND coach_id = p_coach_id AND is_archived = 0;
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_athlete_latest` $$
CREATE PROCEDURE `sp_analytics_athlete_latest`(IN p_athlete_id INT, IN p_coach_id INT)
BEGIN
    SELECT
        assessment_date, talent_category, overall_progress, level,
        (speed_rating + agility_rating + balance_rating + coordination_rating +
         strength_rating + endurance_rating) / 6.0                    AS avg_physical,
        (technique_rating + control_accuracy_rating + footwork_rating) / 3.0
                                                                        AS avg_technical,
        (game_awareness_rating + decision_making_rating +
         follow_instructions_rating) / 3.0                            AS avg_tactical,
        (discipline_rating + effort_rating + coachability_rating +
         confidence_rating + team_behaviour_rating) / 5.0             AS avg_behavioral
    FROM athlete_assessments
    WHERE athlete_id = p_athlete_id AND coach_id = p_coach_id
          AND status <> 'Draft' AND is_archived = 0
    ORDER BY assessment_date DESC, id DESC
    LIMIT 1;
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_athlete_trend` $$
CREATE PROCEDURE `sp_analytics_athlete_trend`(IN p_athlete_id INT, IN p_coach_id INT)
BEGIN
    SELECT
        assessment_date,
        attendance_pct,
        (speed_rating + agility_rating + balance_rating + coordination_rating +
         strength_rating + endurance_rating + technique_rating + control_accuracy_rating +
         footwork_rating + game_awareness_rating + decision_making_rating +
         follow_instructions_rating + discipline_rating + effort_rating +
         coachability_rating + confidence_rating + team_behaviour_rating) / 17.0
                                                                        AS overall_rating,
        talent_category, overall_progress
    FROM athlete_assessments
    WHERE athlete_id = p_athlete_id AND coach_id = p_coach_id
          AND status <> 'Draft' AND is_archived = 0
    ORDER BY assessment_date ASC, id ASC;
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_category_averages` $$
CREATE PROCEDURE `sp_analytics_category_averages`(
    IN p_coach_id INT, IN p_athlete_id INT, IN p_sport VARCHAR(100),
    IN p_date_from DATE, IN p_date_to DATE
)
BEGIN
    SELECT
        AVG((aa.speed_rating + aa.agility_rating + aa.balance_rating + aa.coordination_rating +
             aa.strength_rating + aa.endurance_rating) / 6.0)         AS avg_physical,
        AVG((aa.technique_rating + aa.control_accuracy_rating + aa.footwork_rating) / 3.0)
                                                                        AS avg_technical,
        AVG((aa.game_awareness_rating + aa.decision_making_rating +
             aa.follow_instructions_rating) / 3.0)                    AS avg_tactical,
        AVG((aa.discipline_rating + aa.effort_rating + aa.coachability_rating +
             aa.confidence_rating + aa.team_behaviour_rating) / 5.0)  AS avg_behavioral
    FROM athlete_assessments aa
    JOIN athletes a ON a.id = aa.athlete_id
    WHERE aa.coach_id = p_coach_id AND aa.status <> 'Draft' AND aa.is_archived = 0
          AND (p_athlete_id IS NULL OR aa.athlete_id = p_athlete_id)
          AND (p_sport IS NULL OR a.sport = p_sport)
          AND (p_date_from IS NULL OR aa.assessment_date >= p_date_from)
          AND (p_date_to IS NULL OR aa.assessment_date <= p_date_to);
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_kpis` $$
CREATE PROCEDURE `sp_analytics_kpis`(
    IN p_coach_id INT, IN p_athlete_id INT, IN p_sport VARCHAR(100),
    IN p_date_from DATE, IN p_date_to DATE
)
BEGIN
    SELECT
        COUNT(DISTINCT aa.athlete_id)                                AS athlete_count,
        COUNT(*)                                                     AS total_assessments,
        SUM(aa.status <> 'Draft')                                    AS finalized_count,
        SUM(aa.status = 'Draft')                                     AS draft_count,
        AVG(aa.attendance_pct)                                       AS avg_attendance_pct,
        AVG(
            CASE WHEN aa.status <> 'Draft' THEN
                (aa.speed_rating + aa.agility_rating + aa.balance_rating + aa.coordination_rating +
                 aa.strength_rating + aa.endurance_rating + aa.technique_rating + aa.control_accuracy_rating +
                 aa.footwork_rating + aa.game_awareness_rating + aa.decision_making_rating +
                 aa.follow_instructions_rating + aa.discipline_rating + aa.effort_rating +
                 aa.coachability_rating + aa.confidence_rating + aa.team_behaviour_rating) / 17.0
            ELSE NULL END
        )                                                             AS avg_overall_rating
    FROM athlete_assessments aa
    JOIN athletes a ON a.id = aa.athlete_id
    WHERE aa.coach_id = p_coach_id AND aa.is_archived = 0
          AND (p_athlete_id IS NULL OR aa.athlete_id = p_athlete_id)
          AND (p_sport IS NULL OR a.sport = p_sport)
          AND (p_date_from IS NULL OR aa.assessment_date >= p_date_from)
          AND (p_date_to IS NULL OR aa.assessment_date <= p_date_to);
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_monthly_trend` $$
CREATE PROCEDURE `sp_analytics_monthly_trend`(
    IN p_coach_id INT, IN p_athlete_id INT, IN p_sport VARCHAR(100),
    IN p_date_from DATE, IN p_date_to DATE
)
BEGIN
    SELECT
        DATE_FORMAT(aa.assessment_date, '%Y-%m')                      AS month,
        AVG(aa.attendance_pct)                                        AS avg_attendance_pct,
        AVG((aa.speed_rating + aa.agility_rating + aa.balance_rating + aa.coordination_rating +
             aa.strength_rating + aa.endurance_rating + aa.technique_rating + aa.control_accuracy_rating +
             aa.footwork_rating + aa.game_awareness_rating + aa.decision_making_rating +
             aa.follow_instructions_rating + aa.discipline_rating + aa.effort_rating +
             aa.coachability_rating + aa.confidence_rating + aa.team_behaviour_rating) / 17.0)
                                                                        AS avg_overall_rating,
        COUNT(*)                                                       AS assessment_count
    FROM athlete_assessments aa
    JOIN athletes a ON a.id = aa.athlete_id
    WHERE aa.coach_id = p_coach_id AND aa.status <> 'Draft' AND aa.is_archived = 0
          AND (p_athlete_id IS NULL OR aa.athlete_id = p_athlete_id)
          AND (p_sport IS NULL OR a.sport = p_sport)
          AND (p_date_from IS NULL OR aa.assessment_date >= p_date_from)
          AND (p_date_to IS NULL OR aa.assessment_date <= p_date_to)
    GROUP BY DATE_FORMAT(aa.assessment_date, '%Y-%m')
    ORDER BY month;
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_progress_distribution` $$
CREATE PROCEDURE `sp_analytics_progress_distribution`(
    IN p_coach_id INT, IN p_athlete_id INT, IN p_sport VARCHAR(100),
    IN p_date_from DATE, IN p_date_to DATE
)
BEGIN
    SELECT aa.overall_progress, COUNT(*) AS cnt
    FROM athlete_assessments aa
    JOIN athletes a ON a.id = aa.athlete_id
    WHERE aa.coach_id = p_coach_id AND aa.status <> 'Draft' AND aa.is_archived = 0
          AND aa.overall_progress IS NOT NULL
          AND (p_athlete_id IS NULL OR aa.athlete_id = p_athlete_id)
          AND (p_sport IS NULL OR a.sport = p_sport)
          AND (p_date_from IS NULL OR aa.assessment_date >= p_date_from)
          AND (p_date_to IS NULL OR aa.assessment_date <= p_date_to)
    GROUP BY aa.overall_progress;
END $$

DROP PROCEDURE IF EXISTS `sp_analytics_talent_distribution` $$
CREATE PROCEDURE `sp_analytics_talent_distribution`(
    IN p_coach_id INT, IN p_athlete_id INT, IN p_sport VARCHAR(100),
    IN p_date_from DATE, IN p_date_to DATE
)
BEGIN
    SELECT aa.talent_category, COUNT(*) AS cnt
    FROM athlete_assessments aa
    JOIN athletes a ON a.id = aa.athlete_id
    WHERE aa.coach_id = p_coach_id AND aa.status <> 'Draft' AND aa.is_archived = 0
          AND aa.talent_category IS NOT NULL
          AND (p_athlete_id IS NULL OR aa.athlete_id = p_athlete_id)
          AND (p_sport IS NULL OR a.sport = p_sport)
          AND (p_date_from IS NULL OR aa.assessment_date >= p_date_from)
          AND (p_date_to IS NULL OR aa.assessment_date <= p_date_to)
    GROUP BY aa.talent_category;
END $$

DROP PROCEDURE IF EXISTS `sp_assessment_archive` $$
CREATE PROCEDURE `sp_assessment_archive`(IN p_id INT, IN p_is_archived TINYINT)
BEGIN
    UPDATE athlete_assessments SET is_archived = p_is_archived WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_assessment_create` $$
CREATE PROCEDURE `sp_assessment_create`(
    IN p_athlete_id INT,
    IN p_coach_id INT,
    IN p_assessment_date DATE,
    IN p_status VARCHAR(30),
    IN p_calculated_age INT,
    IN p_age_group_focus VARCHAR(50),
    IN p_level VARCHAR(20),
    IN p_sessions_planned INT,
    IN p_sessions_attended INT,
    IN p_attendance_pct DECIMAL(5,2),
    IN p_attendance_remarks TEXT,
    IN p_speed_rating TINYINT, IN p_speed_remarks TEXT,
    IN p_agility_rating TINYINT, IN p_agility_remarks TEXT,
    IN p_balance_rating TINYINT, IN p_balance_remarks TEXT,
    IN p_coordination_rating TINYINT, IN p_coordination_remarks TEXT,
    IN p_strength_rating TINYINT, IN p_strength_remarks TEXT,
    IN p_endurance_rating TINYINT, IN p_endurance_remarks TEXT,
    IN p_technique_rating TINYINT, IN p_technique_remarks TEXT,
    IN p_control_accuracy_rating TINYINT, IN p_control_accuracy_remarks TEXT,
    IN p_footwork_rating TINYINT, IN p_footwork_remarks TEXT,
    IN p_game_awareness_rating TINYINT, IN p_game_awareness_remarks TEXT,
    IN p_decision_making_rating TINYINT, IN p_decision_making_remarks TEXT,
    IN p_follow_instructions_rating TINYINT, IN p_follow_instructions_remarks TEXT,
    IN p_discipline_rating TINYINT, IN p_discipline_remarks TEXT,
    IN p_effort_rating TINYINT, IN p_effort_remarks TEXT,
    IN p_coachability_rating TINYINT, IN p_coachability_remarks TEXT,
    IN p_confidence_rating TINYINT, IN p_confidence_remarks TEXT,
    IN p_team_behaviour_rating TINYINT, IN p_team_behaviour_remarks TEXT,
    IN p_talent_category VARCHAR(30),
    IN p_talent_justification TEXT,
    IN p_strength_1 VARCHAR(500), IN p_strength_2 VARCHAR(500), IN p_strength_3 VARCHAR(500),
    IN p_improvement_1 VARCHAR(500), IN p_improvement_2 VARCHAR(500), IN p_improvement_3 VARCHAR(500),
    IN p_idp_technical_action VARCHAR(500), IN p_idp_technical_responsibility VARCHAR(30),
    IN p_idp_physical_action TEXT, IN p_idp_physical_responsibility VARCHAR(30),
    IN p_idp_behavioral_action TEXT, IN p_idp_behavioral_responsibility VARCHAR(30),
    IN p_parent_name VARCHAR(100),
    IN p_parent_feedback VARCHAR(1000),
    IN p_overall_progress VARCHAR(30),
    IN p_coach_summary_remarks VARCHAR(1000),
    IN p_created_by INT,
    OUT p_new_id INT
)
BEGIN
    INSERT INTO athlete_assessments (
        athlete_id, coach_id, assessment_date, status,
        calculated_age, age_group_focus, level,
        sessions_planned, sessions_attended, attendance_pct, attendance_remarks,
        speed_rating, speed_remarks, agility_rating, agility_remarks,
        balance_rating, balance_remarks, coordination_rating, coordination_remarks,
        strength_rating, strength_remarks, endurance_rating, endurance_remarks,
        technique_rating, technique_remarks, control_accuracy_rating, control_accuracy_remarks,
        footwork_rating, footwork_remarks,
        game_awareness_rating, game_awareness_remarks, decision_making_rating, decision_making_remarks,
        follow_instructions_rating, follow_instructions_remarks,
        discipline_rating, discipline_remarks, effort_rating, effort_remarks,
        coachability_rating, coachability_remarks, confidence_rating, confidence_remarks,
        team_behaviour_rating, team_behaviour_remarks,
        talent_category, talent_justification,
        strength_1, strength_2, strength_3,
        improvement_1, improvement_2, improvement_3,
        idp_technical_action, idp_technical_responsibility,
        idp_physical_action, idp_physical_responsibility,
        idp_behavioral_action, idp_behavioral_responsibility,
        parent_name, parent_feedback,
        overall_progress, coach_summary_remarks,
        created_by, submitted_at
    ) VALUES (
        p_athlete_id, p_coach_id, p_assessment_date, p_status,
        p_calculated_age, p_age_group_focus, p_level,
        p_sessions_planned, p_sessions_attended, p_attendance_pct, p_attendance_remarks,
        p_speed_rating, p_speed_remarks, p_agility_rating, p_agility_remarks,
        p_balance_rating, p_balance_remarks, p_coordination_rating, p_coordination_remarks,
        p_strength_rating, p_strength_remarks, p_endurance_rating, p_endurance_remarks,
        p_technique_rating, p_technique_remarks, p_control_accuracy_rating, p_control_accuracy_remarks,
        p_footwork_rating, p_footwork_remarks,
        p_game_awareness_rating, p_game_awareness_remarks, p_decision_making_rating, p_decision_making_remarks,
        p_follow_instructions_rating, p_follow_instructions_remarks,
        p_discipline_rating, p_discipline_remarks, p_effort_rating, p_effort_remarks,
        p_coachability_rating, p_coachability_remarks, p_confidence_rating, p_confidence_remarks,
        p_team_behaviour_rating, p_team_behaviour_remarks,
        p_talent_category, p_talent_justification,
        p_strength_1, p_strength_2, p_strength_3,
        p_improvement_1, p_improvement_2, p_improvement_3,
        p_idp_technical_action, p_idp_technical_responsibility,
        p_idp_physical_action, p_idp_physical_responsibility,
        p_idp_behavioral_action, p_idp_behavioral_responsibility,
        p_parent_name, p_parent_feedback,
        p_overall_progress, p_coach_summary_remarks,
        p_created_by, IF(p_status = 'Submitted', NOW(), NULL)
    );
    SET p_new_id = LAST_INSERT_ID();
END $$

DROP PROCEDURE IF EXISTS `sp_assessment_delete` $$
CREATE PROCEDURE `sp_assessment_delete`(IN p_id INT)
BEGIN
    DELETE FROM athlete_assessments WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_assessment_get_by_id` $$
CREATE PROCEDURE `sp_assessment_get_by_id`(IN p_id INT)
BEGIN
    SELECT a.*, ath.name AS athlete_name, ath.dob AS athlete_dob, ath.sport AS athlete_sport,
           u.name AS coach_name
    FROM athlete_assessments a
    JOIN athletes ath ON ath.id = a.athlete_id
    JOIN coaches c ON c.id = a.coach_id
    JOIN users u ON u.id = c.user_id
    WHERE a.id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_assessment_list` $$
CREATE PROCEDURE `sp_assessment_list`(
    IN p_athlete_id INT,
    IN p_coach_id INT,
    IN p_status VARCHAR(30),
    IN p_is_archived TINYINT
)
BEGIN
    SELECT a.id, a.athlete_id, a.coach_id, a.assessment_date, a.status,
           a.overall_progress, a.talent_category, a.is_archived,
           a.created_at, a.updated_at, a.submitted_at,
           ath.name AS athlete_name
    FROM athlete_assessments a
    JOIN athletes ath ON ath.id = a.athlete_id
    WHERE (p_athlete_id IS NULL OR a.athlete_id = p_athlete_id)
      AND (p_coach_id IS NULL OR a.coach_id = p_coach_id)
      AND (p_status IS NULL OR a.status = p_status)
      AND (p_is_archived IS NULL OR a.is_archived = p_is_archived)
    ORDER BY a.assessment_date DESC, a.id DESC;
END $$

DROP PROCEDURE IF EXISTS `sp_assessment_update` $$
CREATE PROCEDURE `sp_assessment_update`(
    IN p_id INT,
    IN p_status VARCHAR(30),
    IN p_calculated_age INT,
    IN p_age_group_focus VARCHAR(50),
    IN p_level VARCHAR(20),
    IN p_sessions_planned INT,
    IN p_sessions_attended INT,
    IN p_attendance_pct DECIMAL(5,2),
    IN p_attendance_remarks TEXT,
    IN p_speed_rating TINYINT, IN p_speed_remarks TEXT,
    IN p_agility_rating TINYINT, IN p_agility_remarks TEXT,
    IN p_balance_rating TINYINT, IN p_balance_remarks TEXT,
    IN p_coordination_rating TINYINT, IN p_coordination_remarks TEXT,
    IN p_strength_rating TINYINT, IN p_strength_remarks TEXT,
    IN p_endurance_rating TINYINT, IN p_endurance_remarks TEXT,
    IN p_technique_rating TINYINT, IN p_technique_remarks TEXT,
    IN p_control_accuracy_rating TINYINT, IN p_control_accuracy_remarks TEXT,
    IN p_footwork_rating TINYINT, IN p_footwork_remarks TEXT,
    IN p_game_awareness_rating TINYINT, IN p_game_awareness_remarks TEXT,
    IN p_decision_making_rating TINYINT, IN p_decision_making_remarks TEXT,
    IN p_follow_instructions_rating TINYINT, IN p_follow_instructions_remarks TEXT,
    IN p_discipline_rating TINYINT, IN p_discipline_remarks TEXT,
    IN p_effort_rating TINYINT, IN p_effort_remarks TEXT,
    IN p_coachability_rating TINYINT, IN p_coachability_remarks TEXT,
    IN p_confidence_rating TINYINT, IN p_confidence_remarks TEXT,
    IN p_team_behaviour_rating TINYINT, IN p_team_behaviour_remarks TEXT,
    IN p_talent_category VARCHAR(30),
    IN p_talent_justification TEXT,
    IN p_strength_1 VARCHAR(500), IN p_strength_2 VARCHAR(500), IN p_strength_3 VARCHAR(500),
    IN p_improvement_1 VARCHAR(500), IN p_improvement_2 VARCHAR(500), IN p_improvement_3 VARCHAR(500),
    IN p_idp_technical_action VARCHAR(500), IN p_idp_technical_responsibility VARCHAR(30),
    IN p_idp_physical_action TEXT, IN p_idp_physical_responsibility VARCHAR(30),
    IN p_idp_behavioral_action TEXT, IN p_idp_behavioral_responsibility VARCHAR(30),
    IN p_parent_name VARCHAR(100),
    IN p_parent_feedback VARCHAR(1000),
    IN p_overall_progress VARCHAR(30),
    IN p_coach_summary_remarks VARCHAR(1000)
)
BEGIN
    UPDATE athlete_assessments SET
        status = p_status,
        calculated_age = p_calculated_age, age_group_focus = p_age_group_focus, level = p_level,
        sessions_planned = p_sessions_planned, sessions_attended = p_sessions_attended,
        attendance_pct = p_attendance_pct, attendance_remarks = p_attendance_remarks,
        speed_rating = p_speed_rating, speed_remarks = p_speed_remarks,
        agility_rating = p_agility_rating, agility_remarks = p_agility_remarks,
        balance_rating = p_balance_rating, balance_remarks = p_balance_remarks,
        coordination_rating = p_coordination_rating, coordination_remarks = p_coordination_remarks,
        strength_rating = p_strength_rating, strength_remarks = p_strength_remarks,
        endurance_rating = p_endurance_rating, endurance_remarks = p_endurance_remarks,
        technique_rating = p_technique_rating, technique_remarks = p_technique_remarks,
        control_accuracy_rating = p_control_accuracy_rating, control_accuracy_remarks = p_control_accuracy_remarks,
        footwork_rating = p_footwork_rating, footwork_remarks = p_footwork_remarks,
        game_awareness_rating = p_game_awareness_rating, game_awareness_remarks = p_game_awareness_remarks,
        decision_making_rating = p_decision_making_rating, decision_making_remarks = p_decision_making_remarks,
        follow_instructions_rating = p_follow_instructions_rating, follow_instructions_remarks = p_follow_instructions_remarks,
        discipline_rating = p_discipline_rating, discipline_remarks = p_discipline_remarks,
        effort_rating = p_effort_rating, effort_remarks = p_effort_remarks,
        coachability_rating = p_coachability_rating, coachability_remarks = p_coachability_remarks,
        confidence_rating = p_confidence_rating, confidence_remarks = p_confidence_remarks,
        team_behaviour_rating = p_team_behaviour_rating, team_behaviour_remarks = p_team_behaviour_remarks,
        talent_category = p_talent_category, talent_justification = p_talent_justification,
        strength_1 = p_strength_1, strength_2 = p_strength_2, strength_3 = p_strength_3,
        improvement_1 = p_improvement_1, improvement_2 = p_improvement_2, improvement_3 = p_improvement_3,
        idp_technical_action = p_idp_technical_action, idp_technical_responsibility = p_idp_technical_responsibility,
        idp_physical_action = p_idp_physical_action, idp_physical_responsibility = p_idp_physical_responsibility,
        idp_behavioral_action = p_idp_behavioral_action, idp_behavioral_responsibility = p_idp_behavioral_responsibility,
        parent_name = p_parent_name, parent_feedback = p_parent_feedback,
        overall_progress = p_overall_progress, coach_summary_remarks = p_coach_summary_remarks,
        submitted_at = IF(p_status = 'Submitted' AND submitted_at IS NULL, NOW(), submitted_at)
    WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_archive` $$
CREATE PROCEDURE `sp_athlete_archive`(
    IN p_id INT,
    IN p_is_archived BOOLEAN
)
BEGIN
    UPDATE athletes SET is_archived = p_is_archived WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_create` $$
CREATE PROCEDURE `sp_athlete_create`(
    IN  p_code            VARCHAR(255),
    IN  p_first_name      VARCHAR(100),
    IN  p_middle_name     VARCHAR(100),
    IN  p_last_name       VARCHAR(100),
    IN  p_email           VARCHAR(255),
    IN  p_phone           VARCHAR(255),
    IN  p_dob             DATE,
    IN  p_sport           VARCHAR(255),
    IN  p_coach_id        INT,
    IN  p_created_by      INT,
    IN  p_user_id         INT,
    IN  p_height          DECIMAL(5,2),
    IN  p_weight          DECIMAL(5,2),
    IN  p_parent_name     VARCHAR(255),
    IN  p_father_name     VARCHAR(255),
    IN  p_mother_name     VARCHAR(255),
    IN  p_address_line1   VARCHAR(255),
    IN  p_address_line2   VARCHAR(255),
    IN  p_city            VARCHAR(100),
    IN  p_state           VARCHAR(100),
    IN  p_postal_code     VARCHAR(20),
    IN  p_physical_params JSON,
    OUT p_id              INT
)
BEGIN
    INSERT INTO athletes
        (athlete_code, first_name, middle_name, last_name,
         email, phone, dob, sport, coach_id, created_by, user_id,
         height, weight, parent_name, father_name, mother_name,
         address_line1, address_line2, city, state, postal_code, physical_params)
    VALUES
        (p_code, p_first_name, p_middle_name, p_last_name,
         p_email, p_phone, p_dob, p_sport, p_coach_id, p_created_by, p_user_id,
         p_height, p_weight, p_parent_name, p_father_name, p_mother_name,
         p_address_line1, p_address_line2, p_city, p_state, p_postal_code, p_physical_params);
    SET p_id = LAST_INSERT_ID();
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_delete` $$
CREATE PROCEDURE `sp_athlete_delete`(IN p_id INT)
BEGIN
    DELETE FROM athletes WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_get_by_id` $$
CREATE PROCEDURE `sp_athlete_get_by_id`(IN p_id INT)
BEGIN
    SELECT a.*, u.name AS coach_name
      FROM athletes a
      LEFT JOIN coaches c ON c.id = a.coach_id
      LEFT JOIN users u ON u.id = c.user_id
     WHERE a.id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_get_by_user_id` $$
CREATE PROCEDURE `sp_athlete_get_by_user_id`(IN p_user_id INT)
BEGIN
    SELECT * FROM athletes WHERE user_id = p_user_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_link_user` $$
CREATE PROCEDURE `sp_athlete_link_user`(IN p_athlete_id INT, IN p_user_id INT)
BEGIN
    UPDATE athletes SET user_id = p_user_id WHERE id = p_athlete_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_list` $$
CREATE PROCEDURE `sp_athlete_list`(
    IN p_coach_id INT,
    IN p_is_archived TINYINT,
    IN p_sport VARCHAR(100),
    IN p_search VARCHAR(150)
)
BEGIN
    SELECT a.*, u.name AS coach_name
      FROM athletes a
      LEFT JOIN coaches c ON c.id = a.coach_id
      LEFT JOIN users u ON u.id = c.user_id
     WHERE (p_coach_id IS NULL OR a.coach_id = p_coach_id)
       AND (p_is_archived IS NULL OR a.is_archived = p_is_archived)
       AND (p_sport IS NULL OR a.sport = p_sport)
       AND (p_search IS NULL
            OR a.name LIKE CONCAT('%', p_search, '%')
            OR a.athlete_code LIKE CONCAT('%', p_search, '%'))
     ORDER BY a.created_at DESC;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_login_info` $$
CREATE PROCEDURE `sp_athlete_login_info`(IN p_athlete_id INT)
BEGIN
    SELECT a.id AS athlete_id, a.user_id, u.username
    FROM athletes a
    LEFT JOIN users u ON u.id = a.user_id
    WHERE a.id = p_athlete_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_sports_add` $$
CREATE PROCEDURE `sp_athlete_sports_add`(IN p_athlete_id INT, IN p_sport_id INT)
BEGIN
    INSERT IGNORE INTO athlete_sports (athlete_id, sport_id) VALUES (p_athlete_id, p_sport_id);
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_sports_clear` $$
CREATE PROCEDURE `sp_athlete_sports_clear`(IN p_athlete_id INT)
BEGIN
    DELETE FROM athlete_sports WHERE athlete_id = p_athlete_id;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_sports_get` $$
CREATE PROCEDURE `sp_athlete_sports_get`(IN p_athlete_id INT)
BEGIN
    SELECT s.id, s.name
    FROM athlete_sports asp
    JOIN sports s ON s.id = asp.sport_id
    WHERE asp.athlete_id = p_athlete_id
    ORDER BY s.name;
END $$

DROP PROCEDURE IF EXISTS `sp_athlete_update` $$
CREATE PROCEDURE `sp_athlete_update`(
    IN p_id             INT,
    IN p_first_name     VARCHAR(100),
    IN p_middle_name    VARCHAR(100),
    IN p_last_name      VARCHAR(100),
    IN p_email          VARCHAR(255),
    IN p_phone          VARCHAR(255),
    IN p_dob            DATE,
    IN p_sport          VARCHAR(255),
    IN p_coach_id       INT,
    IN p_height         DECIMAL(5,2),
    IN p_weight         DECIMAL(5,2),
    IN p_parent_name    VARCHAR(255),
    IN p_father_name    VARCHAR(255),
    IN p_mother_name    VARCHAR(255),
    IN p_address_line1  VARCHAR(255),
    IN p_address_line2  VARCHAR(255),
    IN p_city           VARCHAR(100),
    IN p_state          VARCHAR(100),
    IN p_postal_code    VARCHAR(20),
    IN p_physical_params JSON
)
BEGIN
    UPDATE athletes
    SET first_name    = p_first_name,
        middle_name   = p_middle_name,
        last_name     = p_last_name,
        email         = p_email,
        phone         = p_phone,
        dob           = p_dob,
        sport         = p_sport,
        coach_id      = p_coach_id,
        height        = p_height,
        weight        = p_weight,
        parent_name   = p_parent_name,
        father_name   = p_father_name,
        mother_name   = p_mother_name,
        address_line1 = p_address_line1,
        address_line2 = p_address_line2,
        city          = p_city,
        state         = p_state,
        postal_code   = p_postal_code,
        physical_params = p_physical_params
    WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_audit_log_insert` $$
CREATE PROCEDURE `sp_audit_log_insert`(
    IN p_actor_username VARCHAR(50),
    IN p_actor_role VARCHAR(20),
    IN p_action VARCHAR(50),
    IN p_target_type VARCHAR(20),
    IN p_target_id INT,
    IN p_details TEXT
)
BEGIN
    INSERT INTO audit_log (actor_username, actor_role, action, target_type, target_id, details)
    VALUES (p_actor_username, p_actor_role, p_action, p_target_type, p_target_id, p_details);
END $$

DROP PROCEDURE IF EXISTS `sp_audit_log_list` $$
CREATE PROCEDURE `sp_audit_log_list`(
    IN p_target_type VARCHAR(20),
    IN p_target_id INT,
    IN p_limit INT
)
BEGIN
    SELECT * FROM audit_log
     WHERE (p_target_type IS NULL OR target_type = p_target_type)
       AND (p_target_id IS NULL OR target_id = p_target_id)
     ORDER BY created_at DESC
     LIMIT p_limit;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_archive` $$
CREATE PROCEDURE `sp_coach_archive`(
    IN p_id INT,
    IN p_is_archived BOOLEAN
)
BEGIN
    UPDATE coaches SET is_archived = p_is_archived WHERE id = p_id;
    UPDATE users u
      JOIN coaches c ON c.user_id = u.id
       SET u.is_archived = p_is_archived
     WHERE c.id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_create` $$
CREATE PROCEDURE `sp_coach_create`(
    IN p_user_id INT,
    IN p_specialty VARCHAR(100),
    OUT p_coach_id INT
)
BEGIN
    INSERT INTO coaches (user_id, specialty) VALUES (p_user_id, p_specialty);
    SET p_coach_id = LAST_INSERT_ID();
END $$

DROP PROCEDURE IF EXISTS `sp_coach_dashboard_sport_breakdown` $$
CREATE PROCEDURE `sp_coach_dashboard_sport_breakdown`(IN p_coach_id INT)
BEGIN
    SELECT
        COALESCE(NULLIF(a.sport, ''), 'Unspecified')                          AS sport,
        COUNT(DISTINCT a.id)                                                  AS athlete_count,
        COALESCE(SUM(aa.sessions_planned), 0)                                 AS sessions_planned,
        COALESCE(SUM(aa.sessions_attended), 0)                                AS sessions_attended
    FROM athletes a
    LEFT JOIN athlete_assessments aa
           ON aa.athlete_id = a.id AND aa.is_archived = 0
    WHERE a.coach_id = p_coach_id AND a.is_archived = 0
    GROUP BY COALESCE(NULLIF(a.sport, ''), 'Unspecified')
    ORDER BY athlete_count DESC;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_dashboard_stats` $$
CREATE PROCEDURE `sp_coach_dashboard_stats`(IN p_coach_id INT)
BEGIN
    SELECT
        (SELECT COUNT(*)
           FROM athletes
          WHERE coach_id = p_coach_id AND is_archived = 0)                    AS athlete_count,
        (SELECT COUNT(DISTINCT sport)
           FROM athletes
          WHERE coach_id = p_coach_id AND is_archived = 0
                AND sport IS NOT NULL AND sport <> '')                        AS sport_count,
        (SELECT COALESCE(SUM(sessions_planned), 0)
           FROM athlete_assessments
          WHERE coach_id = p_coach_id AND is_archived = 0)                    AS sessions_planned_total,
        (SELECT COALESCE(SUM(sessions_attended), 0)
           FROM athlete_assessments
          WHERE coach_id = p_coach_id AND is_archived = 0)                    AS sessions_attended_total;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_get_by_id` $$
CREATE PROCEDURE `sp_coach_get_by_id`(IN p_id INT)
BEGIN
    SELECT c.*, u.username, u.name, u.email, u.is_archived AS user_is_archived
      FROM coaches c
      JOIN users u ON u.id = c.user_id
     WHERE c.id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_get_by_user_id` $$
CREATE PROCEDURE `sp_coach_get_by_user_id`(IN p_user_id INT)
BEGIN
    SELECT * FROM coaches WHERE user_id = p_user_id;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_list` $$
CREATE PROCEDURE `sp_coach_list`(IN p_is_archived TINYINT)
BEGIN
    SELECT c.*, u.username, u.name, u.email
      FROM coaches c
      JOIN users u ON u.id = c.user_id
     WHERE (p_is_archived IS NULL OR c.is_archived = p_is_archived)
     ORDER BY u.name;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_sports_add` $$
CREATE PROCEDURE `sp_coach_sports_add`(IN p_coach_id INT, IN p_sport_id INT)
BEGIN
    INSERT IGNORE INTO coach_sports (coach_id, sport_id) VALUES (p_coach_id, p_sport_id);
END $$

DROP PROCEDURE IF EXISTS `sp_coach_sports_clear` $$
CREATE PROCEDURE `sp_coach_sports_clear`(IN p_coach_id INT)
BEGIN
    DELETE FROM coach_sports WHERE coach_id = p_coach_id;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_sports_get` $$
CREATE PROCEDURE `sp_coach_sports_get`(IN p_coach_id INT)
BEGIN
    SELECT s.id, s.name
    FROM coach_sports cs
    JOIN sports s ON s.id = cs.sport_id
    WHERE cs.coach_id = p_coach_id
    ORDER BY s.name;
END $$

DROP PROCEDURE IF EXISTS `sp_coach_update` $$
CREATE PROCEDURE `sp_coach_update`(
    IN p_id INT,
    IN p_specialty VARCHAR(100)
)
BEGIN
    UPDATE coaches SET specialty = p_specialty WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_org_dashboard_age_distribution` $$
CREATE PROCEDURE `sp_org_dashboard_age_distribution`()
BEGIN
    SELECT
        CASE
            WHEN age IS NULL THEN 'Unknown'
            WHEN age <= 9 THEN 'Under 10'
            WHEN age BETWEEN 10 AND 13 THEN '10-13'
            WHEN age BETWEEN 14 AND 17 THEN '14-17'
            ELSE '18+'
        END AS age_group,
        COUNT(*) AS athlete_count
    FROM (
        SELECT TIMESTAMPDIFF(YEAR, dob, CURDATE()) AS age
        FROM athletes
        WHERE is_archived = 0
    ) ages
    GROUP BY age_group
    ORDER BY FIELD(age_group, 'Under 10', '10-13', '14-17', '18+', 'Unknown');
END $$

DROP PROCEDURE IF EXISTS `sp_org_dashboard_top_athletes` $$
CREATE PROCEDURE `sp_org_dashboard_top_athletes`(IN p_limit INT)
BEGIN
    SELECT athlete_id, athlete_name, sport, coach_name, avg_rating, attendance_pct, talent_category, assessment_date
    FROM (
        SELECT
            ath.id AS athlete_id,
            ath.name AS athlete_name,
            ath.sport AS sport,
            u.name AS coach_name,
            ROUND((
                aa.speed_rating + aa.agility_rating + aa.balance_rating + aa.coordination_rating +
                aa.strength_rating + aa.endurance_rating + aa.technique_rating + aa.control_accuracy_rating +
                aa.footwork_rating + aa.game_awareness_rating + aa.decision_making_rating +
                aa.follow_instructions_rating + aa.discipline_rating + aa.effort_rating +
                aa.coachability_rating + aa.confidence_rating + aa.team_behaviour_rating
            ) / 17.0, 2) AS avg_rating,
            aa.attendance_pct AS attendance_pct,
            aa.talent_category AS talent_category,
            aa.assessment_date AS assessment_date,
            ROW_NUMBER() OVER (PARTITION BY aa.athlete_id ORDER BY aa.assessment_date DESC, aa.id DESC) AS rn
        FROM athlete_assessments aa
        JOIN athletes ath ON ath.id = aa.athlete_id
        JOIN coaches c ON c.id = aa.coach_id
        JOIN users u ON u.id = c.user_id
        WHERE aa.is_archived = 0 AND aa.status <> 'Draft' AND ath.is_archived = 0
    ) ranked
    WHERE rn = 1
    ORDER BY avg_rating DESC
    LIMIT p_limit;
END $$

DROP PROCEDURE IF EXISTS `sp_reset_token_create` $$
CREATE PROCEDURE `sp_reset_token_create`(
    IN p_token VARCHAR(255),
    IN p_user_id INT,
    IN p_expires_at DATETIME
)
BEGIN
    INSERT INTO password_reset_tokens (token, user_id, expires_at)
    VALUES (p_token, p_user_id, p_expires_at);
END $$

DROP PROCEDURE IF EXISTS `sp_reset_token_delete_expired` $$
CREATE PROCEDURE `sp_reset_token_delete_expired`()
BEGIN
    DELETE FROM password_reset_tokens WHERE expires_at < NOW();
END $$

DROP PROCEDURE IF EXISTS `sp_reset_token_get` $$
CREATE PROCEDURE `sp_reset_token_get`(IN p_token VARCHAR(255))
BEGIN
    SELECT * FROM password_reset_tokens
     WHERE token = p_token AND used = FALSE AND expires_at > NOW();
END $$

DROP PROCEDURE IF EXISTS `sp_reset_token_mark_used` $$
CREATE PROCEDURE `sp_reset_token_mark_used`(IN p_token VARCHAR(255))
BEGIN
    UPDATE password_reset_tokens SET used = TRUE WHERE token = p_token;
END $$

DROP PROCEDURE IF EXISTS `sp_sport_archive` $$
CREATE PROCEDURE `sp_sport_archive`(IN p_id INT, IN p_is_archived TINYINT(1))
BEGIN
    UPDATE sports SET is_archived = p_is_archived WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_sport_create` $$
CREATE PROCEDURE `sp_sport_create`(IN p_name VARCHAR(100), OUT p_id INT)
BEGIN
    INSERT INTO sports (name) VALUES (p_name);
    SET p_id = LAST_INSERT_ID();
END $$

DROP PROCEDURE IF EXISTS `sp_sport_get_by_id` $$
CREATE PROCEDURE `sp_sport_get_by_id`(IN p_id INT)
BEGIN
    SELECT id, name, is_archived, created_at FROM sports WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_sport_get_by_name` $$
CREATE PROCEDURE `sp_sport_get_by_name`(IN p_name VARCHAR(100))
BEGIN
    SELECT id, name, is_archived, created_at FROM sports WHERE name = p_name;
END $$

DROP PROCEDURE IF EXISTS `sp_sport_list` $$
CREATE PROCEDURE `sp_sport_list`(IN p_is_archived TINYINT(1))
BEGIN
    SELECT id, name, is_archived, created_at
    FROM sports
    WHERE (p_is_archived IS NULL OR is_archived = p_is_archived)
    ORDER BY name;
END $$

DROP PROCEDURE IF EXISTS `sp_sport_update` $$
CREATE PROCEDURE `sp_sport_update`(IN p_id INT, IN p_name VARCHAR(100))
BEGIN
    UPDATE sports SET name = p_name WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_superadmin_dashboard_coach_sport_matrix` $$
CREATE PROCEDURE `sp_superadmin_dashboard_coach_sport_matrix`()
BEGIN
    SELECT
        c.id                                                                  AS coach_id,
        u.name                                                                AS coach_name,
        COALESCE(NULLIF(a.sport, ''), 'Unspecified')                          AS sport,
        COUNT(*)                                                              AS athlete_count
    FROM athletes a
    JOIN coaches c ON c.id = a.coach_id
    JOIN users u ON u.id = c.user_id
    WHERE a.is_archived = 0 AND u.is_archived = 0
    GROUP BY c.id, u.name, COALESCE(NULLIF(a.sport, ''), 'Unspecified')
    ORDER BY u.name, athlete_count DESC;
END $$

DROP PROCEDURE IF EXISTS `sp_superadmin_dashboard_sport_breakdown` $$
CREATE PROCEDURE `sp_superadmin_dashboard_sport_breakdown`()
BEGIN
    SELECT
        COALESCE(NULLIF(a.sport, ''), 'Unspecified')                          AS sport,
        COUNT(DISTINCT a.id)                                                  AS athlete_count,
        COUNT(DISTINCT a.coach_id)                                            AS coach_count,
        COALESCE(SUM(aa.sessions_planned), 0)                                 AS sessions_planned,
        COALESCE(SUM(aa.sessions_attended), 0)                                AS sessions_attended,
        ROUND(AVG(aa.attendance_pct), 1)                                      AS avg_attendance_pct
    FROM athletes a
    LEFT JOIN athlete_assessments aa
           ON aa.athlete_id = a.id AND aa.is_archived = 0
    WHERE a.is_archived = 0
    GROUP BY COALESCE(NULLIF(a.sport, ''), 'Unspecified')
    ORDER BY athlete_count DESC;
END $$

DROP PROCEDURE IF EXISTS `sp_superadmin_dashboard_stats` $$
CREATE PROCEDURE `sp_superadmin_dashboard_stats`()
BEGIN
    SELECT
        (SELECT COUNT(*)
           FROM users
          WHERE role = 'admin' AND is_archived = 0)                           AS admin_count,
        (SELECT COUNT(*)
           FROM coaches c
           JOIN users u ON u.id = c.user_id
          WHERE u.is_archived = 0)                                            AS coach_count,
        (SELECT COUNT(*)
           FROM athletes
          WHERE is_archived = 0)                                              AS athlete_count,
        (SELECT COUNT(DISTINCT sport)
           FROM athletes
          WHERE is_archived = 0 AND sport IS NOT NULL AND sport <> '')        AS sport_count,
        (SELECT COALESCE(SUM(sessions_planned), 0)
           FROM athlete_assessments
          WHERE is_archived = 0)                                              AS sessions_planned_total,
        (SELECT COALESCE(SUM(sessions_attended), 0)
           FROM athlete_assessments
          WHERE is_archived = 0)                                              AS sessions_attended_total,
        (SELECT ROUND(AVG(attendance_pct), 1)
           FROM athlete_assessments
          WHERE is_archived = 0 AND attendance_pct IS NOT NULL)               AS avg_attendance_pct;
END $$

DROP PROCEDURE IF EXISTS `sp_user_archive` $$
CREATE PROCEDURE `sp_user_archive`(
    IN p_id INT,
    IN p_is_archived BOOLEAN
)
BEGIN
    UPDATE users SET is_archived = p_is_archived WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_user_create` $$
CREATE PROCEDURE `sp_user_create`(
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

DROP PROCEDURE IF EXISTS `sp_user_delete` $$
CREATE PROCEDURE `sp_user_delete`(IN p_id INT)
BEGIN
    DELETE FROM users WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_user_get_by_id` $$
CREATE PROCEDURE `sp_user_get_by_id`(IN p_id INT)
BEGIN
    SELECT * FROM users WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_user_get_by_username` $$
CREATE PROCEDURE `sp_user_get_by_username`(IN p_username VARCHAR(50))
BEGIN
    SELECT * FROM users WHERE username = p_username;
END $$

DROP PROCEDURE IF EXISTS `sp_user_list` $$
CREATE PROCEDURE `sp_user_list`(
    IN p_role VARCHAR(20),
    IN p_is_archived TINYINT
)
BEGIN
    SELECT * FROM users
    WHERE (p_role IS NULL OR role = p_role)
      AND (p_is_archived IS NULL OR is_archived = p_is_archived)
    ORDER BY created_at DESC;
END $$

DROP PROCEDURE IF EXISTS `sp_user_update` $$
CREATE PROCEDURE `sp_user_update`(
    IN p_id INT,
    IN p_name VARCHAR(100),
    IN p_email VARCHAR(120)
)
BEGIN
    UPDATE users SET name = p_name, email = p_email WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS `sp_user_update_password` $$
CREATE PROCEDURE `sp_user_update_password`(
    IN p_id INT,
    IN p_password_hash VARCHAR(255)
)
BEGIN
    UPDATE users SET password_hash = p_password_hash WHERE id = p_id;
END $$

DELIMITER ;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- Done. Verify with:
--   SELECT COUNT(*) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA = 'bjk_athletes';
--   SHOW TABLES;
-- ---------------------------------------------------------------------
