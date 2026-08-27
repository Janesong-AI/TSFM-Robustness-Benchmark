#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
utils - Infrastructure Utility Layer

This package provides stateless pure functions and generic entity wrappers, serving as the
underlying support for the entire project. It currently includes:

Modules:
-------
log — Logging Management
  Centralized logging configuration and management.
  Provides a unified interface for log initialization, handler management, and context propagation.

client.py — TimechoAI Client Connection
  Provides factory functions get_timecho_client() / get_timecho_async_client(),
  unifying the creation and lifecycle management of TimechoAIClient / TimechoAIAsyncClient instances.
  Prevents duplicate handling of API_KEY and initialization logic across modules.

data_sanitizer.py — Data Sanitization & Type Safety
  Handles NaN/Inf values for JSON compatibility and provides robust type conversion.
  Ensures data integrity before persistence or transmission.

files.py — File Operation Utilities
  Provides functionality for reading, writing, appending, and status checking for files (CSV/JSON).
  Unified error handling and path management.

metrics.py — Evaluation Metrics Calculator
  Provides standard evaluation metrics (MAE, RMSE, MAPE) for time series forecasting models.
  Pure mathematical calculation functions without side effects.

runner.py — Test Runner Core
  Test discovery (AST static analysis), single-case execution (timeout + retry), result tracking.
  Provides the execution primitives shared by run.py, conftest.py, and core/resume.py.

concurrent.py —— (Internal) Concurrent Utilities
  Provides thread-safe primitives (FileLock, ProcessSafeCache) used internally.
  NOT exposed in __all__. Used by results.py for file operation safety.

Usage Conventions:
--------------------------
1. Business modules (e.g., features/) should access TimechoAI services indirectly through core.timecho.
2. The core layer is the only module that directly uses utils.client.
3. Files and data_sanitizer can be used directly by core layers, but features should prefer core interfaces.

Import Path Examples:
-----------------------------
>>> # Recommended: Access via core layer
>>> from core.timecho import forecast
>>> from core.results import load_results_from_csv

>>> # Utils layer usage (for core layer developers)
>>> from utils.files import save_to_csv, append_to_csv
>>> from utils.log import get_logger, setup_logging
>>> from utils.metrics import calc_metrics, calc_diff, evaluate_prediction
>>> from utils.data_sanitizer import clean_nan_values, safe_float
>>> from utils.runner import parse_module_path
"""

__all__ = [
    "client",
    "data_sanitizer",
    "files",
    "log",
    "metrics",
    "test_helpers",
    "runner",
]
