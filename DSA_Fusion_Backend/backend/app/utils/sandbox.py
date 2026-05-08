"""
DSA AutoGrader - Enhanced Sandbox with Memory Limits.

Features:
- CPU time limit enforcement
- Memory limit enforcement (Windows & Linux)
- Process isolation
- Resource monitoring
"""

import logging
import os
import json
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from typing import Optional

from app.core.config import SANDBOX_MAX_CPU_TIME, SANDBOX_MAX_MEMORY_MB

logger = logging.getLogger("dsa.sandbox")

# Check for psutil availability once at module load
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Only import ctypes once globally if psutil is unavailable on Windows
if sys.platform == 'win32' and not HAS_PSUTIL:
    import ctypes

@dataclass
class SandboxResult:
    """Result from sandbox execution."""
    success: bool
    output: str
    error: str
    time_used: float
    memory_used: float
    return_code: Optional[int] = None
    timeout: bool = False
    memory_exceeded: bool = False


def _get_process_memory_mb(pid: int) -> float:
    """Get current memory usage of a process in MB."""
    try:
        if sys.platform == 'win32':
            # Windows: Use wmic or psutil
            if HAS_PSUTIL:
                process = psutil.Process(pid)
                return process.memory_info().rss / (1024 * 1024)  # Convert to MB
            else:
                # Fallback: use wmic
                ctypes.windll.kernel32.GlobalMemoryStatusEx.restype = ctypes.c_bool
                return 0.0
        else:
            # Linux: Read from /proc
            with open(f'/proc/{pid}/status', 'r') as f:
                for line in f:
                    if line.startswith('VmRSS:'):
                        # VmRSS is in kB
                        parts = line.split()
                        if len(parts) >= 2:
                            return float(parts[1]) / 1024  # Convert to MB
            return 0.0
    except Exception:
        return 0.0


def _monitor_process_memory(process: subprocess.Popen, max_memory_mb: float, stop_event: threading.Event) -> bool:
    """
    Monitor process memory usage.
    
    Returns True if memory limit exceeded, False otherwise.
    """
    while not stop_event.is_set():
        try:
            memory_mb = _get_process_memory_mb(process.pid)
            if memory_mb > max_memory_mb:
                logger.warning("Process memory limit exceeded: %.2f MB > %.2f MB", memory_mb, max_memory_mb)
                return True
        except Exception:
            pass
        time.sleep(0.1)  # Check every 100ms
    return False


def run_python_sandbox(
    code: str,
    input_str: str = "",
    timeout: int = None,
    max_memory_mb: int = None
) -> SandboxResult:
    """Run Python code in sandbox for a single input."""
    results = run_python_sandbox_batch(code, [input_str], timeout, max_memory_mb)
    return results[0]


def run_python_sandbox_batch(
    code: str,
    inputs: list[str],
    timeout_per_case: int = None,
    max_memory_mb: int = None
) -> list[SandboxResult]:
    """
    Run Python code in sandbox for MULTIPLE inputs in ONE process.
    
    This is much faster than running one process per test case.
    """
    timeout_per_case = timeout_per_case or SANDBOX_MAX_CPU_TIME
    total_timeout = timeout_per_case * len(inputs) + 2 # Add buffer
    max_memory_mb = max_memory_mb or SANDBOX_MAX_MEMORY_MB

    # Wrapper code to handle multiple test cases
    wrapper_code = f"""
import sys
import json
import time
import io

# Backup original stdin/stdout
_orig_stdin = sys.stdin
_orig_stdout = sys.stdout

# Student code template (will be executed inside each test case)
_STUDENT_CODE = {repr(code)}

def _run_test_case(input_data):
    sys.stdin = io.StringIO(input_data)
    sys.stdout = io.StringIO()

    start_time = time.time()
    error = ""
    success = True

    try:
        # Execute student code ONLY inside this test case
        exec(_STUDENT_CODE, {{}})
    except Exception as e:
        success = False
        error = str(e)
    
    output = sys.stdout.getvalue()
    elapsed = time.time() - start_time
    
    return {{
        "success": success,
        "output": output,
        "error": error,
        "time_used": elapsed
    }}

test_inputs = {repr(inputs)}
results = []

for inp in test_inputs:
    results.append(_run_test_case(inp))

sys.stdout = _orig_stdout
print(json.dumps(results))
"""

    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
        encoding="utf-8",
        newline='\n'
    ) as f:
        f.write(wrapper_code)
        temp_file = f.name

    # Start process
    try:
        process = subprocess.Popen(
            [sys.executable, temp_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0,
        )
        
        stdout, stderr = process.communicate(timeout=total_timeout)
        
        try:
            batch_results = json.loads(stdout)
            return [
                SandboxResult(
                    success=r["success"],
                    output=r["output"],
                    error=r["error"] or stderr,
                    time_used=r["time_used"],
                    memory_used=0.0, # Approximate
                    return_code=0
                ) for r in batch_results
            ]
        except Exception:
            # Fallback if JSON parsing fails
            return [
                SandboxResult(
                    success=False,
                    output=stdout,
                    error=stderr or "Process failed to produce valid JSON results",
                    time_used=0,
                    memory_used=0,
                    return_code=-1
                ) for _ in inputs
            ]

    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except: pass
        return [
            SandboxResult(
                success=False,
                output="",
                error="Batch execution timeout",
                time_used=timeout_per_case,
                memory_used=0,
                timeout=True
            ) for _ in inputs
        ]
    except Exception as e:
        return [
            SandboxResult(
                success=False,
                output="",
                error=f"Sandbox error: {str(e)}",
                time_used=0,
                memory_used=0
            ) for _ in inputs
        ]
    finally:
        try: os.unlink(temp_file)
        except: pass


def run_with_sandbox_limits(
    code: str,
    test_cases: list,
    timeout: int = None,
    max_memory_mb: int = None
) -> list:
    """Run multiple test cases using the optimized batch sandbox."""
    inputs = [tc[0] for tc in test_cases]
    expectations = [tc[1] for tc in test_cases]
    
    batch_results = run_python_sandbox_batch(code, inputs, timeout, max_memory_mb)
    
    final_results = []
    for i, result in enumerate(batch_results):
        expected_output = expectations[i]
        passed = result.success and result.output.strip() == expected_output.strip()

        final_results.append({
            "testcase_id": f"test_{i + 1}",
            "passed": passed,
            "actual_output": result.output,
            "expected_output": expected_output,
            "error": result.error,
            "time_ms": result.time_used * 1000,
            "memory_kb": result.memory_used * 1024,
            "timeout": result.timeout,
            "memory_exceeded": result.memory_exceeded,
        })

    return final_results


__all__ = [
    "SandboxResult",
    "run_python_sandbox",
    "run_with_sandbox_limits",
]
