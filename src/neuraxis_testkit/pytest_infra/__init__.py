
"""

Modules:
-------
manifest_loader.py 


models.py —— Shared Data Models
  Defines core data structures (TestStatus, TestResult, BatchReport) used across
  the entire framework. Supports i18n via TEST_LANG environment variable.

Import Path Examples:
-----------------------------
>>> # Data models
>>> from pytest_infra.models import TestStatus, TestResult, BatchReport
>>> result = TestResult(module_path="test_xxx.py")
>>> result.mark_start()
>>> result.mark_end(TestStatus.PASSED)
>>> print(result.status.get_display("PASSED"))  # i18n display
"""

__all__ = [
    "collection",
    "conftest",
    "manifest_loader",
    "models",
    "resume",
    "session_manager",
]