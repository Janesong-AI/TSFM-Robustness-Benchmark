"""
core —— Business Core Layer

Provides centralized management for business logic, state, and external interactions.
Serves as the bridge between the ``features`` layer and ``utils`` layer.

Modules:
-------
results.py —— Test Result Manager
  Manages result persistence (batch buffering), historical loading, and querying.
  Internally uses utils.concurrent for thread-safe file operations.

resume.py —— Strategy Controller
  Provides checkpoint resumption logic and rate limit detection strategy.

timecho.py —— TimechoAI Interaction Layer
    Encapsulates API requests and response handling, offering a unified high-level API.

Usage:
--------------
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

