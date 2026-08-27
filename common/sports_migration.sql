-- =====================================================================
-- Sports Master -- one-time data migration
-- Run AFTER sports_schema.sql. Seeds the Sports Master from every
-- distinct sport-like string already in use, then links existing
-- athletes/coaches to their matching Sports Master row. Safe to re-run
-- (every insert is IGNORE-on-duplicate).
-- =====================================================================

USE bjk_athletes;

-- 1. Seed Sports Master from existing free-text values.
INSERT IGNORE INTO sports (name)
SELECT DISTINCT TRIM(sport) FROM athletes
WHERE sport IS NOT NULL AND TRIM(sport) <> '';

INSERT IGNORE INTO sports (name)
SELECT DISTINCT TRIM(specialty) FROM coaches
WHERE specialty IS NOT NULL AND TRIM(specialty) <> '';

-- 2. Link each athlete to their existing single sport (their one legacy
--    value becomes their first Sports Master entry -- add more later via
--    the Edit Athlete form).
INSERT IGNORE INTO athlete_sports (athlete_id, sport_id)
SELECT a.id, s.id
FROM athletes a
JOIN sports s ON s.name = TRIM(a.sport)
WHERE a.sport IS NOT NULL AND TRIM(a.sport) <> '';

-- 3. Link each coach to a sport only where their free-text `specialty`
--    matches a Sports Master name exactly (case-insensitive). Specialty
--    values that aren't sport names (e.g. "Youth Development") won't
--    auto-map -- assign those coaches' sports manually from the Coaches
--    page afterwards.
INSERT IGNORE INTO coach_sports (coach_id, sport_id)
SELECT c.id, s.id
FROM coaches c
JOIN sports s ON LOWER(s.name) = LOWER(TRIM(c.specialty))
WHERE c.specialty IS NOT NULL AND TRIM(c.specialty) <> '';
