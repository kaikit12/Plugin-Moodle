<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

/**
 * Upgrade script for Exercise Suggestion Integration plugin
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

/**
 * Upgrade the plugin database tables and configuration
 *
 * @param int $oldversion The old version of the plugin
 * @return bool True if upgrade was successful
 */
function xmldb_local_exercise_suggestion_upgrade($oldversion) {
    global $DB;
    $dbman = $DB->get_manager();

    if ($oldversion < 2024102201) {
        // Add new field to feedback table if it doesn't exist
        $table = new xmldb_table('local_exsug_feedback');
        $field = new xmldb_field('usefulness_rating', XMLDB_TYPE_INTEGER, '2', null, null, null, null, 'difficulty_rating');

        if (!$dbman->field_exists($table, $field)) {
            $dbman->add_field($table, $field);
        }

        // Exercise suggestion savepoint reached.
        upgrade_plugin_savepoint(true, 2024102201, 'local', 'exercise_suggestion');
    }

    if ($oldversion < 2024102202) {
        // Add index for better performance on feedback queries
        $table = new xmldb_table('local_exsug_feedback');
        $index = new xmldb_index('completed_idx', XMLDB_INDEX_NOTUNIQUE, array('completed'));

        if (!$dbman->index_exists($table, $index)) {
            $dbman->add_index($table, $index);
        }

        // Exercise suggestion savepoint reached.
        upgrade_plugin_savepoint(true, 2024102202, 'local', 'exercise_suggestion');
    }

    if ($oldversion < 2024102203) {
        // Add cache cleanup for performance
        $table = new xmldb_table('local_exsug_cache');
        if ($dbman->table_exists($table)) {
            // Clean up expired cache entries
            $expiredtime = time() - (7 * 24 * 3600); // Older than 7 days
            $DB->delete_records_select('local_exsug_cache', 'timeexpires < ?', array($expiredtime));
        }

        // Exercise suggestion savepoint reached.
        upgrade_plugin_savepoint(true, 2024102203, 'local', 'exercise_suggestion');
    }

    if ($oldversion < 2024102204) {
        // Update default configuration values
        set_config('cache_duration', 3600, 'local_exercise_suggestion'); // 1 hour default
        set_config('max_suggestions', 10, 'local_exercise_suggestion');
        set_config('api_timeout', 30, 'local_exercise_suggestion');

        // Exercise suggestion savepoint reached.
        upgrade_plugin_savepoint(true, 2024102204, 'local', 'exercise_suggestion');
    }

    if ($oldversion < 2024102205) {
        // Add new analytics table if it doesn't exist (for older versions that might not have it)
        $table = new xmldb_table('local_exsug_analytics');
        
        if (!$dbman->table_exists($table)) {
            // Define table structure
            $table->add_field('id', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, XMLDB_SEQUENCE, null);
            $table->add_field('userid', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, null);
            $table->add_field('courseid', XMLDB_TYPE_INTEGER, '10', null, null, null, null);
            $table->add_field('analytics_type', XMLDB_TYPE_CHAR, '50', null, XMLDB_NOTNULL, null, null);
            $table->add_field('analytics_data', XMLDB_TYPE_TEXT, null, null, XMLDB_NOTNULL, null, null);
            $table->add_field('engagement_score', XMLDB_TYPE_NUMBER, '5,2', null, null, null, null);
            $table->add_field('performance_score', XMLDB_TYPE_NUMBER, '5,2', null, null, null, null);
            $table->add_field('confidence_level', XMLDB_TYPE_CHAR, '20', null, null, null, null);
            $table->add_field('recommended_difficulty', XMLDB_TYPE_CHAR, '20', null, null, null, null);
            $table->add_field('last_api_update', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, null);
            $table->add_field('timecreated', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, null);
            $table->add_field('timemodified', XMLDB_TYPE_INTEGER, '10', null, XMLDB_NOTNULL, null, null);

            // Add keys
            $table->add_key('primary', XMLDB_KEY_PRIMARY, array('id'));
            $table->add_key('userid_fk', XMLDB_KEY_FOREIGN, array('userid'), 'user', array('id'));
            $table->add_key('courseid_fk', XMLDB_KEY_FOREIGN, array('courseid'), 'course', array('id'));

            // Add indexes
            $table->add_index('userid_courseid_type_idx', XMLDB_INDEX_UNIQUE, array('userid', 'courseid', 'analytics_type'));
            $table->add_index('userid_idx', XMLDB_INDEX_NOTUNIQUE, array('userid'));
            $table->add_index('last_api_update_idx', XMLDB_INDEX_NOTUNIQUE, array('last_api_update'));

            // Create table
            $dbman->create_table($table);
        }

        // Exercise suggestion savepoint reached.
        upgrade_plugin_savepoint(true, 2024102205, 'local', 'exercise_suggestion');
    }

    return true;
}

/**
 * Post installation hook
 */
function xmldb_local_exercise_suggestion_install() {
    global $DB;
    
    // Set default configuration values
    set_config('enable_analytics', 1, 'local_exercise_suggestion');
    set_config('enable_feedback', 1, 'local_exercise_suggestion');
    set_config('cache_duration', 3600, 'local_exercise_suggestion');
    set_config('max_suggestions', 10, 'local_exercise_suggestion');
    set_config('api_timeout', 30, 'local_exercise_suggestion');
    set_config('debug_mode', 0, 'local_exercise_suggestion');
    set_config('enable_error_logging', 0, 'local_exercise_suggestion');
}