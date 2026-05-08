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
 * API Call Logger - Ghi log API calls theo section 6.2.1.A
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class logger {

    /**
     * Log an API call to database
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $action Action name (get_suggestions, get_exercise, submit, get_result)
     * @param string $apiendpoint API endpoint URL
     * @param int $httpstatus HTTP status code
     * @param float $responsetime Response time in seconds
     * @param string|null $errormessage Error message if request failed
     * @return bool True if logged successfully
     */
    public static function log_api_call($userid, $courseid, $action, $apiendpoint, $httpstatus, $responsetime, $errormessage = null) {
        global $DB;

        $logrecord = new \stdClass();
        $logrecord->userid = $userid;
        $logrecord->courseid = $courseid;
        $logrecord->action = $action;
        $logrecord->api_endpoint = $apiendpoint;
        $logrecord->http_status = $httpstatus;
        $logrecord->response_time = $responsetime;
        $logrecord->error_message = $errormessage;
        $logrecord->timecreated = time();

        try {
            $DB->insert_record('local_exsug_logs', $logrecord);
            return true;
        } catch (\Exception $e) {
            // Don't throw exception on logging failure
            debugging('Failed to log API call: ' . $e->getMessage(), DEBUG_DEVELOPER);
            return false;
        }
    }

    /**
     * Get API logs for a user in a course
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param int $limit Maximum number of logs to retrieve
     * @return array Array of log records
     */
    public static function get_user_logs($userid, $courseid, $limit = 50) {
        global $DB;

        $sql = "SELECT *
                  FROM {local_exsug_logs}
                 WHERE userid = :userid
                   AND courseid = :courseid
              ORDER BY timecreated DESC";

        return $DB->get_records_sql($sql, ['userid' => $userid, 'courseid' => $courseid], 0, $limit);
    }

    /**
     * Get API logs by action type
     *
     * @param string $action Action name (get_suggestions, get_exercise, submit, get_result)
     * @param int $limit Maximum number of logs to retrieve
     * @return array Array of log records
     */
    public static function get_logs_by_action($action, $limit = 50) {
        global $DB;

        return $DB->get_records('local_exsug_logs', ['action' => $action], 'timecreated DESC', '*', 0, $limit);
    }

    /**
     * Get failed API calls (http_status >= 400)
     *
     * @param int $limit Maximum number of logs to retrieve
     * @return array Array of log records
     */
    public static function get_failed_logs($limit = 50) {
        global $DB;

        $sql = "SELECT *
                  FROM {local_exsug_logs}
                 WHERE http_status >= 400
              ORDER BY timecreated DESC";

        return $DB->get_records_sql($sql, [], 0, $limit);
    }

    /**
     * Get API call statistics for a course
     *
     * @param int $courseid Course ID
     * @param int $timestart Start timestamp (optional)
     * @param int $timeend End timestamp (optional)
     * @return array Statistics array
     */
    public static function get_course_statistics($courseid, $timestart = 0, $timeend = 0) {
        global $DB;

        $params = ['courseid' => $courseid];
        $timesql = '';

        if ($timestart > 0) {
            $timesql .= ' AND timecreated >= :timestart';
            $params['timestart'] = $timestart;
        }

        if ($timeend > 0) {
            $timesql .= ' AND timecreated <= :timeend';
            $params['timeend'] = $timeend;
        }

        // Total calls
        $totalcalls = $DB->count_records_select('local_exsug_logs', "courseid = :courseid{$timesql}", $params);

        // Calls by action
        $sql = "SELECT action, COUNT(*) as count
                  FROM {local_exsug_logs}
                 WHERE courseid = :courseid{$timesql}
              GROUP BY action";
        $actionstats = $DB->get_records_sql($sql, $params);

        // Success rate (http_status 200-299)
        $sql = "SELECT COUNT(*) as count
                  FROM {local_exsug_logs}
                 WHERE courseid = :courseid
                   AND http_status >= 200
                   AND http_status < 300{$timesql}";
        $successcount = $DB->get_field_sql($sql, $params);

        $successrate = $totalcalls > 0 ? ($successcount / $totalcalls) * 100 : 0;

        // Average response time
        $sql = "SELECT AVG(response_time) as avg_time
                  FROM {local_exsug_logs}
                 WHERE courseid = :courseid{$timesql}";
        $avgresponsetime = $DB->get_field_sql($sql, $params);

        return [
            'total_calls' => $totalcalls,
            'success_count' => $successcount,
            'success_rate' => round($successrate, 2),
            'avg_response_time' => round($avgresponsetime, 3),
            'calls_by_action' => $actionstats,
        ];
    }

    /**
     * Cleanup old logs based on retention policy (section 6.2.2)
     * Should be called by scheduled task
     *
     * @return int Number of deleted records
     */
    public static function cleanup_old_logs() {
        global $DB;

        // Get retention days from config (default 90 days)
        $retentiondays = (int)get_config('local_exercise_suggestion', 'log_retention_days') ?: 90;
        $cutofftime = time() - ($retentiondays * 24 * 60 * 60);

        $count = $DB->count_records_select('local_exsug_logs', 'timecreated < :cutoff', ['cutoff' => $cutofftime]);
        
        if ($count > 0) {
            $DB->delete_records_select('local_exsug_logs', 'timecreated < :cutoff', ['cutoff' => $cutofftime]);
            debugging("Cleaned up {$count} old log records (older than {$retentiondays} days)", DEBUG_DEVELOPER);
        }

        return $count;
    }

    /**
     * Get slow API calls (response_time > threshold)
     *
     * @param float $threshold Response time threshold in seconds (default 5.0)
     * @param int $limit Maximum number of logs to retrieve
     * @return array Array of log records
     */
    public static function get_slow_api_calls($threshold = 5.0, $limit = 50) {
        global $DB;

        $sql = "SELECT *
                  FROM {local_exsug_logs}
                 WHERE response_time > :threshold
              ORDER BY response_time DESC";

        return $DB->get_records_sql($sql, ['threshold' => $threshold], 0, $limit);
    }
}
