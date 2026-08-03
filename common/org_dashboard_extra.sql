-- =====================================================================
-- Org-wide Dashboard Extras - Stored Procedures
-- Shared by both the Admin and Super Admin premium dashboards
-- (dashboard.html): a top-athlete leaderboard and an age-distribution
-- breakdown, both computed across every coach in the organisation.
-- Run this once against the bjk_athletes database (after
-- assessment_schema.sql and superadmin_dashboard_stats.sql). Safe to
-- re-run any time (idempotent DROP + CREATE). Requires MySQL 8.0+
-- (window functions).
-- =====================================================================

USE bjk_athletes;

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_org_dashboard_top_athletes: leaderboard, ranked by average rating
-- across the 17 assessment categories on each athlete's most recent
-- finalized (non-Draft) assessment.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_org_dashboard_top_athletes $$
CREATE PROCEDURE sp_org_dashboard_top_athletes(IN p_limit INT)
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


-- ---------------------------------------------------------------------
-- sp_org_dashboard_age_distribution: athlete counts by age bracket
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_org_dashboard_age_distribution $$
CREATE PROCEDURE sp_org_dashboard_age_distribution()
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

DELIMITER ;
