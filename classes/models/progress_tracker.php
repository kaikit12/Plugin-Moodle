<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

namespace local_exercise_suggestion\models;

defined('MOODLE_INTERNAL') || die();

/**
 * Progress Tracker - Track exercise progress theo section 6.2.1.C
 * Status flow: pending → in_progress → submitted → graded
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class progress_tracker {

    /** @var array Valid status values */
    const VALID_STATUSES = ['pending', 'in_progress', 'submitted', 'graded'];

    /**
     * Create or update progress record (UC2 - student starts exercise)
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $exerciseid Exercise ID from API
     * @param string $status Status (pending, in_progress, submitted, graded)
     * @param array $data Additional data (submission_id, score, max_score, time_spent)
     * @return int|bool Progress record ID or false on failure
     */
    public static function update_progress($userid, $courseid, $exerciseid, $status, $data = []) {
        global $DB;

        // Validate status
        if (!in_array($status, self::VALID_STATUSES)) {
            debugging("Invalid status: {$status}", DEBUG_DEVELOPER);
            return false;
        }

        // Check if progress record exists
        $existing = $DB->get_record('local_exsug_progress', [
            'userid' => $userid,
            'courseid' => $courseid,
            'exerciseid' => $exerciseid
        ]);

        $now = time();

        if ($existing) {
            // Update existing record
            $existing->status = $status;
            $existing->timemodified = $now;

            if (isset($data['submission_id'])) {
                $existing->submission_id = $data['submission_id'];
            }
            if (isset($data['score'])) {
                $existing->score = $data['score'];
            }
            if (isset($data['max_score'])) {
                $existing->max_score = $data['max_score'];
            }
            if (isset($data['time_spent'])) {
                $existing->time_spent = $data['time_spent'];
            }

            $DB->update_record('local_exsug_progress', $existing);
            return $existing->id;

        } else {
            // Create new record
            $record = new \stdClass();
            $record->userid = $userid;
            $record->courseid = $courseid;
            $record->exerciseid = $exerciseid;
            $record->status = $status;
            $record->submission_id = $data['submission_id'] ?? null;
            $record->score = $data['score'] ?? null;
            $record->max_score = $data['max_score'] ?? null;
            $record->time_spent = $data['time_spent'] ?? null;
            $record->timecreated = $now;
            $record->timemodified = $now;

            return $DB->insert_record('local_exsug_progress', $record);
        }
    }

    /**
     * Mark exercise as in progress (UC2 - student starts doing exercise)
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $exerciseid Exercise ID
     * @return int|bool Progress record ID or false
     */
    public static function mark_in_progress($userid, $courseid, $exerciseid) {
        return self::update_progress($userid, $courseid, $exerciseid, 'in_progress');
    }

    /**
     * Mark exercise as submitted (UC3 - student submits solution)
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $exerciseid Exercise ID
     * @param string $submissionid Submission ID from API
     * @param int $timespent Time spent in seconds
     * @return int|bool Progress record ID or false
     */
    public static function mark_submitted($userid, $courseid, $exerciseid, $submissionid, $timespent = 0) {
        return self::update_progress($userid, $courseid, $exerciseid, 'submitted', [
            'submission_id' => $submissionid,
            'time_spent' => $timespent
        ]);
    }

    /**
     * Mark exercise as graded (UC4 - result is available)
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $exerciseid Exercise ID
     * @param float $score Student's score
     * @param float $maxscore Maximum possible score
     * @return int|bool Progress record ID or false
     */
    public static function mark_graded($userid, $courseid, $exerciseid, $score, $maxscore) {
        return self::update_progress($userid, $courseid, $exerciseid, 'graded', [
            'score' => $score,
            'max_score' => $maxscore
        ]);
    }

    /**
     * Get progress record for a specific exercise
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $exerciseid Exercise ID
     * @return \stdClass|false Progress record or false if not found
     */
    public static function get_progress($userid, $courseid, $exerciseid) {
        global $DB;

        return $DB->get_record('local_exsug_progress', [
            'userid' => $userid,
            'courseid' => $courseid,
            'exerciseid' => $exerciseid
        ]);
    }

    /**
     * Get progress record by submission ID
     *
     * @param string $submissionid Submission ID
     * @return \stdClass|false Progress record or false if not found
     */
    public static function get_progress_by_submission($submissionid) {
        global $DB;

        return $DB->get_record('local_exsug_progress', ['submission_id' => $submissionid]);
    }

    /**
     * Get all progress records for a user in a course
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string|null $status Filter by status (optional)
     * @return array Array of progress records
     */
    public static function get_user_progress($userid, $courseid, $status = null) {
        global $DB;

        $conditions = [
            'userid' => $userid,
            'courseid' => $courseid
        ];

        if ($status !== null && in_array($status, self::VALID_STATUSES)) {
            $conditions['status'] = $status;
        }

        return $DB->get_records('local_exsug_progress', $conditions, 'timemodified DESC');
    }

    /**
     * Get course progress statistics
     *
     * @param int $courseid Course ID
     * @return array Statistics array
     */
    public static function get_course_statistics($courseid) {
        global $DB;

        $sql = "SELECT status, COUNT(*) as count
                  FROM {local_exsug_progress}
                 WHERE courseid = :courseid
              GROUP BY status";

        $statusstats = $DB->get_records_sql($sql, ['courseid' => $courseid]);

        // Calculate totals
        $totalexercises = 0;
        $stats = [];
        foreach (self::VALID_STATUSES as $status) {
            $count = isset($statusstats[$status]) ? $statusstats[$status]->count : 0;
            $stats[$status] = $count;
            $totalexercises += $count;
        }

        // Average score for graded exercises
        $sql = "SELECT AVG(score) as avg_score, AVG(score / max_score * 100) as avg_percentage
                  FROM {local_exsug_progress}
                 WHERE courseid = :courseid
                   AND status = 'graded'
                   AND max_score > 0";
        $scorestats = $DB->get_record_sql($sql, ['courseid' => $courseid]);

        return [
            'total_exercises' => $totalexercises,
            'pending' => $stats['pending'],
            'in_progress' => $stats['in_progress'],
            'submitted' => $stats['submitted'],
            'graded' => $stats['graded'],
            'avg_score' => $scorestats ? round($scorestats->avg_score, 2) : 0,
            'avg_percentage' => $scorestats ? round($scorestats->avg_percentage, 2) : 0
        ];
    }

    /**
     * Get student's completion rate in a course
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @return float Completion rate (0-100)
     */
    public static function get_completion_rate($userid, $courseid) {
        global $DB;

        $total = $DB->count_records('local_exsug_progress', [
            'userid' => $userid,
            'courseid' => $courseid
        ]);

        if ($total == 0) {
            return 0.0;
        }

        $completed = $DB->count_records('local_exsug_progress', [
            'userid' => $userid,
            'courseid' => $courseid,
            'status' => 'graded'
        ]);

        return round(($completed / $total) * 100, 2);
    }

    /**
     * Get student's average score in a course
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @return float Average score percentage
     */
    public static function get_average_score($userid, $courseid) {
        global $DB;

        $sql = "SELECT AVG(score / max_score * 100) as avg_percentage
                  FROM {local_exsug_progress}
                 WHERE userid = :userid
                   AND courseid = :courseid
                   AND status = 'graded'
                   AND max_score > 0";

        $result = $DB->get_field_sql($sql, ['userid' => $userid, 'courseid' => $courseid]);

        return $result ? round($result, 2) : 0.0;
    }

    /**
     * Delete progress record (for testing or cleanup)
     *
     * @param int $progressid Progress record ID
     * @return bool True if deleted successfully
     */
    public static function delete_progress($progressid) {
        global $DB;

        return $DB->delete_records('local_exsug_progress', ['id' => $progressid]);
    }

    /**
     * Get recent activity for a user
     *
     * @param int $userid User ID
     * @param int $limit Maximum number of records
     * @return array Array of progress records
     */
    public static function get_recent_activity($userid, $limit = 10) {
        global $DB;

        return $DB->get_records('local_exsug_progress', 
            ['userid' => $userid], 
            'timemodified DESC', 
            '*', 
            0, 
            $limit
        );
    }
}

