"""
DSA AutoGrader - AST Grader Tests

Test suite for AST-based code analysis.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ast_grader import (
    DSALightningGrader, 
    lightning_grader,
    CodeFeatures
)
from app.services.grading.constants import SCORING_CONSTANTS


@pytest.fixture
def grader():
    """Create a grader instance."""
    return DSALightningGrader()


class TestASTGrader:
    """Tests for AST grader."""

    def test_grader_initialization(self, grader):
        """Test grader initializes correctly."""
        assert grader is not None
        # DSALightningGrader uses grade_file_ultra_fast method
        assert hasattr(grader, 'grade_file_ultra_fast')

    def test_bubble_sort_detection(self, grader):
        """Test bubble sort algorithm detection."""
        code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""
        result = grader.grade_file_ultra_fast(code, "bubble_sort.py", "sort")
        assert result is not None
        assert result.get("valid_score", False)

    def test_nested_loops_detection(self, grader):
        """Test nested loop detection."""
        code = """
for i in range(10):
    for j in range(10):
        print(i, j)
"""
        result = grader.grade_file_ultra_fast(code, "nested.py", "")
        assert result is not None
        assert "total_score" in result or "algorithms" in result

    def test_recursion_detection(self, grader):
        """Test recursion detection."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        result = grader.grade_file_ultra_fast(code, "factorial.py", "recursion")
        assert result is not None

    def test_data_structure_detection(self, grader):
        """Test data structure detection."""
        code = """
my_list = [1, 2, 3]
my_dict = {"key": "value"}
my_set = {1, 2, 3}
my_tuple = (1, 2, 3)
"""
        result = grader.grade_file_ultra_fast(code, "data_structures.py", "")
        assert result is not None

    def test_main_guard_detection(self, grader):
        """Test __main__ guard detection."""
        code = """
if __name__ == "__main__":
    print("Hello")
"""
        result = grader.grade_file_ultra_fast(code, "main.py", "")
        assert result is not None

    def test_type_hint_detection(self, grader):
        """Test type hint detection."""
        code = """
def add(a: int, b: int) -> int:
    return a + b
"""
        result = grader.grade_file_ultra_fast(code, "typed.py", "")
        assert result is not None

    def test_swap_detection(self, grader):
        """Test swap pattern detection."""
        code = """
a, b = b, a
"""
        result = grader.grade_file_ultra_fast(code, "swap.py", "")
        assert result is not None

    def test_complexity_analysis(self, grader):
        """Test complexity analysis."""
        code = """
for i in range(n):
    for j in range(n):
        for k in range(n):
            print(i, j, k)
"""
        result = grader.grade_file_ultra_fast(code, "complex.py", "")
        assert result is not None


class TestLightningGraderModule:
    """Tests for lightning_grader module."""

    def test_lightning_grader_grade_file_ultra_fast(self):
        """Test lightning_grader module function."""
        code = """
def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr
"""
        result = lightning_grader.grade_file_ultra_fast(code, "test.py", "sort")
        assert result is not None
        assert "total_score" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
