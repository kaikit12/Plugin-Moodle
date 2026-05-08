<?php
// This file is part of Moodle - http://moodle.org/
//
// Moodle is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

defined('MOODLE_INTERNAL') || die();

/**
 * Plugin version information
 *
 * @package    local_exercise_suggestion
 * @copyright  2024 Your Organization
 * @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

$plugin->component = 'local_exercise_suggestion';
$plugin->version = 2026030701; // YYYYMMDDXX format - bumped to force Moodle DB upgrade
$plugin->requires = 2020110900; // Moodle 3.10 or higher
$plugin->maturity = MATURITY_STABLE;
$plugin->release = 'v1.0.0';
$plugin->dependencies = array();