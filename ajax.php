<?php

define('AJAX_SCRIPT', true);

require_once('C:/xampp/htdocs/moodle/config.php');
require_once($CFG->dirroot . '/local/exercise_suggestion/classes/services/exercise_service.php');

use local_exercise_suggestion\services\exercise_service;

// 1. Chỉ chấp nhận phương thức POST (Bảo mật cơ bản)
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    die();
}

try {
    // 2. Kiểm tra Moodle Session & bảo mật CSRF (Sesskey)
    require_login();
    require_sesskey();

    global $USER;
    $username = $USER->username; // Sử dụng username (MSSV) để gọi API ngoài
    $moodle_userid = $USER->id;  // ID nội bộ của Moodle để lấy danh sách khóa học
    $action = optional_param('action', 'course_suggestions', PARAM_ALPHAEXT);
    $limit = optional_param('limit', 10, PARAM_INT);
    
    $service = new exercise_service();
    $filters = ['limit' => $limit];

    if ($action === 'get_dashboard_summary') {
        // Lấy danh sách khóa học của sinh viên
        $courses = enrol_get_users_courses($moodle_userid, true, 'id, fullname');
        $dashboard_data = [];

        foreach ($courses as $course) {
            $course_data = $service->get_suggestions($username, $course->id, $filters);
            if (!empty($course_data['suggestions'])) {
                foreach ($course_data['suggestions'] as &$suggestion) {
                    $suggestion['view_url'] = (new moodle_url('/local/exercise_suggestion/index.php', [
                        'courseid' => $course->id,
                        'action' => 'view',
                        'exerciseid' => $suggestion['id']
                    ]))->out(false);
                }
                
                $dashboard_data[] = [
                    'course_id' => $course->id,
                    'course_name' => $course->fullname,
                    'suggestions' => $course_data['suggestions']
                ];
            }
        }

        $response = [
            'status' => 'success',
            'data' => [
                'courses' => $dashboard_data,
                'has_courses' => count($dashboard_data) > 0
            ]
        ];

    } elseif ($action === 'get_exercise_details') {
        $exerciseid = required_param('exerciseid', PARAM_TEXT);
        $courseid = required_param('courseid', PARAM_INT);
        $data = $service->get_exercise($exerciseid, $username, $courseid);
        
        $response = [
            'status' => 'success',
            'data' => $data
        ];
    } elseif ($action === 'submit') {
        $exerciseid = required_param('exerciseid', PARAM_TEXT);
        $courseid = required_param('courseid', PARAM_INT);
        // Nhận code từ frontend gửi lên
        $code_content = required_param('solution', PARAM_RAW); 
        $timespent = optional_param('timespent', 0, PARAM_INT);
        $answers = ['solution' => $code_content];
        
        $data = $service->submit_exercise($username, $exerciseid, $courseid, $answers, $timespent);
        
        $response = [
            'status' => 'success',
            'data' => $data
        ];
    } else {
        $courseid = required_param('courseid', PARAM_INT);
        $data = $service->get_suggestions($username, $courseid, $filters);

        if (!empty($data['suggestions'])) {
            foreach ($data['suggestions'] as &$suggestion) {
                $suggestion['view_url'] = (new moodle_url('/local/exercise_suggestion/index.php', [
                    'courseid' => $courseid,
                    'action' => 'view',
                    'exerciseid' => $suggestion['id']
                ]))->out(false);
            }
        }

        $response = [
            'status' => 'success',
            'data' => [
                'course_id' => $courseid,
                'suggestions' => $data['suggestions'] ?? [],
                'metadata' => $data['metadata'] ?? []
            ]
        ];
    }

    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($response);
    die();

} catch (\moodle_exception $e) {
    http_response_code(400);
    echo json_encode(['status' => 'error', 'message' => $e->getMessage()]);
    die();
} catch (\Exception $e) {
    http_response_code(500);
    echo json_encode(['status' => 'error', 'message' => 'Lỗi kết nối đến hệ thống AI: ' . $e->getMessage()]);
    die();
}
