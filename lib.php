<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

/**
 * Plugin library functions
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

// Hook removed to favor JS injection.

/**
 * Extend the course navigation / user navigation
 */
function local_exercise_suggestion_extend_navigation(global_navigation $navigation) {
    global $PAGE;

    if (empty($PAGE)) {
        return;
    }

    // CHỈ HIỂN THỊ nếu pagetype thuộc mảng cho phép
    if (in_array($PAGE->pagetype, ['site-index', 'my-index', 'mycourses-index'])) {
        
        // CSS Style Inline - nhúng vào body
        $css = '<style>
            .suggestion-fab {
                position: fixed;
                bottom: 30px;
                right: 30px;
                z-index: 9999;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white !important;
                border: none;
                border-radius: 50px;
                padding: 15px 25px;
                font-size: 16px;
                font-weight: 600;
                box-shadow: 0 4px 15px rgba(102, 126, 234, 0.5);
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .suggestion-fab:hover {
                transform: translateY(-5px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.7);
                color: white !important;
            }
            .suggestion-overlay {
                display: none;
                position: fixed;
                bottom: 90px;
                right: 30px;
                width: 420px;
                max-height: 75vh;
                overflow-y: auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                z-index: 9998;
                padding: 20px;
            }
            .suggestion-overlay::-webkit-scrollbar { width: 6px; }
            .suggestion-overlay::-webkit-scrollbar-track { background: transparent; }
            .suggestion-overlay::-webkit-scrollbar-thumb { background-color: #ddd; border-radius: 20px; }
        </style>';

        // HTML chèn vào DOM
        $html = $css . '
            <button class="suggestion-fab btn-suggest-exercise-dashboard">
                <i class="fa fa-magic" style="margin-right:8px;"></i> Có bài tập đề xuất
            </button>
            <div id="suggestion-dashboard-overlay" class="suggestion-overlay"></div>
        ';

        // Xóa dấu nháy đơn và ngoặc kép bị xung đột khi escape JS
        $safe_html = str_replace(["\r", "\n", "'"], ["", "", "\\'"], $html);

        // 1. Tiêm HTML vào cuối body
        $PAGE->requires->js_amd_inline("document.body.insertAdjacentHTML('beforeend', '" . $safe_html . "');");

        // 2. Load file AMD JS main.js và gọi hàm init
        $PAGE->requires->js_call_amd('local_exercise_suggestion/main', 'init');
    }
}

function local_exercise_suggestion_extend_navigation_course($navigation, $course, $context) {
    if (has_capability('local/exercise_suggestion:view', $context)) {
        $url = new moodle_url('/local/exercise_suggestion/index.php', array('courseid' => $course->id));
        $navigation->add(
            get_string('exercise_suggestions', 'local_exercise_suggestion'),
            $url,
            navigation_node::TYPE_SETTING,
            null,
            'exercise_suggestions',
            new pix_icon('i/report', '')
        );
    }
}