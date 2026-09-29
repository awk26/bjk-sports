-- =====================================================================
-- Athletes -- Identification, Schooling & Health fields
-- Adds the columns backing the "Identification, Schooling & Health"
-- section of the Add/Edit Athlete form (admin & coach).
--
-- Not required to run manually: common/models.py -> ensure_schema_extensions()
-- applies these same columns automatically at app startup (each is
-- skipped there if it already exists). This file exists so the change
-- can also be applied directly / reviewed / run against another
-- environment ahead of a deploy.
--
-- Run once, naming the target database on the command line. There is no
-- "USE" statement here on purpose: hardcoding one (as the other .sql files
-- in this repo do) points at the DEV database even when you mean prod.
--
--   dev :  mysql -h <host> -P <port> -u <user> -p bjk_athletes < common/athlete_extended_fields_migration.sql
--   prod:  mysql -h <host> -P <port> -u <user> -p bjksports    < common/athlete_extended_fields_migration.sql
--
-- Running it a second time will error on "Duplicate column name" for any
-- column already added -- that's expected, it just means it's applied.
-- =====================================================================

ALTER TABLE athletes ADD COLUMN nationality      VARCHAR(50)  NULL;
ALTER TABLE athletes ADD COLUMN id_proof_type    VARCHAR(50)  NULL;
ALTER TABLE athletes ADD COLUMN id_proof_number  VARCHAR(50)  NULL;
ALTER TABLE athletes ADD COLUMN school_name      VARCHAR(150) NULL;
ALTER TABLE athletes ADD COLUMN school_grade     VARCHAR(20)  NULL;
ALTER TABLE athletes ADD COLUMN admission_date   DATE         NULL;
ALTER TABLE athletes ADD COLUMN medical_notes    TEXT         NULL;

-- Verification: SHOW COLUMNS FROM athletes;
