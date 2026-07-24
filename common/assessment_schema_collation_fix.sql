-- =====================================================================
-- Fix: collation mismatch between athlete_assessments and the existing
-- athletes/coaches/users tables.
--
-- Your DB's default collation (utf8mb4_0900_ai_ci, MySQL 8 default)
-- differs from the collation the rest of bjk_athletes uses
-- (utf8mb4_unicode_ci). Run this once after creating athlete_assessments.
-- =====================================================================

USE bjk_athletes;

-- Sanity check first — confirm what collation your existing tables use.
-- If this shows something other than utf8mb4_unicode_ci, change the
-- COLLATE clause below to match before running the ALTER.
SELECT TABLE_NAME, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'bjk_athletes'
  AND TABLE_NAME IN ('athletes', 'coaches', 'users', 'athlete_assessments');

-- Bring athlete_assessments in line with the rest of the schema.
ALTER TABLE athlete_assessments
    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
