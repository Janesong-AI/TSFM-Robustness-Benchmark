"""
core —— Business Core Layer

Provides centralized management for business logic, state, and external interactions.
Serves as the bridge between the ``testcases`` layer and ``utils`` layer.

Modules:
-------
models.py —— Shared Data Models
  Defines core data structures (TestStatus, TestResult, BatchReport) used across
  the entire framework. Supports i18n via TEST_LANG environment variable.

results.py —— Test Result Manager
  Manages result persistence (batch buffering), historical loading, and querying.
  Internally uses utils.concurrent for thread-safe file operations.

resume.py —— Strategy Controller
  Provides checkpoint resumption logic and rate limit detection strategy.

timecho.py —— TimechoAI Interaction Layer
    Encapsulates API requests and response handling, offering a unified high-level API.

Usage:
--------------
>>> # Data models
>>> from core.models import TestStatus, TestResult, BatchReport
>>> result = TestResult(module_path="test_xxx.py")
>>> result.mark_start()
>>> result.mark_end(TestStatus.PASSED)
>>> print(result.status.get_display("PASSED"))  # i18n display

>>> # Result management (with auto buffering)
>>> from core.results import load_results_from_csv, append_result_to_csv, flush_all_results
>>> records, fails = load_results_from_csv("./results/test.csv")
>>> append_result_to_csv("./results/test.csv", {"mae": 0.5})  # Auto buffered
>>> flush_all_results()  # Must call before exit

>>> # Strategy control
>>> from core.resume import is_rate_limited, should_skip_test, build_completed_keys
>>> if is_rate_limited("Error 429"):
...     print("Rate limit detected")

>>> # API interaction
>>> from core.timecho import forecast
>>> forecast(data)
"""

__all__ = [
    "models",
    "results",
    "resume",
    "timecho",
]

