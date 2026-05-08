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
 * API Client class for communicating with third-party exercise suggestion system
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */
class client {
    
    /** @var string API base URL */
    private $apiurl;
    
    /** @var string API authentication key */
    private $apikey;
    
    /** @var int Request timeout in seconds */
    private $timeout;
    
    /** @var array Default headers for API requests */
    private $defaultheaders;

    /** @var int Number of retry attempts */
    private $retrycount;
    
    /**
     * Constructor
     *
     * @param string|null $apiurl API base URL (uses config if null)
     * @param string|null $apikey API key (uses config if null)
     * @param int|null $timeout Request timeout in seconds (uses config if null)
     * @param int|null $retrycount Number of retry attempts (uses config if null)
     */
    public function __construct($apiurl = null, $apikey = null, $timeout = null, $retrycount = null) {
        $this->apiurl = 'http://localhost:8080';
        $this->apikey = $apikey ?: get_config('local_exercise_suggestion', 'api_key');
        $this->timeout = $timeout ?: ((int)get_config('local_exercise_suggestion', 'timeout') ?: 10);
        $this->retrycount = $retrycount !== null ? $retrycount : ((int)get_config('local_exercise_suggestion', 'retry_count') ?: 1);
        
        $this->defaultheaders = [
            'Content-Type: application/json',
            'Accept: application/json',
            'User-Agent: Moodle-Exercise-Suggestion-Plugin/1.0.0'
        ];
        
        // Add authorization header if API key is available
        if (!empty($this->apikey)) {
            $this->defaultheaders[] = 'Authorization: Bearer ' . $this->apikey;
        }
    }

    /**
     * Send HTTP request to API endpoint with retry logic
     *
     * @param string $endpoint API endpoint (without base URL)
     * @param string $method HTTP method (GET, POST, PUT, DELETE)
     * @param array $data Request payload data
     * @param array $headers Additional headers
     * @return array Decoded JSON response
     * @throws \moodle_exception If request fails after all retries
     */
    public function send_request($endpoint, $method = 'GET', $data = [], $headers = []) {
        // Validate inputs
        if (empty($this->apiurl)) {
            throw new \moodle_exception('error:apinotconfigured', 'local_exercise_suggestion');
        }
        
        $lastexception = null;
        $attempts = $this->retrycount + 1; // Initial attempt + retries
        
        // Retry loop
        for ($attempt = 1; $attempt <= $attempts; $attempt++) {
            try {
                return $this->execute_request($endpoint, $method, $data, $headers, $attempt);
            } catch (\Exception $e) {
                $lastexception = $e;
                
                // Don't retry on HTTP 4xx errors (client errors)
                if (strpos($e->getMessage(), 'HTTP 4') !== false) {
                    throw $e;
                }
                
                // If this was the last attempt, throw the exception
                if ($attempt >= $attempts) {
                    throw $e;
                }
                
                // Wait before retry (exponential backoff)
                $waittime = min(pow(2, $attempt - 1), 8); // Max 8 seconds
                sleep($waittime);
                
                debugging("Retry attempt {$attempt}/{$this->retrycount} for {$endpoint}", DEBUG_DEVELOPER);
            }
        }
        
        // Should never reach here, but just in case
        throw $lastexception ?: new \moodle_exception('error:apierror', 'local_exercise_suggestion', '', 'Unknown error');
    }
    
    /**
     * Execute a single HTTP request (used internally by send_request)
     *
     * @param string $endpoint API endpoint
     * @param string $method HTTP method
     * @param array $data Request data
     * @param array $headers Additional headers
     * @param int $attempt Current attempt number
     * @return array Decoded JSON response
     * @throws \moodle_exception If request fails
     */
    private function execute_request($endpoint, $method, $data, $headers, $attempt) {
        
        // Build complete URL
        $url = rtrim($this->apiurl, '/') . '/' . ltrim($endpoint, '/');
        
        // Merge headers
        $requestheaders = array_merge($this->defaultheaders, $headers);
        
        // Initialize cURL
        $curl = curl_init();
        if (!$curl) {
            throw new \moodle_exception('curl_init_failed', 'local_exercise_suggestion');
        }
        
        // Set basic cURL options
        curl_setopt_array($curl, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_CONNECTTIMEOUT => 10,
            CURLOPT_HTTPHEADER => $requestheaders,
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS => 3,
            CURLOPT_USERAGENT => 'Moodle-Exercise-Suggestion-Plugin/1.0.0'
        ]);
        
        // Configure method-specific options
        $method = strtoupper($method);
        switch ($method) {
            case 'POST':
                curl_setopt($curl, CURLOPT_POST, true);
                if (!empty($data)) {
                    curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($data));
                }
                break;
                
            case 'PUT':
                curl_setopt($curl, CURLOPT_CUSTOMREQUEST, 'PUT');
                if (!empty($data)) {
                    curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($data));
                }
                break;
                
            case 'DELETE':
                curl_setopt($curl, CURLOPT_CUSTOMREQUEST, 'DELETE');
                if (!empty($data)) {
                    curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($data));
                }
                break;
                
            case 'PATCH':
                curl_setopt($curl, CURLOPT_CUSTOMREQUEST, 'PATCH');
                if (!empty($data)) {
                    curl_setopt($curl, CURLOPT_POSTFIELDS, json_encode($data));
                }
                break;
                
            default: // GET and other methods
                if (!empty($data)) {
                    $url .= '?' . http_build_query($data);
                    curl_setopt($curl, CURLOPT_URL, $url);
                }
        }
        
        // Execute request
        $response = curl_exec($curl);
        $httpcode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        $curlinfo = curl_getinfo($curl);
        $curlerror = curl_error($curl);
        curl_close($curl);
        
        // Log request for debugging (only in debug mode)
        if (debugging('', DEBUG_DEVELOPER)) {
            $logdata = [
                'url' => $url,
                'method' => $method,
                'headers' => $requestheaders,
                'data' => $data,
                'http_code' => $httpcode,
                'curl_info' => $curlinfo
            ];
            // mtrace('Exercise Suggestion API Request: ' . json_encode($logdata));
        }
        
        // Handle cURL errors
        if ($response === false || !empty($curlerror)) {
            $errormsg = !empty($curlerror) ? $curlerror : 'Unknown cURL error';
            throw new \moodle_exception('api_connection_error', 'local_exercise_suggestion', '', $errormsg);
        }
        
        // Handle HTTP errors
        if ($httpcode >= 400) {
            $errordetail = ['http_code' => $httpcode, 'response' => $response];
            throw new \moodle_exception('api_http_error', 'local_exercise_suggestion', '', $errordetail);
        }
        
        // Decode JSON response
        $decodedresponse = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \moodle_exception('api_json_decode_error', 'local_exercise_suggestion', '', json_last_error_msg());
        }
        
        return $decodedresponse;
    }

    /**
     * Test API connection
     *
     * @return array Connection test result
     */
    public function test_connection() {
        try {
            $response = $this->send_request('/health', 'GET');
            return [
                'success' => true,
                'message' => 'Connection successful',
                'response' => $response
            ];
        } catch (\Exception $e) {
            return [
                'success' => false,
                'message' => 'Connection failed',
                'error' => $e->getMessage()
            ];
        }
    }

    /**
     * Get exercise suggestions from API (UC1)
     * Endpoint: POST /api/suggestions
     *
     * @param int $userid Moodle user ID
     * @param int $courseid Moodle course ID
     * @param array $filters Additional filters (limit, difficulty_range, etc.)
     * @return array API response with suggestions
     * @throws \moodle_exception If request fails
     */
    public function get_suggestions($userid, $courseid, $filters = []) {
        $data = [
            'user_id'          => $userid,
            'course_id'        => $courseid,
            'exam_code'        => $filters['exam_code'] ?? null,
            'limit'            => $filters['limit'] ?? 10,
            'difficulty_range' => $filters['difficulty_range'] ?? []
        ];
        
        return $this->send_request('/api/suggestions', 'POST', $data);
    }

    /**
     * Get exercise details from API (UC2)
     * Endpoint: GET /api/exercise/{id}
     *
     * @param string $exerciseid Exercise ID from external system
     * @return array API response with exercise details
     * @throws \moodle_exception If request fails
     */
    public function get_exercise($exerciseid) {
        return $this->send_request('/api/exercise/' . urlencode($exerciseid), 'GET');
    }

    /**
     * Submit exercise solution to API (UC3)
     * Endpoint: POST /api/submit
     *
     * @param int $userid Moodle user ID
     * @param string $exerciseid Exercise ID
     * @param int $courseid Moodle course ID
     * @param array $answers Student's answers
     * @param int $timespent Time spent in seconds
     * @param int $attemptnumber Attempt number (default 1)
     * @return array API response with submission_id
     * @throws \moodle_exception If request fails
     */
    public function submit_exercise($userid, $exerciseid, $courseid, $answers, $timespent, $attemptnumber = 1) {
        $data = [
            'user_id' => $userid,
            'exercise_id' => $exerciseid,
            'course_id' => $courseid,
            'answers' => $answers,
            'time_spent' => $timespent,
            'attempt_number' => $attemptnumber
        ];
        
        return $this->send_request('/api/submit', 'POST', $data);
    }

    /**
     * Get exercise result from API (UC4)
     * Endpoint: GET /api/result/{submission_id}
     *
     * @param string $submissionid Submission ID from external system
     * @return array API response with result and feedback
     * @throws \moodle_exception If request fails
     */
    public function get_result($submissionid) {
        return $this->send_request('/api/result/' . urlencode($submissionid), 'GET');
    }

    /**
     * Submit code to DSA Fusion Auto-Grader
     * Endpoint: POST http://127.0.0.1:8000/submissions/
     */
    public function submit_code_to_dsa_fusion($userid, $exerciseid, $code_content) {
        $url = get_config('local_exercise_suggestion', 'fusion_url') ?: "http://127.0.0.1:8000/submissions/";
        
        $temp_dir = make_temp_directory("exsug_submissions");
        $file_name = "submission_{$userid}_{$exerciseid}.py";
        $file_path = $temp_dir . "/" . $file_name;
        
        file_put_contents($file_path, $code_content);
        
        $cfile = new \CURLFile($file_path, "text/x-python", $file_name);
        
        $idempotency_key = md5((string)$userid . $exerciseid . time());
        
        $post_data = [
            "student_id" => (string)$userid,
            "student_name" => "SV_" . $userid,
            "idempotency_key" => $idempotency_key,
            "files" => $cfile
        ];
        
        $curl = curl_init();
        curl_setopt_array($curl, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $post_data,
            CURLOPT_TIMEOUT => 60 
        ]);
        
        $response = curl_exec($curl);
        $httpcode = curl_getinfo($curl, CURLINFO_HTTP_CODE);
        $curlerror = curl_error($curl);
        curl_close($curl);
        
        @unlink($file_path);
        
        if ($response === false || !empty($curlerror)) {
             throw new \moodle_exception("api_http_error", "local_exercise_suggestion", "", $curlerror);
        }
        
        if ($httpcode >= 400) {
             throw new \moodle_exception("api_http_error", "local_exercise_suggestion", "", "HTTP " . $httpcode . ": " . $response);
        }
        
        $decodedresponse = json_decode($response, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            throw new \moodle_exception("api_json_decode_error", "local_exercise_suggestion", "", json_last_error_msg());
        }
        
        return $decodedresponse;
    }
}




