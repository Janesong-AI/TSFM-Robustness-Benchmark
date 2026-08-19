#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
core/results.py —— Test Result Manager
====================================
Module Purpose:
  Provides centralized management for test results, including result loading,
  caching, batch writing, and querying. Encapsulates business logic while
  leveraging utils layer for file operations.

Core Features:
  - Result persistence with batch buffering (reduce I/O overhead)
  - Historical result loading with error classification
  - Multi-dimensional result querying (by model, scene, pass)
  - Independent buffer per file (safe for concurrent tasks)

Author: Janesong
Create Date: 2026/07/19, Updated on 2026/08/17.
"""

from pathlib import Path
from typing import Any
from core.resume import is_rate_limited
from utils.files import append_to_csv, csv_exists_and_not_empty, read_csv_to_list


# Buffer Manager (Internal Implementation)
class _ResultBufferManager:
    """
    Result buffer manager for batch writing optimization.

    Design:
        - One buffer per file (safe for concurrent tasks)
        - Auto-flush when reaching threshold
        - Manual flush on demand
    """

    def __init__(self, default_batch_size: int = 20):
        """
        Initialize buffer manager.

        Args:
            default_batch_size: Default batch size for auto-flush (default 20)
        """
        self._buffers: dict[str, list[dict[str, Any]]] = {}
        self._batch_sizes: dict[str, int] = {}
        self._default_batch_size = default_batch_size

    def append(
        self,
        file_path: str,
        result: dict[str, Any],
        batch_size: int | None = None
    ) -> int:
        """
        Append result to buffer, return current buffer size.

        Args:
            file_path: Result file path
            result: Single result dictionary
            batch_size: Batch size for this file (None = use default)

        Returns:
            Current buffer size after appending
        """
        # Initialize buffer if not exists
        if file_path not in self._buffers:
            self._buffers[file_path] = []
            if batch_size is not None:
                self._batch_sizes[file_path] = batch_size
            elif file_path not in self._batch_sizes:
                self._batch_sizes[file_path] = self._default_batch_size

        # Append to buffer
        self._buffers[file_path].append(result)
        return len(self._buffers[file_path])

    def should_flush(self, file_path: str) -> bool:
        """Check if buffer should be flushed."""
        if file_path not in self._buffers:
            return False
        return len(self._buffers[file_path]) >= self._batch_sizes[file_path]

    def flush(self, file_path: str) -> int:
        """
        Flush buffer to CSV file.

        Returns:
            Number of records flushed
        """
        if file_path not in self._buffers:
            return 0

        buffer = self._buffers[file_path]
        if not buffer:
            return 0

        # Batch write
        try:
            append_to_csv(file_path, buffer)
            count = len(buffer)
            print(f"Batch written {count} records to {Path(file_path).name}")

            # Clear buffer
            self._buffers[file_path] = []
            return count

        except Exception as exp:
            print(f"  Failed to flush buffer: {exp}")
            raise

    def flush_all(self) -> dict[str, int]:
        """
        Flush all buffers (call this before program exit).

        Returns:
            Dict of {file_path: record_count}
        """
        flush_results = {}

        for file_path in list(self._buffers.keys()):
            count = self.flush(file_path)
            if count > 0:
                flush_results[file_path] = count

        return flush_results

    def get_buffer_size(self, file_path: str) -> int:
        """Get current buffer size for a file."""
        return len(self._buffers.get(file_path, []))

# Global buffer manager instance (singleton)
_buffer_manager = _ResultBufferManager(default_batch_size=20)


def load_results_from_csv(result_csv_path_file: str) -> tuple[list[dict[str, Any]], int]:
    """
    Load historical results from CSV with error classification.
    
    This method reads existing results and classifies them into:
        - Successful records
        - Permanent failures (non-rate-limit errors)
        - Rate-limit errors (429)

    Args:
        result_csv_path_file: Result CSV file path

    Returns:
        (all_records, non_rate_limit_error)
        - all_records: List of all records (each row as dict)
        - non_rate_limit_error: Count of non-rate-limit errors
    """
    if not csv_exists_and_not_empty(result_csv_path_file):
        print(f"{Path(result_csv_path_file).name} not found, starting fresh")
        return [], 0

    try:
        all_records = read_csv_to_list(result_csv_path_file)

        # Classify error types
        non_rate_limit_error = 0
        retry_count = 0

        for record in all_records:
            success_val = record.get("success", "")
            if str(success_val).strip().lower() == "true":
                continue

            # Classify failure reason
            if is_rate_limited(str(record.get("error", ""))):
                retry_count += 1
            else:
                non_rate_limit_error += 1

        msg = f"Loaded {Path(result_csv_path_file).name}: {len(all_records)} records"
        success_count = len(all_records) - non_rate_limit_error - retry_count
        msg += f" (Success: {success_count}"

        if non_rate_limit_error > 0:
            msg += f", Failed: {non_rate_limit_error}"
        if retry_count > 0:
            msg += f", Pending Retry: {retry_count}"
        msg += ")"
        print(msg)

        return all_records, non_rate_limit_error

    except Exception as exp:
        print(f"Failed to load {Path(result_csv_path_file).name}: {exp}")
        return [], 0


def append_result_to_csv(
    result_csv_path_file: str,
    result: dict[str, Any],
    batch_size: int = 20,
    force_flush: bool = False,
    validate: bool = True
) -> None:
    """
    Append test result to CSV with batch buffering.

    Features:
        - Batch buffering to reduce I/O overhead
        - Auto-flush when buffer reaches batch_size
        - Independent buffer per file (safe for concurrent tasks)

    Usage:
        # Normal append (buffered)
        append_result_to_csv("./results.csv", result)

        # Force flush immediately
        append_result_to_csv("./results.csv", result, force_flush=True)

        # Custom batch size
        append_result_to_csv("./results.csv", result, batch_size=50)

    Args:
        result_csv_path_file: Result CSV file path
        result: Single result dictionary
        batch_size: Batch size for auto-flush (default 20)
        force_flush: Force flush immediately (default False)
        validate: Validate result format (default True)
    """

    # Business logic 2: Field normalization
    result = _normalize_result(result)

    # Business logic 3: Append to buffer
    current_size = _buffer_manager.append(
        result_csv_path_file,
        result,
        batch_size=batch_size
    )

    # Business logic 4: Determine whether to flush
    should_flush = force_flush or _buffer_manager.should_flush(result_csv_path_file)

    if should_flush:
        _buffer_manager.flush(result_csv_path_file)
        print(f"Flushed buffer (size={current_size}) for {Path(result_csv_path_file).name}")


def flush_all_results() -> dict[str, int]:
    """
    Flush all result buffers (call before program exit).

    Returns:
        Dict of {file_path: flushed_record_count}

    Example:
        >>> # At the end of your script
        >>> from core.results import flush_all_results
        >>> flush_results = flush_all_results()
        >>> print(f"Flushed: {flush_results}")
    """
    return _buffer_manager.flush_all()


def get_results(results_data: list[dict[str, Any]], 
               model_id: str,
               scene_prefix: str,
               pass_name: str = "Preprocessed") -> dict[str, Any] | None:
    """
    Retrieve the first matching test result for a specific model, scene, and pass.
    
    Args:
        results_data: List of result dictionaries (typically from CSV).
        model_id: Model identifier (e.g., "Timer-3.0", "Timer-3.5")
        scene_prefix: Scene prefix to match (e.g., "S0", "S1", "S4")
                     Uses prefix matching, so "S0" matches "S0-Clean[Preprocessed]".
        pass_name: Pass name ("Raw" or "Preprocessed"). Defaults to "Preprocessed".

    Returns:
        Matching result dictionary, or None if not found

    Example:
        >>> results = [
        ...     {"model_id": "Timer-3.5", "scene": "S0-Clean[Preprocessed]", "pass": "Preprocessed", "mae": 0.5},
        ...     {"model_id": "Timer-3.0", "scene": "S1-Missing5%[Raw]", "pass": "Raw", "mae": None}
        ... ]
        >>> get_results(results, "Timer-3.5", "S0", "Preprocessed")
        {'model_id': 'Timer-3.5', 'scene': 'S0-Clean[Preprocessed]', 'pass': 'Preprocessed', 'mae': 0.5}
    """
    for record in results_data:
        if (record.get("model_id") == model_id and 
            record.get("scene", "").startswith(scene_prefix) and 
            record.get("pass") == pass_name):
            return record
    return None

def get_results_by_model(results_data: list[dict[str, Any]], 
                         model_id: str) -> list[dict[str, Any]]:
    """
    Retrieve all results for a specific model.

    Args:
        results_data: List of result dictionaries
        model_id: Model identifier (e.g., "Timer-3.0", "Timer-3.5")

    Returns:
        List of matching result dictionaries. Empty list if none found.

    Example:
        >>> results = [
        ...     {"model_id": "Timer-3.0", "scene": "S0-Clean[Preprocessed]", "pass": "Preprocessed", "mae": 0.5},
        ...     {"model_id": "Timer-3.5", "scene": "S1-Missing5%[Raw]", "pass": "Raw", "mae": None}
        ... ]
        >>> get_results_by_model(results, "Timer-3.5")
        [{'model_id': 'Timer-3.5', 'scene': 'S1-Missing5%[Raw]', 'pass': 'Raw', 'mae': None}]
    """
    return [record for record in results_data if record.get("model_id") == model_id]

def get_results_by_scene(results_data: list[dict[str, Any]],
                         scene_prefix: str) -> list[dict[str, Any]]:
    """
    Retrieve all results for a specific scene prefix.

    Args:
        results_data: List of result dictionaries
        scene_prefix: Scene prefix (e.g., "S0", "S1", "S4")

    Returns:
        List of matching result dictionaries. Empty list if none found.

    Example:
        >>> results = [
        ...     {"model_id": "Timer-3.5", "scene": "S0-Clean[Preprocessed]", "pass": "Preprocessed", "mae": 0.5},
        ...     {"model_id": "Timer-3.5", "scene": "S1-Missing5%[Raw]", "pass": "Raw", "mae": None}
        ... ]
        >>> get_results_by_scene(results, "S0")
        [{'model_id': 'Timer-3.5', 'scene': 'S0-Clean[Preprocessed]', 'pass': 'Preprocessed', 'mae': 0.5}]
    """
    return [record for record in results_data  if record.get("scene", "").startswith(scene_prefix)]

def get_results_by_pass(results_data: list[dict[str, Any]], 
                        pass_name: str) -> list[dict[str, Any]]:
    """
    Retrieve all results for a specific pass.

    Args:
        results_data: List of result dictionaries.
        pass_name: Pass name ("Raw" or "Preprocessed").

    Returns:
        List of matching result dictionaries. Empty list if none found.

    Example:
        >>> results = [
        ...     {"model_id": "Timer-3.0", "scene": "S0-Clean[Preprocessed]", "pass": "Preprocessed", "mae": 0.5},
        ...     {"model_id": "Timer-3.5", "scene": "S1-Missing5%[Raw]", "pass": "Raw", "mae": None}
        ... ]
        >>> get_results_by_pass(results, "Preprocessed")
        [{'model_id': 'Timer-3.0', 'scene': 'S0-Clean[Preprocessed]', 'pass': 'Preprocessed', 'mae': 0.5}]
    """
    return [record for record in results_data if record.get("pass") == pass_name]


def _normalize_result(result: dict) -> dict:
    """Normalize result format (business logic)."""
    from utils.data_sanitizer import clean_nan_values
    return clean_nan_values(result)

