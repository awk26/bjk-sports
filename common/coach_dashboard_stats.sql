-- =====================================================================
-- Coach Dashboard Stats - Stored Procedures
-- Powers the coach-facing top-level Dashboard (dashboard.html): total
-- athletes, total sports, total sessions planned/attended, and a
-- sport-wise breakdown chart -- all scoped to a single coach.
-- Run this once against the bjk_athletes database (after
-- assessment_schema.sql). Safe to re-run any time (idempotent DROP + CREATE).
-- =====================================================================

USE bjk_athletes;

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_coach_dashboard_stats: top-line KPI cards
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_coach_dashboard_stats $$
CREATE PROCEDURE sp_coach_dashboard_stats(IN p_coach_id INT)
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


-- ---------------------------------------------------------------------
-- sp_coach_dashboard_sport_breakdown: athletes + sessions, grouped by sport
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_coach_dashboard_sport_breakdown $$
CREATE PROCEDURE sp_coach_dashboard_sport_breakdown(IN p_coach_id INT)
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

DELIMITER ;
