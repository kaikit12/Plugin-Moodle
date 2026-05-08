<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

/**
 * Exercise Suggestion Plugin - Main Entry Point
 * Handles UC1-UC4 flows from report section 4
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

$moodleconfig = __DIR__ . '/../../config.php';
if (!file_exists($moodleconfig)) {
    $moodleconfig = 'C:/xampp/htdocs/moodle/config.php';
}
require_once($moodleconfig);
require_once($CFG->dirroot . '/local/exercise_suggestion/classes/services/exercise_service.php');
require_once($CFG->dirroot . '/local/exercise_suggestion/classes/models/progress_tracker.php');

use local_exercise_suggestion\services\exercise_service;
use local_exercise_suggestion\models\progress_tracker;

function exsug_completion_pref_key($courseid) {
    return 'local_exercise_suggestion_completed_' . (int)$courseid;
}

function exsug_get_completed_exercises($userid, $courseid) {
    $raw = get_user_preferences(exsug_completion_pref_key($courseid), '[]', $userid);
    $items = json_decode($raw, true);

    return is_array($items) ? array_values(array_unique(array_filter($items))) : [];
}

function exsug_mark_completed($userid, $courseid, $exerciseid) {
    if (empty($exerciseid)) {
        return;
    }

    $completed = exsug_get_completed_exercises($userid, $courseid);
    $completed[] = $exerciseid;
    $completed = array_values(array_unique($completed));
    set_user_preference(exsug_completion_pref_key($courseid), json_encode($completed), $userid);
}

// Get parameters
$courseid = optional_param('courseid', 0, PARAM_INT);
$action = optional_param('action', 'courses', PARAM_ALPHA);
$exerciseid = optional_param('exerciseid', '', PARAM_TEXT);
$submissionid = optional_param('submissionid', '', PARAM_TEXT);

// If no courseid, show course list or use site course
if (!$courseid) {
    if ($action === 'courses') {
        handle_courses_list();
        exit;
    } else {
        // Use site course (id=1) if no course specified
        $courseid = 1;
    }
}

// Get course (allow site course for testing)
$course = $DB->get_record('course', ['id' => $courseid]);
if (!$course) {
    print_error('courseidnotfound', 'error');
}

// Login required (allow guests for testing)
require_login($course, false, null, false, true);

// Context and capability checks
$context = context_course::instance($courseid);
require_capability('local/exercise_suggestion:view', $context);

// Set up page
$PAGE->set_url('/local/exercise_suggestion/index.php', ['courseid' => $courseid, 'action' => $action]);
$PAGE->set_context($context);
$PAGE->set_course($course);
$PAGE->set_pagelayout('incourse');
$PAGE->set_title(get_string('pluginname', 'local_exercise_suggestion'));
$PAGE->set_heading($course->fullname);

// Initialize service
$service = new exercise_service();

// Handle actions
switch ($action) {
    case 'list':
        // UC1: List exercise suggestions
        handle_list_action($service, $courseid, $context);
        break;

    case 'view':
        // UC2: View exercise details
        handle_view_action($service, $exerciseid, $courseid, $context);
        break;

    case 'submit':
        // UC3: Submit exercise solution
        handle_submit_action($service, $exerciseid, $courseid, $context);
        break;

    case 'result':
        // UC4: View submission result
        handle_result_action($service, $submissionid, $exerciseid, $courseid, $context);
        break;

    default:
        print_error('invalidaction', 'local_exercise_suggestion');
}

/**
 * Handle list action (UC1 - section 4.1)
 */
function handle_list_action($service, $courseid, $context) {
    global $USER, $OUTPUT, $PAGE;

    $PAGE->navbar->add(get_string('exercises', 'local_exercise_suggestion'));

    echo $OUTPUT->header();
    echo $OUTPUT->heading(get_string('exercises', 'local_exercise_suggestion'));

    try {
        // Get filters from request
        $limit = optional_param('limit', 10, PARAM_INT);
        $difficulty = optional_param('difficulty', '', PARAM_TEXT);

        $filters = ['limit' => $limit];
        if (!empty($difficulty)) {
            $filters['difficulty_range'] = [$difficulty];
        }

        // Get suggestions from API with cache
        $data = $service->get_suggestions($USER->username, $courseid, $filters);
        $completed = exsug_get_completed_exercises($USER->id, $courseid);
        $completedmap = array_flip($completed);
        $suggestions = array_map(function($suggestion) use ($courseid, $completedmap) {
            $suggestion['view_url'] = (new moodle_url('/local/exercise_suggestion/index.php', [
                'courseid' => $courseid,
                'action' => 'view',
                'exerciseid' => $suggestion['id']
            ]))->out(false);
            $suggestion['is_completed'] = isset($completedmap[$suggestion['id']]);
            return $suggestion;
        }, $data['suggestions']);

        $total = count($suggestions);
        $completedcount = 0;
        foreach ($suggestions as $suggestion) {
            if (!empty($suggestion['is_completed'])) {
                $completedcount++;
            }
        }
        $completionpercent = $total > 0 ? (int)round(($completedcount / $total) * 100) : 0;
        $metadata = $data['metadata'] ?? [];
        $metadata['total_count'] = $total;
        $metadata['completed_count'] = $completedcount;
        $metadata['completion_percent'] = $completionpercent;

        // Render suggestions list
        $templatecontext = [
            'course_id' => $courseid,
            'course_name' => $data['course_name'] ?? '',
            'user_name' => $data['user_name'] ?? '',
            'suggestions' => $suggestions,
            'metadata' => $metadata,
            'sesskey' => sesskey(),
            'ajax_url' => (new moodle_url('/local/exercise_suggestion/ajax.php'))->out(false)
        ];

        echo $OUTPUT->render_from_template('local_exercise_suggestion/suggestions_list', $templatecontext);

    } catch (Exception $e) {
        echo $OUTPUT->notification(get_string('error:apierror', 'local_exercise_suggestion') . ': ' . $e->getMessage(), 'error');
    }

    echo $OUTPUT->footer();
}

/**
 * Handle view action (UC2 - section 4.2)
 */
function handle_view_action($service, $exerciseid, $courseid, $context) {
    global $USER, $OUTPUT, $PAGE;

    if (empty($exerciseid)) {
        print_error('missingexerciseid', 'local_exercise_suggestion');
    }

    $PAGE->navbar->add(get_string('exercises', 'local_exercise_suggestion'), 
        new moodle_url('/local/exercise_suggestion/index.php', ['courseid' => $courseid, 'action' => 'list']));
    $PAGE->navbar->add(get_string('exercisedetails', 'local_exercise_suggestion'));

    echo $OUTPUT->header();

    try {
        // Get exercise from API with cache
        $exercise = $service->get_exercise($exerciseid, $USER->username, $courseid);

        // Mark as in progress (temporarily disabled - table schema mismatch)
        // progress_tracker::mark_in_progress($USER->id, $courseid, $exerciseid);

        // Render exercise view
        $templatecontext = [
            'course_id' => $courseid,
            'exercise' => $exercise,
            'submit_url' => (new moodle_url('/local/exercise_suggestion/index.php', [
                'courseid' => $courseid,
                'action' => 'submit',
                'exerciseid' => $exerciseid
            ]))->out(false),
            'back_url' => isset($_SERVER['HTTP_REFERER']) ? $_SERVER['HTTP_REFERER'] : (new moodle_url('/my/'))->out(false),
            'sesskey' => sesskey()
        ];

        echo $OUTPUT->render_from_template('local_exercise_suggestion/exercise_view', $templatecontext);

    } catch (Exception $e) {
        // Debug output
        if (debugging('', DEBUG_DEVELOPER)) {
            echo '<pre>Exception: ' . htmlspecialchars($e->getMessage()) . "\n";
            echo 'File: ' . $e->getFile() . ':' . $e->getLine() . "\n";
            echo 'Trace: ' . htmlspecialchars($e->getTraceAsString()) . '</pre>';
        }
        echo $OUTPUT->notification(get_string('error:apierror', 'local_exercise_suggestion') . ': ' . $e->getMessage(), 'error');
    }

    echo $OUTPUT->footer();
}

/**
 * Handle submit action (UC3 - section 4.3)
 */
function handle_submit_action($service, $exerciseid, $courseid, $context) {
    global $USER, $OUTPUT, $PAGE;

    // Must be POST request
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        print_error('invalidrequest', 'local_exercise_suggestion');
    }

    // Validate sesskey
    require_sesskey();

    // Check submit capability (commented out for testing)
    // require_capability('local/exercise_suggestion:submit', $context);

    if (empty($exerciseid)) {
        print_error('missingexerciseid', 'local_exercise_suggestion');
    }

    try {
        // Get answers from POST data
        $answers = required_param_array('answers', PARAM_RAW);
        $timespent = required_param('time_spent', PARAM_INT);
        $attemptnumber = optional_param('attempt_number', 1, PARAM_INT);

        // Submit to API
        $result = $service->submit_exercise($USER->username, $exerciseid, $courseid, $answers, $timespent, $attemptnumber);
        exsug_mark_completed($USER->id, $courseid, $exerciseid);

        // Mark as submitted in progress tracker (DISABLED - table schema doesn't support external exercises)
        // progress_tracker::mark_submitted($USER->id, $courseid, $exerciseid, $result['submission_id'], $timespent);

        // Redirect to result page
        $redirecturl = new moodle_url('/local/exercise_suggestion/index.php', [
            'courseid' => $courseid,
            'action' => 'result',
            'submissionid' => $result['submission_id'],
            'exerciseid' => $exerciseid
        ]);

        redirect($redirecturl, get_string('submitsuccess', 'local_exercise_suggestion'), null, \core\output\notification::NOTIFY_SUCCESS);

    } catch (Exception $e) {
        $PAGE->navbar->add(get_string('exercises', 'local_exercise_suggestion'), 
            new moodle_url('/local/exercise_suggestion/index.php', ['courseid' => $courseid, 'action' => 'list']));
        $PAGE->navbar->add(get_string('submit', 'local_exercise_suggestion'));

        echo $OUTPUT->header();
        echo $OUTPUT->notification(get_string('error:submitfailed', 'local_exercise_suggestion') . ': ' . $e->getMessage(), 'error');
        echo $OUTPUT->continue_button(new moodle_url('/local/exercise_suggestion/index.php', [
            'courseid' => $courseid,
            'action' => 'view',
            'exerciseid' => $exerciseid
        ]));
        echo $OUTPUT->footer();
    }
}

/**
 * Handle result action (UC4 - section 4.4)
 */
function handle_result_action($service, $submissionid, $exerciseid, $courseid, $context) {
    global $USER, $OUTPUT, $PAGE;

    if (empty($submissionid)) {
        print_error('missingsubmissionid', 'local_exercise_suggestion');
    }

    $PAGE->navbar->add(get_string('exercises', 'local_exercise_suggestion'), 
        new moodle_url('/local/exercise_suggestion/index.php', ['courseid' => $courseid, 'action' => 'list']));
    $PAGE->navbar->add(get_string('results', 'local_exercise_suggestion'));

    echo $OUTPUT->header();

    try {
        // Get result from API with cache
        $result = $service->get_result($submissionid, $USER->username, $courseid);

        // Update progress if graded (DISABLED - table schema doesn't support external exercises)
        // if ($result['status'] === 'graded') {
        //     progress_tracker::mark_graded($USER->id, $courseid, $result['exercise_id'], 
        //         $result['score'], $result['max_score']);
        // }

        // Render result view
        $templatecontext = [
            'course_id' => $courseid,
            'result' => $result,
            'is_graded' => $result['status'] === 'graded',
            'is_pending' => in_array($result['status'], ['pending', 'grading']),
            'percentage_class' => $result['percentage'] >= 80 ? 'success' : 
                                 ($result['percentage'] >= 50 ? 'warning' : 'danger'),
            'list_url' => new moodle_url('/local/exercise_suggestion/index.php', [
                'courseid' => $courseid,
                'action' => 'list'
            ]),
            'exercise_url' => new moodle_url('/local/exercise_suggestion/index.php', [
                'courseid' => $courseid,
                'action' => 'view',
                'exerciseid' => $result['exercise_id']
            ])
        ];

        echo $OUTPUT->render_from_template('local_exercise_suggestion/result_view', $templatecontext);

    } catch (Exception $e) {
        echo $OUTPUT->notification(get_string('error:apierror', 'local_exercise_suggestion') . ': ' . $e->getMessage(), 'error');
    }

    echo $OUTPUT->footer();
}

/**
 * Handle courses list - Show all courses with exercise suggestions
 */
function handle_courses_list() {
    global $USER, $OUTPUT, $PAGE, $DB;

    require_login();

    $PAGE->set_url('/local/exercise_suggestion/index.php');
    $PAGE->set_context(context_system::instance());
    $PAGE->set_pagelayout('standard');
    $PAGE->set_title(get_string('pluginname', 'local_exercise_suggestion'));
    $PAGE->set_heading(get_string('pluginname', 'local_exercise_suggestion'));

    echo $OUTPUT->header();
    echo $OUTPUT->heading('Chọn môn học');

    // Get all courses user can access
    $courses = $DB->get_records_sql("
        SELECT c.* 
        FROM {course} c 
        WHERE c.id > 1 
        ORDER BY c.fullname
    ");
    
    // If no real courses, include site course for demo
    if (empty($courses)) {
        $courses = $DB->get_records('course', null, 'fullname');
    }

    if (empty($courses)) {
        echo $OUTPUT->notification('Không tìm thấy môn học nào.', 'info');
        echo $OUTPUT->footer();
        return;
    }

    // Render courses
    echo '<style>
    .courses-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 20px;
        margin-top: 20px;
    }
    .course-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: all 0.3s ease;
        text-decoration: none;
        display: block;
        color: inherit;
    }
    .course-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-2px);
        text-decoration: none;
    }
    .course-title {
        font-size: 18px;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 8px;
    }
    .course-code {
        color: #666;
        font-size: 14px;
        margin-bottom: 12px;
    }
    .course-btn {
        background: #667eea;
        color: white;
        padding: 8px 16px;
        border-radius: 6px;
        display: inline-block;
        margin-top: 12px;
        font-size: 14px;
    }
    </style>';

    echo '<div class="courses-grid">';
    foreach ($courses as $course) {
        $url = new moodle_url('/local/exercise_suggestion/index.php', [
            'courseid' => $course->id,
            'action' => 'list'
        ]);
        
        echo '<a href="' . $url . '" class="course-card">';
        echo '<div class="course-title">' . format_string($course->fullname) . '</div>';
        echo '<div class="course-code">' . format_string($course->shortname) . '</div>';
        echo '<span class="course-btn">Xem bài tập đề xuất →</span>';
        echo '</a>';
    }
    echo '</div>';

    echo $OUTPUT->footer();
}
