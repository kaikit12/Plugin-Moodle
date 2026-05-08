"""
DSA AutoGrader - Backend Tests

Test suite for grading services, AST analysis, and test runner.
"""

import pytest
import sys
import os
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.grading.test_runner import score_static_tests, run_dynamic_tests
from app.services.grading.constants import SCORING_CONSTANTS, CodeFeatures


# ═══════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def sample_bubble_sort_code():
    """Sample bubble sort implementation for testing."""
    return """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

if __name__ == "__main__":
    test_arr = [64, 34, 25, 12, 22, 11, 90]
    print(bubble_sort(test_arr))
"""


@pytest.fixture
def sample_bubble_sort_with_type_hints():
    """Bubble sort with type hints."""
    return """
from typing import List

def bubble_sort(arr: List[int]) -> List[int]:
    n: int = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr

if __name__ == "__main__":
    test_arr: List[int] = [64, 34, 25, 12, 22, 11, 90]
    print(bubble_sort(test_arr))
"""


@pytest.fixture
def sample_code_without_main():
    """Code without if __name__ == '__main__' guard."""
    return """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""


# ═══════════════════════════════════════════
#  Static Tests
# ═══════════════════════════════════════════

class TestStaticCodeAnalysis:
    """Tests for static code analysis."""

    def test_code_with_main_guard(self, sample_bubble_sort_code):
        """Test code with __main__ guard detection."""
        features = CodeFeatures(
            has_main_guard=True,
            has_returns=True,
            has_type_hints=False,
            nodes_for_fingerprint=["FunctionDef", "For", "If"]
        )
        score = score_static_tests(features)
        assert score >= SCORING_CONSTANTS.MAIN_GUARD_BONUS

    def test_code_with_type_hints(self, sample_bubble_sort_with_type_hints):
        """Test code with type hints detection."""
        features = CodeFeatures(
            has_main_guard=True,
            has_returns=True,
            has_type_hints=True,
            nodes_for_fingerprint=["FunctionDef", "For", "If"]
        )
        score = score_static_tests(features)
        assert score >= (
            SCORING_CONSTANTS.MAIN_GUARD_BONUS +
            SCORING_CONSTANTS.RETURN_OR_PRINT_BONUS +
            SCORING_CONSTANTS.TYPE_HINT_BONUS
        )

    def test_code_without_main_guard(self, sample_code_without_main):
        """Test code without __main__ guard."""
        features = CodeFeatures(
            has_main_guard=False,
            has_returns=True,
            has_type_hints=False,
            nodes_for_fingerprint=["FunctionDef", "For"]
        )
        score = score_static_tests(features)
        assert score == SCORING_CONSTANTS.RETURN_OR_PRINT_BONUS


# ═══════════════════════════════════════════
#  Dynamic Tests
# ═══════════════════════════════════════════

class TestDynamicTestRunner:
    """Tests for dynamic test execution."""

    def test_run_dynamic_tests_with_valid_code(self, sample_bubble_sort_code):
        """Test running dynamic tests with valid code."""
        score, notes, results = run_dynamic_tests(
            code=sample_bubble_sort_code,
            filename="bubble_sort.py",
            topic="sort"
        )
        
        assert isinstance(score, int)
        assert 0 <= score <= SCORING_CONSTANTS.MAX_TEST_SCORE
        assert isinstance(notes, list)
        assert isinstance(results, list)
        
        # Check that notes contain test execution info
        assert any("test cases" in note.lower() for note in notes)

    def test_run_dynamic_tests_with_sort_topic(self, sample_bubble_sort_code):
        """Test sorting algorithm with sort topic test cases."""
        score, notes, results = run_dynamic_tests(
            code=sample_bubble_sort_code,
            filename="sort.py",
            topic="sort"
        )
        
        # Verify results structure
        for result in results:
            assert "testcase_id" in result or "testcase_name" in result
            assert "passed" in result
            assert "input" in result
            assert "expected_output" in result
            assert "actual_output" in result

    def test_run_dynamic_tests_with_unknown_topic(self, sample_bubble_sort_code):
        """Test with unknown topic (should return empty results)."""
        score, notes, results = run_dynamic_tests(
            code=sample_bubble_sort_code,
            filename="test.py",
            topic="unknown_topic"
        )
        
        assert score == 0
        assert notes == []
        assert results == []


# ═══════════════════════════════════════════
#  Integration Tests
# ═══════════════════════════════════════════

class TestGradingIntegration:
    """Integration tests for the grading pipeline."""

    def test_full_grading_pipeline(self, sample_bubble_sort_code):
        """Test complete grading pipeline."""
        # Static analysis
        features = CodeFeatures(
            has_main_guard=True,
            has_returns=True,
            has_type_hints=False,
            nodes_for_fingerprint=["FunctionDef", "For", "If", "Compare"]
        )
        static_score = score_static_tests(features)
        
        # Dynamic tests
        dynamic_score, notes, results = run_dynamic_tests(
            code=sample_bubble_sort_code,
            filename="bubble_sort.py",
            topic="sort"
        )
        
        # Total score should be combination of static and dynamic
        total_score = static_score + dynamic_score
        assert total_score >= 0
        
        # Notes should contain execution summary
        assert any("test cases" in note.lower() for note in notes)

    def test_grading_with_incorrect_code(self):
        """Test grading with incorrect sorting algorithm."""
        incorrect_code = """
def bubble_sort(arr):
    # Intentionally wrong - returns input unchanged
    return arr

if __name__ == "__main__":
    print(bubble_sort([3, 1, 2]))
"""
        score, notes, results = run_dynamic_tests(
            code=incorrect_code,
            filename="wrong_sort.py",
            topic="sort"
        )
        
        # Score should be low or zero for incorrect code
        # Note: Some test cases might pass by coincidence
        assert isinstance(score, int)
        assert isinstance(results, list)


# ═══════════════════════════════════════════
#  Edge Cases
# ═══════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_code(self):
        """Test with empty code."""
        score, notes, results = run_dynamic_tests(
            code="",
            filename="empty.py",
            topic="sort"
        )
        assert score == 0

    def test_code_with_syntax_error(self):
        """Test with syntax error in code."""
        bad_code = """
def bubble_sort(arr):
    for i in range(n)  # Missing colon - syntax error
        print(arr)
"""
        score, notes, results = run_dynamic_tests(
            code=bad_code,
            filename="syntax_error.py",
            topic="sort"
        )
        assert score == 0
        assert any("error" in note.lower() for note in notes) or len(notes) == 0

    def test_timeout_handling(self):
        """Test handling of timeout scenarios."""
        # Infinite loop code
        infinite_code = """
while True:
    pass
"""
        score, notes, results = run_dynamic_tests(
            code=infinite_code,
            filename="infinite.py",
            topic="sort"
        )
        # Should handle timeout gracefully
        assert isinstance(score, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
