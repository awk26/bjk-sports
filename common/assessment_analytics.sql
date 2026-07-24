-- =====================================================================
-- Athlete Assessment Analytics - Stored Procedures
-- Powers the coach-facing Performance Analytics Dashboard.
-- Run this once against the bjk_athletes database (after assessment_schema.sql).
-- Safe to re-run any time (idempotent DROP + CREATE) -- re-run this file
-- after pulling this update to pick up the new filter parameters used by
-- the Analytics Dashboard filter bar (athlete / sport / date range).
--
-- Note: rating averages only consider Submitted/reviewed/approved
-- assessments (status <> 'Draft'), since Draft rows can have partially
-- filled ratings which would skew the numbers.
--
-- All filter params below are optional -- pass NULL to mean "no filter"
-- (matches the existing pattern used by sp_athlete_list etc.):
--   p_athlete_id  INT      -> restrict to a single athlete
--   p_sport       VARCHAR  -> restrict to athletes of a given sport
--   p_date_from   DATE     -> assessment_date >= p_date_from
--   p_date_to     DATE     -> assessment_date <= p_date_to
-- =====================================================================

USE bjk_athletes;

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_analytics_kpis: top-line summary cards
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_kpis $$
CREATE PROCEDURE sp_analytics_kpis(
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


-- ---------------------------------------------------------------------
-- sp_analytics_category_averages: avg rating per assessment section
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_category_averages $$
CREATE PROCEDURE sp_analytics_category_averages(
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


-- ---------------------------------------------------------------------
-- sp_analytics_talent_distribution
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_talent_distribution $$
CREATE PROCEDURE sp_analytics_talent_distribution(
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


-- ---------------------------------------------------------------------
-- sp_analytics_progress_distribution
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_progress_distribution $$
CREATE PROCEDURE sp_analytics_progress_distribution(
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


-- ---------------------------------------------------------------------
-- sp_analytics_monthly_trend: attendance % + overall rating, by month
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_analytics_monthly_trend $$
CREATE PROCEDURE sp_analytics_monthly_trend(
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

DELIMITER ;
