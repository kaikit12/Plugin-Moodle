<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

/**
 * Plugin settings configuration
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

if ($hassiteconfig) {
    $settings = new admin_settingpage('local_exercise_suggestion', 
        get_string('pluginname', 'local_exercise_suggestion'));

    // API Configuration Section
    $settings->add(new admin_setting_heading(
        'local_exercise_suggestion/api_config',
        get_string('api_config', 'local_exercise_suggestion'),
        get_string('api_config_desc', 'local_exercise_suggestion')
    ));

    // API URL setting
    $settings->add(new admin_setting_configtext(
        'local_exercise_suggestion/api_url',
        get_string('api_url', 'local_exercise_suggestion'),
        get_string('api_url_desc', 'local_exercise_suggestion'),
        'http://localhost:8080',
        PARAM_URL,
        60
    ));

    // API Key setting
    $settings->add(new admin_setting_configpasswordunmask(
        'local_exercise_suggestion/api_key',
        get_string('api_key', 'local_exercise_suggestion'),
        get_string('api_key_desc', 'local_exercise_suggestion'),
        ''
    ));

    // API Timeout setting
    $settings->add(new admin_setting_configtext(
        'local_exercise_suggestion/api_timeout',
        get_string('api_timeout', 'local_exercise_suggestion'),
        get_string('api_timeout_desc', 'local_exercise_suggestion'),
        '30',
        PARAM_INT,
        5
    ));

    // Feature Configuration Section
    $settings->add(new admin_setting_heading(
        'local_exercise_suggestion/feature_config',
        get_string('feature_config', 'local_exercise_suggestion'),
        get_string('feature_config_desc', 'local_exercise_suggestion')
    ));

    // Enable analytics
    $settings->add(new admin_setting_configcheckbox(
        'local_exercise_suggestion/enable_analytics',
        get_string('enable_analytics', 'local_exercise_suggestion'),
        get_string('enable_analytics_desc', 'local_exercise_suggestion'),
        1
    ));

    // Enable feedback collection
    $settings->add(new admin_setting_configcheckbox(
        'local_exercise_suggestion/enable_feedback',
        get_string('enable_feedback', 'local_exercise_suggestion'),
        get_string('enable_feedback_desc', 'local_exercise_suggestion'),
        1
    ));

    // Cache duration
    $settings->add(new admin_setting_configtext(
        'local_exercise_suggestion/cache_duration',
        get_string('cache_duration', 'local_exercise_suggestion'),
        get_string('cache_duration_desc', 'local_exercise_suggestion'),
        '3600',
        PARAM_INT,
        10
    ));

    // Performance Configuration Section
    $settings->add(new admin_setting_heading(
        'local_exercise_suggestion/performance_config',
        get_string('performance_config', 'local_exercise_suggestion'),
        get_string('performance_config_desc', 'local_exercise_suggestion')
    ));

    // Maximum suggestions per request
    $settings->add(new admin_setting_configtext(
        'local_exercise_suggestion/max_suggestions',
        get_string('max_suggestions', 'local_exercise_suggestion'),
        get_string('max_suggestions_desc', 'local_exercise_suggestion'),
        '10',
        PARAM_INT,
        5
    ));

    // Enable error logging
    $settings->add(new admin_setting_configcheckbox(
        'local_exercise_suggestion/enable_error_logging',
        get_string('enable_error_logging', 'local_exercise_suggestion'),
        get_string('enable_error_logging_desc', 'local_exercise_suggestion'),
        0
    ));

    // Debugging Configuration Section
    $settings->add(new admin_setting_heading(
        'local_exercise_suggestion/debug_config',
        get_string('debug_config', 'local_exercise_suggestion'),
        get_string('debug_config_desc', 'local_exercise_suggestion')
    ));

    // Enable debug mode
    $settings->add(new admin_setting_configcheckbox(
        'local_exercise_suggestion/debug_mode',
        get_string('debug_mode', 'local_exercise_suggestion'),
        get_string('debug_mode_desc', 'local_exercise_suggestion'),
        0
    ));

    // Test API Connection Button
    $settings->add(new admin_setting_heading(
        'local_exercise_suggestion/test_connection',
        get_string('test_connection', 'local_exercise_suggestion'),
        get_string('test_connection_desc', 'local_exercise_suggestion')
    ));

    // Add note about connection testing - use standard text element instead
    $settings->add(new admin_setting_configtext(
        'local_exercise_suggestion/connection_test_note',
        '',
        get_string('connection_test_info', 'local_exercise_suggestion'),
        ''
    ));

    // Ensure the localplugins category exists (required if no other local plugin has settings)
    if (!$ADMIN->locate('localplugins')) {
        $ADMIN->add('root', new admin_category('localplugins',
            new lang_string('local', 'admin'), !$hassiteconfig));
    }
    $ADMIN->add('localplugins', $settings);
}