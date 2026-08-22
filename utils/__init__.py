#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
utils - Infrastructure Utility Layer

This package provides stateless pure functions and generic entity wrappers, serving as the
underlying support for the entire project. It currently includes:

Modules:
-------
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

log — Logging Management
  Centralized logging configuration and management.
  Provides a unified interface for log initialization, handler management, and context propagation.

metrics.py — Evaluation Metrics Calculator
  Provides standard evaluation metrics (MAE, RMSE, MAPE) for time series forecasting models.
  Pure mathematical calculation functions without side effects.

runner.py — Test Runner Core
  Test discovery (AST static analysis), single-case execution (timeout + retry), result tracking.
  Provides the execution primitives shared by run.py, conftest.py, and core/resume.py.

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

from .client import (
    get_timecho_client,
    get_timecho_async_client,
    reset_client,
    reset_async_client,
)
from .data_sanitizer import (
    clean_nan_values,
    load_json_with_nan,
    safe_float,
    safe_int,
)
from .files import (
    save_to_csv,
    append_to_csv,
    save_with_json_backup,
    read_csv_to_dataframe,
    read_csv_to_list,
    csv_exists_and_not_empty,
    CSVFileError,
)
from utils.log import (
    Logger,
    get_logger,
    setup_logging,
    get_default_logger,
    set_global_level,
    flush_all_logs,
    get_log_file_path,
    log_execution,
    log_time,
    LogLevelContext,
)
from .metrics import (
    calc_metrics,
    calc_diff,
    evaluate_prediction
)
# ── runner.py must be imported AFTER utils.log ──────────────
from .runner import (
    parse_module_path,
)

__all__ = [
    # --- client.py ---
    "get_timecho_client",
    "get_timecho_async_client",
    "reset_client",
    "reset_async_client",
    # --- data_sanitizer.py ---
    "clean_nan_values",
    "load_json_with_nan",
    "safe_float",
    "safe_int",
    # --- files.py ---
    "save_to_csv",
    "append_to_csv",
    "save_with_json_backup",
    "read_csv_to_dataframe",
    "read_csv_to_list",
    "csv_exists_and_not_empty",
    "CSVFileError",
    # --- log ---
    'Logger',
    'get_logger',
    'setup_logging',
    'get_default_logger',
    'set_global_level',
    'flush_all_logs',
    'get_log_file_path',
    'log_execution',
    'log_time',
    'LogLevelContext',
    # --- metrics.py ---
    "calc_metrics",
    "calc_diff",
    "evaluate_prediction",
    # --- runner.py ---
    "parse_module_path",
]
