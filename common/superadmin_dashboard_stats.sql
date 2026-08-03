-- =====================================================================
-- Superadmin Dashboard Stats - Stored Procedures
-- Powers the superadmin-facing top-level Dashboard (dashboard.html):
-- org-wide KPI cards (admins/coaches/athletes/sports/sessions) and a
-- sport-wise breakdown across every coach in the organisation.
-- Run this once against the bjk_athletes database (after
-- assessment_schema.sql and coach_dashboard_stats.sql). Safe to re-run
-- any time (idempotent DROP + CREATE).
-- =====================================================================

USE bjk_athletes;

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_superadmin_dashboard_stats: top-line, org-wide KPI cards
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_superadmin_dashboard_stats $$
CREATE PROCEDURE sp_superadmin_dashboard_stats()
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


-- ---------------------------------------------------------------------
-- sp_superadmin_dashboard_sport_breakdown: org-wide, grouped by sport
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_superadmin_dashboard_sport_breakdown $$
CREATE PROCEDURE sp_superadmin_dashboard_sport_breakdown()
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


-- ---------------------------------------------------------------------
-- sp_superadmin_dashboard_coach_sport_matrix: coaches x sports, for a
-- "which coach covers which sport" breakdown (athlete counts per cell)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_superadmin_dashboard_coach_sport_matrix $$
CREATE PROCEDURE sp_superadmin_dashboard_coach_sport_matrix()
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

DELIMITER ;
