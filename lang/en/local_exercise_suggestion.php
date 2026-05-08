<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

/**
 * Language strings for Exercise Suggestion Integration plugin
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

defined('MOODLE_INTERNAL') || die();

// Plugin information
$string['pluginname'] = 'Exercise Suggestion Integration';
$string['privacy:metadata'] = 'The Exercise Suggestion Integration plugin does not store any personal data locally. It only acts as a bridge to communicate with third-party exercise suggestion systems.';

// Capabilities
$string['exercise_suggestion:view'] = 'View exercise suggestions';
$string['exercise_suggestion:manage'] = 'Manage exercise suggestion settings';
$string['exercise_suggestion:viewanalytics'] = 'View exercise analytics';

// General
$string['exercise_suggestions'] = 'Exercise Suggestions';
$string['user_suggestions'] = 'User Suggestions';
$string['no_suggestions'] = 'No exercise suggestions available at this time.';
$string['loading_suggestions'] = 'Loading exercise suggestions...';
$string['suggestions_error'] = 'Error loading exercise suggestions. Please try again later.';

// API Configuration
$string['api_config'] = 'API Configuration';
$string['api_config_desc'] = 'Configure the connection to the third-party exercise suggestion system.';
$string['api_url'] = 'API Base URL';
$string['api_url_desc'] = 'The base URL of the third-party exercise suggestion API (e.g., https://api.example.com)';
$string['api_key'] = 'API Key';
$string['api_key_desc'] = 'Authentication key for accessing the exercise suggestion API';
$string['api_timeout'] = 'API Timeout (seconds)';
$string['api_timeout_desc'] = 'Maximum time to wait for API responses (default: 30 seconds)';

// Feature Configuration
$string['feature_config'] = 'Feature Configuration';
$string['feature_config_desc'] = 'Enable or disable specific features of the exercise suggestion system.';
$string['enable_analytics'] = 'Enable Analytics';
$string['enable_analytics_desc'] = 'Allow the system to collect and display learning analytics from the external API';
$string['enable_feedback'] = 'Enable Feedback Collection';
$string['enable_feedback_desc'] = 'Allow users to provide feedback on exercise suggestions';
$string['cache_duration'] = 'Cache Duration (seconds)';
$string['cache_duration_desc'] = 'How long to cache exercise suggestions for better performance (default: 3600 seconds)';

// Performance Configuration
$string['performance_config'] = 'Performance Configuration';
$string['performance_config_desc'] = 'Configure performance-related settings for the plugin.';
$string['max_suggestions'] = 'Maximum Suggestions';
$string['max_suggestions_desc'] = 'Maximum number of suggestions to request and display per user (default: 10)';
$string['enable_error_logging'] = 'Enable Error Logging';
$string['enable_error_logging_desc'] = 'Log API errors to the system error log for debugging purposes';

// Debug Configuration
$string['debug_config'] = 'Debug Configuration';
$string['debug_config_desc'] = 'Configuration options for debugging and troubleshooting.';
$string['debug_mode'] = 'Enable Debug Mode';
$string['debug_mode_desc'] = 'Enable detailed logging for development and troubleshooting';

// Connection Testing
$string['test_connection'] = 'Test API Connection';
$string['test_connection_desc'] = 'Verify that the connection to the exercise suggestion API is working properly.';
$string['connection_test_info'] = 'After configuring the API settings above, use the test connection feature in the plugin dashboard to verify connectivity.';
$string['connection_successful'] = 'API connection test successful!';
$string['connection_failed'] = 'API connection test failed: {$a}';

// Error Messages
$string['api_url_not_configured'] = 'API URL is not configured. Please check the plugin settings.';
$string['curl_init_failed'] = 'Failed to initialize cURL for API communication.';
$string['api_connection_error'] = 'API connection error: {$a}';
$string['api_http_error'] = 'API HTTP error: {$a}';
$string['api_json_decode_error'] = 'API JSON decode error: {$a}';
$string['invalid_api_response'] = 'Invalid response format from API.';
$string['api_returned_error'] = 'API returned an error: {$a}';
$string['invalid_user_or_course'] = 'Invalid user or course specified.';
$string['insufficient_permissions'] = 'You do not have permission to access exercise suggestions.';
$string['invalid_feedback_data'] = 'Invalid feedback data provided.';
$string['analytics_disabled'] = 'Analytics are currently disabled in the plugin configuration.';
$string['invalid_analytics_response'] = 'Invalid analytics response from API.';
$string['analytics_api_error'] = 'Error retrieving analytics from API.';
$string['invalid_feedback_response'] = 'Invalid feedback response from API.';
$string['invalid_progress_data'] = 'Invalid progress data provided.';

// Suggestion Display
$string['suggestion_title'] = 'Exercise Suggestion';
$string['suggestion_description'] = 'Description';
$string['suggestion_difficulty'] = 'Difficulty';
$string['suggestion_estimated_time'] = 'Estimated Time';
$string['suggestion_topics'] = 'Topics';
$string['suggestion_skills'] = 'Skills';
$string['suggestion_confidence'] = 'Confidence Score';
$string['suggestion_external_link'] = 'View Exercise';

// Difficulty Levels
$string['difficulty_easy'] = 'Easy';
$string['difficulty_medium'] = 'Medium';
$string['difficulty_hard'] = 'Hard';
$string['difficulty_expert'] = 'Expert';

// Feedback
$string['feedback_title'] = 'Exercise Feedback';
$string['feedback_rating'] = 'Overall Rating';
$string['feedback_difficulty_rating'] = 'Difficulty Rating';
$string['feedback_comments'] = 'Comments';
$string['feedback_submit'] = 'Submit Feedback';
$string['feedback_success'] = 'Feedback submitted successfully!';
$string['feedback_error'] = 'Error submitting feedback. Please try again.';

// Analytics
$string['analytics_title'] = 'Learning Analytics';
$string['analytics_progress'] = 'Learning Progress';
$string['analytics_skills'] = 'Skill Levels';
$string['analytics_performance'] = 'Performance Metrics';
$string['analytics_engagement'] = 'Engagement Score';
$string['analytics_strengths'] = 'Strengths';
$string['analytics_improvements'] = 'Areas for Improvement';
$string['analytics_not_available'] = 'Analytics data is not available at this time.';

// Dashboard
$string['dashboard_title'] = 'Exercise Suggestion Dashboard';
$string['dashboard_overview'] = 'Overview';
$string['dashboard_recent_suggestions'] = 'Recent Suggestions';
$string['dashboard_analytics'] = 'Your Analytics';
$string['dashboard_feedback'] = 'Feedback History';

// Filters
$string['filters_title'] = 'Filter Suggestions';
$string['filter_difficulty'] = 'Difficulty Level';
$string['filter_topic'] = 'Topic';
$string['filter_time'] = 'Available Time';
$string['filter_skill'] = 'Skill Focus';
$string['filter_apply'] = 'Apply Filters';
$string['filter_clear'] = 'Clear Filters';

// Time formats
$string['time_minutes'] = '{$a} minutes';
$string['time_hours'] = '{$a} hours';
$string['time_days'] = '{$a} days';

// Navigation
$string['nav_suggestions'] = 'Suggestions';
$string['nav_analytics'] = 'Analytics';
$string['nav_feedback'] = 'Feedback';
$string['nav_settings'] = 'Settings';

// Privacy
$string['privacy:metadata:exercise_suggestion_api'] = 'User data sent to external exercise suggestion API';
$string['privacy:metadata:exercise_suggestion_api:userid'] = 'The user ID is sent to identify the user in the external system';
$string['privacy:metadata:exercise_suggestion_api:courseid'] = 'The course ID is sent to provide context for suggestions';
$string['privacy:metadata:exercise_suggestion_api:progress'] = 'User progress data is sent to improve suggestion accuracy';
$string['privacy:metadata:exercise_suggestion_api:preferences'] = 'User learning preferences are sent to personalize suggestions';

// Tasks
$string['task_sync_progress'] = 'Sync user progress with exercise suggestion API';
$string['task_cleanup_cache'] = 'Clean up expired suggestion cache entries';
$string['task_update_analytics'] = 'Update user analytics from API';

// Events
$string['event_suggestion_viewed'] = 'Exercise suggestion viewed';
$string['event_suggestion_clicked'] = 'Exercise suggestion clicked';
$string['event_feedback_submitted'] = 'Exercise feedback submitted';
$string['event_analytics_viewed'] = 'Exercise analytics viewed';

// Result page
$string['backtosuggestionlist'] = 'Back to Exercise List';
$string['retryexercise'] = 'Try Again';
$string['testresults'] = 'Test Results';
$string['overallfeedback'] = 'Overall Feedback';

// UC Navigation strings
$string['exercises'] = 'Exercise Suggestions';
$string['exercisedetails'] = 'Exercise Details';
$string['submit'] = 'Submit Exercise';
$string['results'] = 'Submission Results';

// UC Error strings
$string['error:apierror'] = 'API Error';
$string['error:submitfailed'] = 'Failed to submit exercise';
$string['error:invalidparameters'] = 'Invalid parameters provided';
$string['invalidaction'] = 'Invalid action requested';
$string['missingexerciseid'] = 'Exercise ID is required';
$string['missingsubmissionid'] = 'Submission ID is required';
$string['submitsuccess'] = 'Exercise submitted successfully!';