<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

namespace local_exercise_suggestion\api;

defined('MOODLE_INTERNAL') || die();

/**
 * Response handler for processing API responses from exercise suggestion system
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class response_handler {

    /**
     * Validate and process suggestions response from POST /api/suggestions
     *
     * @param array $response Raw API response
     * @return array Processed suggestions data
     * @throws \moodle_exception If response format is invalid
     */
    public static function validate_suggestions_response($response) {
        // Validate required fields according to report section 6.2.3.A
        if (!isset($response['suggestions']) || !is_array($response['suggestions'])) {
            throw new \moodle_exception('invalid_api_response', 'local_exercise_suggestion', '', 
                'Missing or invalid suggestions field');
        }

        $suggestions = [];
        foreach ($response['suggestions'] as $suggestion) {
            // Validate required fields for each suggestion
            $requiredfields = ['id', 'title', 'difficulty', 'description', 'estimated_time'];
            foreach ($requiredfields as $field) {
                if (!isset($suggestion[$field])) {
                    debugging("Missing required field '{$field}' in suggestion", DEBUG_DEVELOPER);
                    continue 2; // Skip this suggestion
                }
            }

            // Clean and sanitize data
            $suggestions[] = [
                'id' => clean_param($suggestion['id'], PARAM_ALPHANUMEXT),
                'title' => clean_param($suggestion['title'], PARAM_TEXT),
                'difficulty' => clean_param($suggestion['difficulty'], PARAM_TEXT),
                'description' => clean_text($suggestion['description']),
                'estimated_time' => (int)$suggestion['estimated_time'],
                'topics' => isset($suggestion['topics']) ? self::clean_array($suggestion['topics']) : [],
                'prerequisite_ids' => isset($suggestion['prerequisite_ids']) ? self::clean_array($suggestion['prerequisite_ids']) : []
            ];
        }

        return [
            'user_id' => isset($response['user_id']) ? (int)$response['user_id'] : 0,
            'user_name' => isset($response['user_name']) ? clean_param($response['user_name'], PARAM_TEXT) : '',
            'course_id' => isset($response['course_id']) ? (int)$response['course_id'] : 0,
            'course_name' => isset($response['course_name']) ? clean_param($response['course_name'], PARAM_TEXT) : '',
            'suggestions' => $suggestions,
            'metadata' => isset($response['metadata']) ? $response['metadata'] : []
        ];
    }

    /**
     * Validate and process exercise details response from GET /api/exercise/{id}
     *
     * @param array $response Raw API response
     * @return array Processed exercise data
     * @throws \moodle_exception If response format is invalid
     */
    public static function validate_exercise_response($response) {
        // Handle response wrapper (API returns {"success":true,"exercise":{...}})
        if (isset($response['success']) && isset($response['exercise'])) {
            $response = $response['exercise'];
        }

        // Validate required fields - using actual mock API structure
        $requiredfields = ['id', 'title', 'difficulty', 'description', 'instructions', 'estimated_time'];
        foreach ($requiredfields as $field) {
            if (!isset($response[$field])) {
                throw new \moodle_exception('invalid_api_response', 'local_exercise_suggestion', '', 
                    "Missing required field: {$field}");
            }
        }

        // Clean and sanitize exercise data
        $exercise = [
            'id' => clean_param($response['id'], PARAM_ALPHANUMEXT),
            'title' => clean_param($response['title'], PARAM_TEXT),
            'difficulty' => clean_param($response['difficulty'], PARAM_TEXT),
            'description' => clean_text($response['description']),
            'instructions' => clean_text($response['instructions']),
            'estimated_time' => (int)$response['estimated_time'],
            'starter_code' => isset($response['starter_code']) ? $response['starter_code'] : '', // Keep raw code
            'test_cases' => isset($response['test_cases']) && is_array($response['test_cases']) ? $response['test_cases'] : [],
            'hints' => isset($response['hints']) && is_array($response['hints']) ? $response['hints'] : [],
            'tags' => isset($response['tags']) && is_array($response['tags']) ? $response['tags'] : []
        ];

        return $exercise;
    }

    /**
     * Validate and process submit response from POST /api/submit
     *
     * @param array $response Raw API response
     * @return array Processed submission data
     * @throws \moodle_exception If response format is invalid
     */
    public static function validate_submit_response($response) {
        // Validate required fields according to report section 6.2.3.C
        $requiredfields = ['submission_id', 'status'];
        foreach ($requiredfields as $field) {
            if (!isset($response[$field])) {
                throw new \moodle_exception('invalid_api_response', 'local_exercise_suggestion', '', 
                    "Missing required field: {$field}");
            }
        }

        return [
            'submission_id' => clean_param($response['submission_id'], PARAM_ALPHANUMEXT),
            'status' => clean_param($response['status'], PARAM_TEXT),
            'message' => clean_text($response['overall_ai_summary'] ?? 'Đã nộp thuật toán thành công'),
            'estimated_grading_time' => isset($response['estimated_grading_time']) ? (int)$response['estimated_grading_time'] : 0,
            'submitted_at' => isset($response['submitted_at']) ? $response['submitted_at'] : date('c')
        ];
    }

    /**
     * Validate and process result response from GET /api/result/{submission_id}
     *
     * @param array $response Raw API response
     * @return array Processed result data
     * @throws \moodle_exception If response format is invalid
     */
    public static function validate_result_response($response) {
        // Extract result from response wrapper if needed
        if (isset($response['result'])) {
            $response = $response['result'];
        }
        
        // Validate required fields according to report section 6.2.3.D
        $requiredfields = ['submission_id', 'exercise_id', 'status'];
        foreach ($requiredfields as $field) {
            if (!isset($response[$field])) {
                throw new \moodle_exception('invalid_api_response', 'local_exercise_suggestion', '', 
                    "Missing required field: {$field}");
            }
        }

        $result = [
            'submission_id' => clean_param($response['submission_id'], PARAM_ALPHANUMEXT),
            'exercise_id' => clean_param($response['exercise_id'], PARAM_ALPHANUMEXT),
            'status' => clean_param($response['status'], PARAM_TEXT),
            'score' => isset($response['score']) ? (float)$response['score'] : 0.0,
            'max_score' => isset($response['max_score']) ? (float)$response['max_score'] : 0.0,
            'percentage' => isset($response['percentage']) ? (int)$response['percentage'] : 0,
            'fusion_score' => isset($response['fusion_score']) ? (float)$response['fusion_score'] : 0.0,
            'cloud_analysis' => isset($response['cloud_analysis']) ? clean_text($response['cloud_analysis']) : '',
            'feedback' => [],
            'correct_answers' => [],
            'time_spent' => isset($response['time_spent']) ? (int)$response['time_spent'] : 0,
            'submitted_at' => isset($response['submitted_at']) ? $response['submitted_at'] : '',
            'graded_at' => isset($response['graded_at']) ? $response['graded_at'] : ''
        ];

        // Process feedback (can be string or array)
        if (isset($response['feedback'])) {
            if (is_string($response['feedback'])) {
                $result['feedback'] = [
                    'overall' => clean_text($response['feedback']),
                    'questions' => []
                ];
            } else if (is_array($response['feedback'])) {
                $result['feedback'] = [
                    'overall' => isset($response['feedback']['overall']) ? clean_text($response['feedback']['overall']) : '',
                    'questions' => isset($response['feedback']['questions']) ? $response['feedback']['questions'] : []
                ];
            }
        }

        // Process correct answers (keep raw code)
        if (isset($response['correct_answers']) && is_array($response['correct_answers'])) {
            $result['correct_answers'] = $response['correct_answers'];
        }

        // Process test results
        if (isset($response['test_results']) && is_array($response['test_results'])) {
            $result['test_results'] = $response['test_results'];
        } else {
            $result['test_results'] = [];
        }

        return $result;
    }

    /**
     * Handle API errors and map to user-friendly messages
     *
     * @param int $httpcode HTTP status code
     * @param string $rawmessage Raw error message from API
     * @return array Error details
     */
    public static function handle_api_error($httpcode, $rawmessage = '') {
        $errorcodes = [
            400 => ['code' => 'bad_request', 'message' => 'Dá»¯ liá»‡u gá»­i lĂªn khĂ´ng há»£p lá»‡'],
            401 => ['code' => 'unauthorized', 'message' => 'API key khĂ´ng há»£p lá»‡ hoáº·c Ä‘Ă£ háº¿t háº¡n'],
            404 => ['code' => 'not_found', 'message' => 'KhĂ´ng tĂ¬m tháº¥y tĂ i nguyĂªn yĂªu cáº§u'],
            429 => ['code' => 'rate_limit', 'message' => 'VÆ°á»£t quĂ¡ giá»›i háº¡n sá»‘ lÆ°á»£ng request. Vui lĂ²ng thá»­ láº¡i sau'],
            500 => ['code' => 'server_error', 'message' => 'Lá»—i mĂ¡y chá»§ API. Vui lĂ²ng thá»­ láº¡i sau'],
            503 => ['code' => 'unavailable', 'message' => 'Dá»‹ch vá»¥ API táº¡m thá»i khĂ´ng kháº£ dá»¥ng']
        ];

        $error = isset($errorcodes[$httpcode]) ? $errorcodes[$httpcode] : 
            ['code' => 'unknown_error', 'message' => 'Lá»—i khĂ´ng xĂ¡c Ä‘á»‹nh'];

        $error['http_code'] = $httpcode;
        $error['raw_message'] = $rawmessage;
        $error['timestamp'] = time();

        return $error;
    }

    /**
     * Clean array of strings
     *
     * @param array $array Raw array
     * @return array Cleaned array
     */
    private static function clean_array($array) {
        if (!is_array($array)) {
            return [];
        }

        $cleaned = [];
        foreach ($array as $item) {
            if (is_string($item)) {
                $cleaneditem = clean_param($item, PARAM_TEXT);
                if (!empty($cleaneditem)) {
                    $cleaned[] = $cleaneditem;
                }
            }
        }

        return $cleaned;
    }
}

