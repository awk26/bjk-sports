-- =====================================================================
-- Athlete Assessment Analytics - PER-ATHLETE procedures
-- Powers the individual athlete's Performance Analytics Dashboard
-- (coach clicks a single athlete -> sees only that athlete's data).
-- Run this once against the bjk_athletes database (after
-- assessment_schema.sql and assessment_analytics.sql).
-- =====================================================================

USE bjk_athletes;

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_analytics_athlete_kpis
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_athlete_kpis $$
CREATE PROCEDURE sp_analytics_athlete_kpis(IN p_athlete_id INT, IN p_coach_id INT)
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


-- ---------------------------------------------------------------------
-- sp_analytics_athlete_latest: most recent finalized assessment snapshot
-- (used for the "current standing" radar + talent/progress badges)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_athlete_latest $$
CREATE PROCEDURE sp_analytics_athlete_latest(IN p_athlete_id INT, IN p_coach_id INT)
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


-- ---------------------------------------------------------------------
-- sp_analytics_athlete_trend: one row per finalized assessment, in date
-- order — attendance % and overall rating, for the progression line chart
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_athlete_trend $$
CREATE PROCEDURE sp_analytics_athlete_trend(IN p_athlete_id INT, IN p_coach_id INT)
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


-- ---------------------------------------------------------------------
-- sp_analytics_athlete_category_trend: category averages per assessment,
-- in date order — for the 4-line "skill progression" chart
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_athlete_category_trend $$
CREATE PROCEDURE sp_analytics_athlete_category_trend(IN p_athlete_id INT, IN p_coach_id INT)
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

DELIMITER ;
