#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TSFM-Robustness-Benchmark — Unified Entry Point

Usage:
  # Single test case
  python run.py features.futureCovs.dirtyData.dirty_test
  python run.py features.futureCovs.conceptDrift.concept_drift_test

  # File path is also acceptable
  python run.py ./features/futureCovs/dirtyData/dirty_test.py
  python run.py ./features/futureCovs/conceptDrift/concept_drift_test.py

  # To run all cases in batch, please use pytest
  #   pytest features/
  #   pytest features/ -k dirty
  #   pytest features/ -k concept_drift -v

Environment Variable Options:
  LOG_LEVEL=DEBUG              Set log level
  LOG_CONSOLE_OUTPUT=false     Disable console output
  LOG_FILE_OUTPUT=false        Disable file output
  LOG_MAX_BYTES=52428800       Set log file size limit (default 50MB)
"""

import os, sys, logging, argparse
import traceback
from pathlib import Path

# Bootstrap: Allow Python to find packages under the project root directory
_BOOTSTRAP_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_BOOTSTRAP_ROOT))

from config.settings import PROJECT_ROOT
from utils.log import get_logger, get_log_file_path, flush_all_logs, get_log_level
from utils.runner import TestRunner, TestStatus, parse_module_path

if sys.platform == "win32":
    # Change the console code page to UTF-8 (65001) to support Unicode output.
    # Redirect stdout (>nul) and stderr (2>&1) to suppress any command output or errors.
    os.system("chcp 65001 >nul 2>&1")

def main():
    parser = argparse.ArgumentParser(
        description="TSFM-Robustness-Benchmark Unified Entry Point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
For batch execution, please use pytest:
  pytest features/                    # Run all tests
  pytest features/ -k dirty           # Filter by name
  pytest features/ -k concept_drift   # Filter by name
  pytest features/ -v                 # Verbose output
""",
    )

    parser.add_argument(
        "module",
        help="Test module path (e.g., features.futureCovs.dirtyData.dirty_test)"
    )
    args = parser.parse_args()

    # ── Initialize logging ──
    logger = get_logger("run")
    log_file_path = get_log_file_path()

    # Log level: int -> readable name
    level_int = get_log_level()
    level_name = logging.getLevelName(level_int)

    logger.info("=" * 70)
    logger.info("Project started")
    logger.info("=" * 70)
    logger.info(f"Project root: {PROJECT_ROOT}")
    logger.info(f"Log file: {log_file_path}")
    logger.info(f"Log level: {level_name} ({level_int})")

    # ── Path resolution ──
    try:
        module_path = parse_module_path(args.module)
        logger.info(f"Started executing module: {module_path}")
    except FileNotFoundError as exp:
        logger.error(str(exp))
        sys.exit(1)

    # ── Execution ──
    runner = TestRunner(logger=logger)

    try:
        runner.run_single(module_path)
    except Exception as exp:
        error_detail = traceback.format_exc()
        logger.error(f"Execution failed:\n{error_detail}")
        sys.exit(1)

    finally:
        flush_all_logs()
        logger.info("=" * 70)
        logger.info("Project finished")
        logger.info("=" * 70)


if __name__ == "__main__":
    main()
