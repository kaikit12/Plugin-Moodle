<?php
namespace local_exercise_suggestion\output;

defined('MOODLE_INTERNAL') || die();

class main_renderer extends \plugin_renderer_base {
    public function render_suggestions($suggestions) {
        $html = '';
        foreach ($suggestions as $ex) {
            $html .= "<div class='exercise-card'><b>" . htmlspecialchars($ex['title']) . "</b> (" . htmlspecialchars($ex['difficulty']) . ")<br>" . htmlspecialchars($ex['description']) . "</div>\n";
        }
        return $html ?: '<div>No suggestions found.</div>';
    }
}
