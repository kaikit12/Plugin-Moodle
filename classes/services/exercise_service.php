<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

namespace local_exercise_suggestion\services;

use local_exercise_suggestion\api\client;
use local_exercise_suggestion\api\response_handler;

defined('MOODLE_INTERNAL') || die();

global $CFG;
require_once($CFG->dirroot . '/local/exercise_suggestion/classes/api/client.php');
require_once($CFG->dirroot . '/local/exercise_suggestion/classes/api/response_handler.php');

/**
 * Exercise Service - Business logic layer with caching theo report section 6.2
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class exercise_service {

    /** @var client API client instance */
    private $client;

    /** @var \cache Cache instance for API responses */
    private $cache;

    /** @var int Cache TTL for suggestions (default 3600s = 1 hour) */
    private $cache_ttl_suggestions;

    /** @var int Cache TTL for results (default 300s = 5 minutes) */
    private $cache_ttl_results;

    /**
     * Constructor
     */
    public function __construct() {
        $this->client = new client();
        
        // Initialize Moodle cache
        $this->cache = \cache::make('local_exercise_suggestion', 'apiresponses');
        
        // Load cache TTL from config (section 6.2.2)
        $this->cache_ttl_suggestions = (int)get_config('local_exercise_suggestion', 'cache_ttl_suggestions') ?: 3600;
        $this->cache_ttl_results = (int)get_config('local_exercise_suggestion', 'cache_ttl_results') ?: 300;
    }

    /**
     * Get exercise suggestions with cache (UC1 - section 4.1)
     * Cache key format: sug_{userid}_{courseid} (TTL: 3600s)
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param array $filters Optional filters (limit, difficulty_range)
     * @return array Suggestions data
     * @throws \moodle_exception
     */
    public function get_suggestions($userid, $courseid, $filters = []) {
        global $DB;

        // Validate required parameters
        if (empty($userid) || empty($courseid)) {
            throw new \moodle_exception('error:invalidparameters', 'local_exercise_suggestion');
        }

        // Check cache first (section 6.2.1.B)
        $cachekey = "sug_v2_{$userid}_{$courseid}";
        $cached = $this->cache->get($cachekey);
        
        if ($cached !== false) {
            // debugging('Cache HIT for suggestions: ' . $cachekey, DEBUG_DEVELOPER);
            return $cached;
        }

        // debugging('Cache MISS for suggestions: ' . $cachekey, DEBUG_DEVELOPER);

        // Call API
        $starttime = microtime(true);
        try {
            $response = $this->client->get_suggestions($userid, $courseid, $filters);
            $responsetime = round(microtime(true) - $starttime, 3);

            // Validate and process response
            $processeddata = response_handler::validate_suggestions_response($response);

            // Cache the result (TTL: 3600s)
            $this->cache->set($cachekey, $processeddata);

            // Log successful API call (section 6.2.1.A)
            $this->log_api_call($userid, $courseid, 'get_suggestions', '/api/suggestions', 200, $responsetime);

            return $processeddata;

        } catch (\Exception $e) {
            $responsetime = round(microtime(true) - $starttime, 3);
            
            // Log failed API call
            $this->log_api_call($userid, $courseid, 'get_suggestions', '/api/suggestions', 500, $responsetime, $e->getMessage());

            throw $e;
        }
    }

    /**
     * Get exercise details with cache (UC2 - section 4.2)
     * Cache key format: ex_{exercise_id} (TTL: 3600s)
     *
     * @param string $exerciseid Exercise ID
     * @param int $userid User ID (for logging)
     * @param int $courseid Course ID (for logging)
     * @return array Exercise data
     * @throws \moodle_exception
     */
    public function get_exercise($exerciseid, $userid, $courseid) {
        if (empty($exerciseid)) {
            throw new \moodle_exception('error:invalidparameters', 'local_exercise_suggestion');
        }

        // Check cache
        $safe_exercise_id = str_replace('-', '_', $exerciseid);
        $cachekey = "ex_v2_{$safe_exercise_id}";
        $cached = $this->cache->get($cachekey);
        
        if ($cached !== false) {
            // debugging('Cache HIT for exercise: ' . $cachekey, DEBUG_DEVELOPER);
            return $cached;
        }

        // debugging('Cache MISS for exercise: ' . $cachekey, DEBUG_DEVELOPER);

        // Call API
        $starttime = microtime(true);
        try {
            $response = $this->client->get_exercise($exerciseid);
            $responsetime = round(microtime(true) - $starttime, 3);

            // Validate and process response (section 6.2.3.B)
            $processeddata = response_handler::validate_exercise_response($response);

            // Cache the result (TTL: 3600s)
            $this->cache->set($cachekey, $processeddata);

            // Log successful API call
            $this->log_api_call($userid, $courseid, 'get_exercise', "/api/exercise/{$exerciseid}", 200, $responsetime);

            return $processeddata;

        } catch (\Exception $e) {
            $responsetime = round(microtime(true) - $starttime, 3);
            
            // Log failed API call
            $this->log_api_call($userid, $courseid, 'get_exercise', "/api/exercise/{$exerciseid}", 500, $responsetime, $e->getMessage());

            throw $e;
        }
    }

    /**
     * Submit exercise solution (UC3 - section 4.3)
     * No caching for submissions
     *
     * @param int $userid User ID
     * @param string $exerciseid Exercise ID
     * @param int $courseid Course ID
     * @param array $answers Student's answers
     * @param int $timespent Time spent in seconds
     * @param int $attemptnumber Attempt number
     * @return array Submission result
     * @throws \moodle_exception
     */
    public function submit_exercise($userid, $exerciseid, $courseid, $answers, $timespent, $attemptnumber = 1) {
        if (empty($userid) || empty($exerciseid) || empty($courseid)) {
            throw new \moodle_exception('error:invalidparameters', 'local_exercise_suggestion');
        }

        // Call API (no cache for submissions)
        $starttime = microtime(true);
        try {
            // Hit localhost:8000 (Fusion AI)
            $response = $this->client->submit_code_to_dsa_fusion($userid, $exerciseid, $answers["solution"] ?? "");
            $responsetime = round(microtime(true) - $starttime, 3);

            // Validate and process response (section 6.2.3.C)
            $processeddata = response_handler::validate_submit_response($response);
            
            // --- BUILD REAL RESULT FROM FUSION ---
            $score_val = isset($response['total_score']) ? (float)$response['total_score'] : 0;
            // Assuming fusion returns score out of 10, multiply by 10
            $percentage = $score_val <= 10 ? $score_val * 10 : $score_val;
            
            $first_eval = $response['file_evaluations'][0] ?? [];
            $ai_advice = $first_eval['ai_advice'] ?? '';
            $improvement = $first_eval['improvement'] ?? '';
            $criteria_scores = [];
            if (!empty($first_eval['criteria_scores']) && is_array($first_eval['criteria_scores'])) {
                foreach ($first_eval['criteria_scores'] as $criterion) {
                    $criteria_scores[] = [
                        'name' => clean_param($criterion['name'] ?? 'Criterion', PARAM_TEXT),
                        'earned' => isset($criterion['earned']) ? (float)$criterion['earned'] : 0,
                        'max' => isset($criterion['max']) ? (float)$criterion['max'] : 0,
                        'feedback' => clean_text($criterion['feedback'] ?? ''),
                        'evidence' => clean_text($criterion['evidence'] ?? '')
                    ];
                }
            }

            $is_placeholder_feedback = function($text) {
                if (empty($text)) {
                    return true;
                }
                return strpos($text, '[WARNING]') !== false
                    || strpos($text, 'Error') !== false
                    || strpos($text, 'Exception') !== false;
            };

            $test_results = [];
            if (!empty($first_eval['feedbacks'])) {
                foreach ($first_eval['feedbacks'] as $fb) {
                    $msg = isset($fb['message']) ? $fb['message'] : '';
                    if ($is_placeholder_feedback($msg)) {
                        if (!$is_placeholder_feedback($ai_advice)) {
                            $msg = $ai_advice;
                        } else {
                            $points = isset($fb['points']) ? (float)$fb['points'] : $percentage;
                            $msg = "Graded by source-code analysis: {$points}/100. Review the main algorithm, required cases, and edge cases.";
                        }
                    }
                    $test_results[] = [
                        'test' => isset($fb['testcase']) ? $fb['testcase'] : 'Test',
                        'passed' => $percentage >= 50 && isset($fb['status']) && $fb['status'] === 'AC',
                        'message' => $msg
                    ];
                }
            }

            $cloud_analysis_raw = isset($response['overall_ai_summary']) ? $response['overall_ai_summary'] : '';
            if ($is_placeholder_feedback($cloud_analysis_raw) && !$is_placeholder_feedback($ai_advice)) {
                $cloud_analysis = $ai_advice;
            } elseif ($is_placeholder_feedback($cloud_analysis_raw)) {
                if ($percentage >= 80) {
                    $cloud_analysis = 'Good result. You can still improve code organization and add more edge-case tests.';
                } elseif ($percentage >= 50) {
                    $cloud_analysis = 'Basic result. Review the algorithm, data structure choices, and test coverage.';
                } else {
                    $cloud_analysis = 'The submission does not meet the main requirements yet. Re-read the prompt, choose the right algorithm or data structure, then test simple cases first.';
                }
            } else {
                $cloud_analysis = $cloud_analysis_raw;
            }

            $real_result = [
                'submission_id' => $processeddata['submission_id'],
                'exercise_id' => $exerciseid,
                'status' => 'graded',
                'score' => $percentage,
                'max_score' => 100,
                'percentage' => $percentage,
                'fusion_score' => $percentage,
                'cloud_analysis' => $cloud_analysis,
                'feedback' => 'DSA Fusion graded the submission using source-code analysis and exercise criteria.',
                'improvement' => $improvement,
                'criteria_scores' => $criteria_scores,
                'test_results' => $test_results,
                'time_spent' => $timespent,
                'completed_at' => date('c')
            ];

            // Cache it so get_result() picks it up immediately without hitting Mock API!
            $safe_submission_id = str_replace('-', '_', $processeddata['submission_id']);
            $cachekey = "res_{$safe_submission_id}";
            $this->cache->set($cachekey, $real_result);
            // -------------------------------------

            // Log successful API call
            $this->log_api_call($userid, $courseid, 'submit', '/api/submit', 200, $responsetime);

            // Invalidate relevant caches after submission
            $suggestionkey = "sug_v2_{$userid}_{$courseid}";
            $this->cache->delete($suggestionkey);

            return $processeddata;

        } catch (\Exception $e) {
            $responsetime = round(microtime(true) - $starttime, 3);
            
            // Log failed API call
            $this->log_api_call($userid, $courseid, 'submit', '/api/submit', 500, $responsetime, $e->getMessage());

            throw $e;
        }
    }

    /**
     * Get submission result with cache (UC4 - section 4.4)
     * Cache key format: res_{submission_id} (TTL: 300s)
     *
     * @param string $submissionid Submission ID
     * @param int $userid User ID (for logging)
     * @param int $courseid Course ID (for logging)
     * @return array Result data
     * @throws \moodle_exception
     */
    public function get_result($submissionid, $userid, $courseid) {
        if (empty($submissionid)) {
            throw new \moodle_exception('error:invalidparameters', 'local_exercise_suggestion');
        }

        // Check cache with shorter TTL (300s = 5 minutes)
        $safe_submission_id = str_replace('-', '_', $submissionid);
        $cachekey = "res_{$safe_submission_id}";
        $cached = $this->cache->get($cachekey);
        
        if ($cached !== false && $cached['status'] === 'graded') {
            // Only use cache if status is 'graded' (final result)
            // // debugging('Cache HIT for result: ' . $cachekey, DEBUG_DEVELOPER);
            return $cached;
        }

        // // debugging('Cache MISS for result: ' . $cachekey, DEBUG_DEVELOPER);

        // Call API
        $starttime = microtime(true);
        try {
            $response = $this->client->get_result($submissionid);
            $responsetime = round(microtime(true) - $starttime, 3);

            // Validate and process response (section 6.2.3.D)
            $processeddata = response_handler::validate_result_response($response);

            // Cache only if graded (TTL: 300s)
            if ($processeddata['status'] === 'graded') {
                $this->cache->set($cachekey, $processeddata);
            }

            // Log successful API call
            $this->log_api_call($userid, $courseid, 'get_result', "/api/result/{$submissionid}", 200, $responsetime);

            return $processeddata;

        } catch (\Exception $e) {
            $responsetime = round(microtime(true) - $starttime, 3);
            
            // Log failed API call
            $this->log_api_call($userid, $courseid, 'get_result', "/api/result/{$submissionid}", 500, $responsetime, $e->getMessage());

            throw $e;
        }
    }

    /**
     * Clear all cache for a user in a course
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     */
    public function clear_user_cache($userid, $courseid) {
        $cachekey = "sug_{$userid}_{$courseid}";
        $this->cache->delete($cachekey);
        // debugging("Cleared cache for user {$userid} in course {$courseid}", DEBUG_DEVELOPER);
    }

    /**
     * Log API call to database (section 6.2.1.A)
     *
     * @param int $userid User ID
     * @param int $courseid Course ID
     * @param string $action Action name (get_suggestions, get_exercise, submit, get_result)
     * @param string $apiendpoint API endpoint
     * @param int $httpstatus HTTP status code
     * @param float $responsetime Response time in seconds
     * @param string $errormessage Error message (if any)
     */
    private function log_api_call($userid, $courseid, $action, $apiendpoint, $httpstatus, $responsetime, $errormessage = null) {
        global $DB, $USER;

        $logrecord = new \stdClass();
        $logrecord->userid = isset($USER->id) ? $USER->id : 0; // Moodle integer user ID
        $logrecord->courseid = $courseid;
        $logrecord->action = $action;
        $logrecord->api_endpoint = $apiendpoint;
        $logrecord->http_status = $httpstatus;
        $logrecord->response_time = $responsetime;
        $logrecord->error_message = $errormessage;
        $logrecord->timecreated = time();

        try {
            $DB->insert_record('local_exsug_logs', $logrecord);
        } catch (\Exception $e) {
            // Don't throw exception on logging failure
            // debugging('Failed to log API call: ' . $e->getMessage(), DEBUG_DEVELOPER);
        }
    }
}
