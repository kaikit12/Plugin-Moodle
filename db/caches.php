<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

/**
 * Cache definitions for local_exercise_suggestion plugin (section 6.2.1.B)
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

$definitions = [
    // Cache for API responses (suggestions, exercises, results)
    'apiresponses' => [
        'mode' => cache_store::MODE_APPLICATION,
        'simplekeys' => true,
        'simpledata' => false,
        'staticacceleration' => true,
        'staticaccelerationsize' => 100,
        'ttl' => 3600, // Default TTL 1 hour (can be overridden in code)
        'invalidationevents' => [
            'changesincourse',
            'changesinexercise',
        ],
    ],
];
