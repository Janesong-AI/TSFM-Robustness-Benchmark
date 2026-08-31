#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
neuraxis_testkit/utils - Infrastructure Utility Layer

This package provides stateless pure functions and generic entity wrappers, serving as the
underlying support for the entire project. It currently includes:

Modules:
-------
log — Logging Management
  Centralized logging configuration and management.
  Provides a unified interface for log initialization, handler management, and context propagation.

data_sanitizer.py — Data Sanitization & Type Safety
  Handles NaN/Inf values for JSON compatibility and provides robust type conversion.
  Ensures data integrity before persistence or transmission.

files.py — File Operation Utilities
  Provides functionality for reading, writing, appending, and status checking for files (CSV/JSON).
  Unified error handling and path management.

runner.py — Test Runner Core
  Test discovery (AST static analysis), single-case execution (timeout + retry), result tracking.
  Provides the execution primitives shared by run.py, conftest.py, and core/resume.py.

concurrent.py —— (Internal) Concurrent Utilities
  Provides thread-safe primitives (FileLock, ProcessSafeCache) used internally.
  NOT exposed in __all__. Used by results.py for file operation safety.

Usage Conventions:
--------------------------
  Files and data_sanitizer can be used directly by core layers, but testcases should prefer core interfaces.

Import Path Examples:
-----------------------------
>>> # Utils layer usage (for core layer developers)
>>> from neuraxis_testkit.log import get_logger, setup_logging
>>> from neuraxis_testkit.utils.data_sanitizer import clean_nan_values, safe_float
>>> from neuraxis_testkit.utils.files import save_to_csv, append_to_csv
>>> from neuraxis_testkit.utils.runner import parse_module_path
"""

__all__ = [
    "log",
    "data_sanitizer",
    "files",
    "runner",
]
