#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
utils/runner.py — Test Runner Core
Core runner: test discovery + single-case execution + result tracking (in-memory)

Design Principles:
  - This module is the [Execution Capability Layer], no CLI / argparse / print
  - Only responsible for discovering test cases and executing their main() functions
  - Both run.py and conftest.py reuse the capabilities of this module
  - Batch scheduling is delegated to pytest, but the primitives for discovery / execution / result are defined here
"""

import os
import sys
import ast
import time
import importlib
import traceback
import multiprocessing as mp
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field
from enum import Enum
from queue import Empty

# Bootstrap (defensive)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from config.settings import PROJECT_ROOT
from utils.log import get_logger


# ============================================================
# 1. Data Models — shared by runner / pytest / resume
# ============================================================

class TestStatus(Enum):
    """Test status enumeration"""
    PENDING   = "PENDING"
    RUNNING   = "RUNNING"
    PASSED    = "PASSED"
    FAILED    = "FAILED"
    SKIPPED   = "SKIPPED"
    ERROR     = "ERROR"
    TIMEOUT   = "TIMEOUT"

    @property
    def is_success(self) -> bool:
        return self == TestStatus.PASSED

    @property
    def is_failure(self) -> bool:
        return self in (TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT)


@dataclass
class TestResult:
    """
    Execution result of a single test case (in-memory).
    Used by run.py for printing, conftest.py for assertions, and core/results.py for persistence.
    """
    module_path: str
    status: TestStatus = TestStatus.PENDING
    duration: float = 0.0
    error: str | None = None
    start_time: float | None = None
    end_time: float | None = None
    retries: int = 0

    def mark_start(self):
        self.start_time = time.time()
        self.status = TestStatus.RUNNING

    def mark_end(self, status: TestStatus, error: str | None = None):
        self.end_time = time.time()
        self.duration = self.end_time - (self.start_time or self.end_time)
        self.status = status
        self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Dictionary provided for core/results.py to persist to disk."""
        return {
            "module_path": self.module_path,
            "status": self.status.value,
            "duration": round(self.duration, 3),
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "retries": self.retries,
        }

    def __str__(self):
        icon = {
            TestStatus.PASSED:  "✓",
            TestStatus.FAILED:   "✗",
            TestStatus.SKIPPED:  "○",
            TestStatus.ERROR:    "⚠",
            TestStatus.TIMEOUT:  "⏱",
        }.get(self.status, "?")
        retry_str = f" (retries={self.retries})" if self.retries else ""
        return f"{icon} {self.module_path} ({self.duration:.2f}s){retry_str}"


@dataclass
class BatchReport:
    """Batch execution summary report (in-memory), printed by run.py or conftest.py."""
    results: list[TestResult] = field(default_factory=list)
    total_duration: float = 0.0

    def add(self, result: TestResult):
        self.results.append(result)
        self.total_duration += result.duration

    @property
    def total(self):      return len(self.results)
    @property
    def passed(self):      return sum(1 for r in self.results if r.status.is_success)
    @property
    def failed(self):      return sum(1 for r in self.results if r.status.is_failure)
    @property
    def skipped(self):     return sum(1 for r in self.results if r.status == TestStatus.SKIPPED)

    def summary(self) -> str:
        return (
            f"  Total: {self.total}  |  "
            f"Passed: {self.passed}  |  "
            f"Failed: {self.failed}  |  "
            f"Skipped: {self.skipped}  |  "
            f"Duration: {self.total_duration:.2f}s"
        )


# ============================================================
# 2. Test Discoverer — AST static analysis, zero side effects
# ============================================================

class TestDiscoverer:
    """
    Discovers test modules via AST static analysis.
    Never imports modules — zero side effects.

    Usage:
      - run.py --list: List all tests
      - conftest.py: Can replace pytest_collect_file for pre-filtering
      - core/resume.py: Determine the full scope for checkpoint recovery
    """

    ENTRY_POINTS = ("main", "run", "start")
    TEST_PATTERNS = ("_test.py", "_test_v1.py", "_test_v2.py", "_test_v3.py")

    def __init__(self, logger=None):
        self.logger = logger or get_logger("discoverer")
        self.features_root = PROJECT_ROOT / "features"

    def discover(
        self,
        directory: Path | None = None,
        tags: list[str] | None = None,
        skip: list[str] | None = None,
    ) -> list[str]:
        """
        Discover all test modules and return a list of module paths.
        """
        search_root = Path(directory) if directory else self.features_root

        if not search_root.exists():
            self.logger.warning(f"Search directory does not exist: {search_root}")
            return []

        skip = skip or []
        discovered = []

        for py_file in sorted(search_root.rglob("*.py")):
            if py_file.name.startswith("__"):
                continue
            if not self._is_test_file(py_file):
                continue

            module_path = self._file_to_module_path(py_file)
            if module_path is None:
                continue
            if module_path in skip:
                self.logger.info(f"Skipped (--skip): {module_path}")
                continue
            if tags and not self._match_tags(module_path, tags):
                continue
            if not self._has_entry_point_ast(py_file):
                self.logger.debug(f"Skipped (no entry function): {module_path}")
                continue

            discovered.append(module_path)
            self.logger.debug(f"Discovered: {module_path}")

        self.logger.info(f"Total {len(discovered)} test module(s) discovered")
        return discovered

    def _is_test_file(self, py_file: Path) -> bool:
        name = py_file.name
        return any(name.endswith(p) for p in self.TEST_PATTERNS)

    def _file_to_module_path(self, py_file: Path) -> str | None:
        try:
            rel = py_file.resolve().relative_to(PROJECT_ROOT)
            if rel.suffix == ".py":
                rel = rel.with_suffix("")
            return str(rel).replace("/", ".").replace(os.sep, ".")
        except ValueError:
            return None

    def _match_tags(self, module_path: str, tags: list[str]) -> bool:
        parts = module_path.replace(".", "/").split("/")
        return any(tag in parts or tag in module_path for tag in tags)

    def _has_entry_point_ast(self, py_file: Path) -> bool:
        """
        AST static analysis: check whether the file defines an entry function.
        Never imports the module to avoid triggering top-level side effects.
        """
        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            top_funcs = {
                node.name for node in ast.iter_child_nodes(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            return any(ep in top_funcs for ep in self.ENTRY_POINTS)
        except SyntaxError as synExp:
            self.logger.warning(f"Syntax error in {py_file}: {synExp}")
            return False
        except Exception as exp:
            self.logger.warning(f"AST analysis failed for {py_file}: {exp}")
            return False


# ============================================================
# 3. Test Runner — single-case execution with timeout + retry
# ============================================================

class TimeoutError_(Exception):
    """Test execution timed out"""
    pass


class TestRunner:
    """
    Test runner: imports and invokes the entry function of a single test module.
    Entry function priority: main() > run() > start()
    """

    ENTRY_POINTS = ("main", "run", "start")

    def __init__(self, logger=None, default_timeout: int = 0, default_retries: int = 0):
        self.logger = logger or get_logger("runner")
        self.default_timeout = default_timeout
        self.default_retries = default_retries

    def run_single(self, module_path, timeout=None, retries=None):
        timeout = timeout if timeout is not None else self.default_timeout
        retries = retries if retries is not None else self.default_retries
        result = TestResult(module_path=module_path)

        # First, get the entry function name via AST (zero side effects)
        entry_name = self._find_entry_name_ast(module_path)
        if entry_name is None:
            result.mark_end(TestStatus.SKIPPED, "No entry function found")
            return result

        attempt = 0
        max_attempts = retries + 1

        while attempt < max_attempts:
            attempt += 1
            result.retries = attempt - 1
            result.mark_start()

            try:
                if timeout > 0:
                    # Timeout mode: main process does not import, delegates directly to subprocess
                    self._run_with_timeout(module_path, entry_name, timeout)
                else:
                    # Normal mode: main process imports and executes
                    module = importlib.import_module(module_path)
                    func = getattr(module, entry_name)
                    func()

                result.mark_end(TestStatus.PASSED)
                self.logger.info(f" Pass: {module_path}")
                return result

            except TimeoutError_ as timeExp:
                result.mark_end(TestStatus.TIMEOUT, str(timeExp))
                if attempt < max_attempts:
                    self.logger.warning(f" Timeout, will retry ({attempt}/{max_attempts})")
                    continue
                self.logger.error(f" Timed out and retries exhausted: {module_path}")
                return result

            except Exception as exp:
                error_detail = traceback.format_exc()
                if attempt < max_attempts:
                    self.logger.warning(f" Attempt {attempt} failed, will retry")
                    self.logger.debug(error_detail)
                    continue
                self.logger.error(f" Fail: {module_path}\n{error_detail}")
                result.mark_end(TestStatus.FAILED, str(exp))
                return result
        return result


    def _find_entry_name_ast(self, module_path: str) -> str | None:
        """
        AST static analysis: find the entry function name.
        Does not import the module to avoid triggering top-level side effects.

        Returns: Entry function name (e.g., "main") or None (if not found)
        """
        # module_path -> file path
        parts = module_path.replace(".", "/")
        py_file = PROJECT_ROOT / f"{parts}.py"

        if not py_file.exists():
            self.logger.warning(f"File not found: {py_file}")
            return None

        try:
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_file))
            top_funcs = {
                node.name for node in ast.iter_child_nodes(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            # Return the first match based on priority
            for ep in self.ENTRY_POINTS:
                if ep in top_funcs:
                    return ep
            return None
        except SyntaxError as synExp:
            self.logger.warning(f"Syntax error in {py_file}: {synExp}")
            return None
        except Exception as exp:
            self.logger.warning(f"AST analysis failed for {py_file}: {exp}")
            return None


    def _run_with_timeout(self, module_path: str, entry_name: str, timeout: int):
        """
        Implements timeout control using multiprocessing.Process (cross-platform).
        The process is forcibly terminated on timeout, simulating the hard interrupt effect of the original SIGALRM.
        """
        result_queue = mp.Queue()
        process = mp.Process(target=self._wrap_func, args=(module_path, entry_name, result_queue))
        process.start()
        process.join(timeout)

        if process.is_alive():
            process.terminate()
            process.join()
            raise TimeoutError_(f"Execution timed out ({timeout}s)")

        if process.exitcode != 0:
            raise RuntimeError(
                f"Subprocess crashed (exitcode={process.exitcode})"
            )

        # Check if the subprocess exited due to an exception
        try:
            error_pkg = result_queue.get_nowait()
            if error_pkg is not None:
                raise RuntimeError(
                    f"{error_pkg['type']}: {error_pkg['message']}\n"
                    f"{error_pkg['traceback']}"
                )
        except Empty:
            # Queue is empty and process exited normally
            pass
        finally:
            result_queue.close()
            result_queue.join_thread()

    @staticmethod
    def _wrap_func(module_path: str, entry_name: str, queue):
        try:
            if str(_PROJECT_ROOT) not in sys.path:
                sys.path.insert(0, str(_PROJECT_ROOT))

            module = importlib.import_module(module_path)
            func = getattr(module, entry_name)
            func()
            queue.put(None)  # Normal completion marker
        except Exception as exp:
            queue.put({
                "type": type(exp).__name__,
                "message": str(exp),
                "traceback": traceback.format_exc()
            })  # Pass exception details to the main process


# ============================================================
# 4. Path Resolution Utility
# ============================================================

def parse_module_path(raw_path: str) -> str:
    """
    Resolve a user-provided path into a standard module path.
    Supports:
      - features.futureCovs.dirtyData.dirty_test
      - ./features/futureCovs/dirtyData/dirty_test.py
      - features/futureCovs/dirtyData/dirty_test.py
    """
    if raw_path.startswith("./") or raw_path.endswith(".py") or "/" in raw_path:
        file_path = Path(raw_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File does not exist: {file_path}")
        rel_path = file_path.relative_to(PROJECT_ROOT)
        if rel_path.suffix == ".py":
            rel_path = rel_path.with_suffix("")
        module_path = str(rel_path).replace("/", ".").replace(os.sep, ".")
    else:
        module_path = raw_path
    return module_path
