-- =====================================================================
-- Athlete Assessment Module - Schema + Stored Procedures
-- Digitized from the paper "Athlete Performance Evaluation" form.
-- Run this once against the bjk_athletes database.
-- =====================================================================

USE bjk_athletes;

-- ---------------------------------------------------------------------
-- TABLE: athlete_assessments
-- One row per coach assessment "sitting" for an athlete (form is filled
-- periodically, so history is naturally preserved).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS athlete_assessments (
    id                              INT AUTO_INCREMENT PRIMARY KEY,
    athlete_id                      INT NOT NULL,
    coach_id                        INT NOT NULL,
    assessment_date                 DATE NOT NULL,
    status                          ENUM('Draft','Submitted','Under Review','Approved & Published') NOT NULL DEFAULT 'Draft',

    -- Section 1: Basic Athlete Info (derived / per-assessment fields only;
    -- name/DOB/sport/coach live on athletes/coaches and are joined in)
    calculated_age                  INT NULL,
    age_group_focus                 VARCHAR(50) NULL,
    level                           ENUM('Beginner','Intermediate','Advanced') NULL,

    -- Section 2: Attendance / Training Exposure
    sessions_planned                INT NULL,
    sessions_attended               INT NULL,
    attendance_pct                  DECIMAL(5,2) NULL,
    attendance_remarks              TEXT NULL,

    -- Section 3: Physical Development (1-5 ratings)
    speed_rating                    TINYINT NULL,
    speed_remarks                   TEXT NULL,
    agility_rating                  TINYINT NULL,
    agility_remarks                 TEXT NULL,
    balance_rating                  TINYINT NULL,
    balance_remarks                 TEXT NULL,
    coordination_rating             TINYINT NULL,
    coordination_remarks            TEXT NULL,
    strength_rating                 TINYINT NULL,
    strength_remarks                TEXT NULL,
    endurance_rating                TINYINT NULL,
    endurance_remarks               TEXT NULL,

    -- Section 4A: Technical Understanding
    technique_rating                TINYINT NULL,
    technique_remarks               TEXT NULL,
    control_accuracy_rating         TINYINT NULL,
    control_accuracy_remarks        TEXT NULL,
    footwork_rating                 TINYINT NULL,
    footwork_remarks                TEXT NULL,

    -- Section 4B: Tactical Understanding
    game_awareness_rating           TINYINT NULL,
    game_awareness_remarks          TEXT NULL,
    decision_making_rating          TINYINT NULL,
    decision_making_remarks         TEXT NULL,
    follow_instructions_rating      TINYINT NULL,
    follow_instructions_remarks     TEXT NULL,

    -- Section 5: Psychological & Behavioral Attributes
    discipline_rating               TINYINT NULL,
    discipline_remarks              TEXT NULL,
    effort_rating                   TINYINT NULL,
    effort_remarks                  TEXT NULL,
    coachability_rating             TINYINT NULL,
    coachability_remarks            TEXT NULL,
    confidence_rating               TINYINT NULL,
    confidence_remarks              TEXT NULL,
    team_behaviour_rating           TINYINT NULL,
    team_behaviour_remarks          TEXT NULL,

    -- Section 6: Talent Identification Marker
    talent_category                 ENUM('Recreational','Developing','Potential Talent','High Potential') NULL,
    talent_justification            TEXT NULL,

    -- Section 7: Key Strengths (Top 3)
    strength_1                      VARCHAR(500) NULL,
    strength_2                      VARCHAR(500) NULL,
    strength_3                      VARCHAR(500) NULL,

    -- Section 8: Key Areas for Improvement (Top 3)
    improvement_1                   VARCHAR(500) NULL,
    improvement_2                   VARCHAR(500) NULL,
    improvement_3                   VARCHAR(500) NULL,

    -- Section 9: Individual Development Plan (4-8 weeks)
    idp_technical_action            VARCHAR(500) NULL,
    idp_technical_responsibility    ENUM('Athlete','Coach','Parent','Shared (Coach/Athlete)','Shared (Parent/Athlete)') NULL,
    idp_physical_action             TEXT NULL,
    idp_physical_responsibility     ENUM('Athlete','Coach','Parent','Shared (Coach/Athlete)','Shared (Parent/Athlete)') NULL,
    idp_behavioral_action           TEXT NULL,
    idp_behavioral_responsibility   ENUM('Athlete','Coach','Parent','Shared (Coach/Athlete)','Shared (Parent/Athlete)') NULL,

    -- Section 10: Parents Feedback
    parent_name                     VARCHAR(100) NULL,
    parent_feedback                 VARCHAR(1000) NULL,

    -- Section 11: Coach's Summary
    overall_progress                ENUM('Excellent','Good','Average','Need Attention') NULL,
    coach_summary_remarks           VARCHAR(1000) NULL,

    -- Meta
    created_by                      INT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    submitted_at                    TIMESTAMP NULL,
    is_archived                     TINYINT(1) NOT NULL DEFAULT 0,

    CONSTRAINT fk_assessment_athlete FOREIGN KEY (athlete_id) REFERENCES athletes(id),
    CONSTRAINT fk_assessment_coach   FOREIGN KEY (coach_id)   REFERENCES coaches(id),
    INDEX idx_assessment_athlete (athlete_id),
    INDEX idx_assessment_coach (coach_id),
    INDEX idx_assessment_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- =====================================================================
-- STORED PROCEDURES
-- Field order below is the single source of truth. It MUST match
-- ASSESSMENT_FIELDS in common/models.py exactly.
-- =====================================================================

DELIMITER $$

-- ---------------------------------------------------------------------
-- sp_assessment_create
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_assessment_create $$
CREATE PROCEDURE sp_assessment_create(
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


-- ---------------------------------------------------------------------
-- sp_assessment_update  (same field order, prefixed by id)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_assessment_update $$
CREATE PROCEDURE sp_assessment_update(
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


-- ---------------------------------------------------------------------
-- sp_assessment_get_by_id  (joined with athlete + coach names for display)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_assessment_get_by_id $$
CREATE PROCEDURE sp_assessment_get_by_id(IN p_id INT)
BEGIN
    SELECT a.*, ath.name AS athlete_name, ath.dob AS athlete_dob, ath.sport AS athlete_sport,
           u.name AS coach_name
    FROM athlete_assessments a
    JOIN athletes ath ON ath.id = a.athlete_id
    JOIN coaches c ON c.id = a.coach_id
    JOIN users u ON u.id = c.user_id
    WHERE a.id = p_id;
END $$


-- ---------------------------------------------------------------------
-- sp_assessment_list
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_assessment_list $$
CREATE PROCEDURE sp_assessment_list(
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


-- ---------------------------------------------------------------------
-- sp_assessment_archive / sp_assessment_delete
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_assessment_archive $$
CREATE PROCEDURE sp_assessment_archive(IN p_id INT, IN p_is_archived TINYINT)
BEGIN
    UPDATE athlete_assessments SET is_archived = p_is_archived WHERE id = p_id;
END $$

DROP PROCEDURE IF EXISTS sp_assessment_delete $$
CREATE PROCEDURE sp_assessment_delete(IN p_id INT)
BEGIN
    DELETE FROM athlete_assessments WHERE id = p_id;
END $$

DELIMITER ;
