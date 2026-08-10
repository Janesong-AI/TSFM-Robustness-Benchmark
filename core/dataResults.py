#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
core/dataResults.py —— Result Data Processing
====================================
Function: Provides common utility functions for data cleaning and result querying, etc.

Author: Janesong
Create Date: 2026/07/19
"""

import numpy as np
import json
import re
from typing import Dict, List, Optional, Any


def get_results(results_data: List[Dict[str, Any]], 
               model_id: str, 
               scene_prefix: str, 
               pass_name: str = "Preprocessed") -> Optional[Dict[str, Any]]:
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
    for r in results_data:
        if (r.get("model_id") == model_id and 
            r.get("scene", "").startswith(scene_prefix) and 
            r.get("pass") == pass_name):
            return r
    return None

def get_results_by_model(results_data: List[Dict[str, Any]], 
                         model_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve all test results for a specific model from the result list

    Args:
        results_data: List of result dictionaries (records read from CSV)
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
    return [r for r in results_data if r.get("model_id") == model_id]

def get_results_by_scene(results_data: List[Dict[str, Any]], 
                         scene_prefix: str) -> List[Dict[str, Any]]:
    """
    Retrieve all test results for a specific scene prefix.

    Args:
        results_data: List of result dictionaries.
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
    return [r for r in results_data 
            if r.get("scene", "").startswith(scene_prefix)]

def get_results_by_pass(results_data: List[Dict[str, Any]], 
                        pass_name: str) -> List[Dict[str, Any]]:
    """
    Retrieve all test results for a specific pass.

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
    return [r for r in results_data if r.get("pass") == pass_name]


def clean_nan_values(obj: Any, 
                      _depth: int = 0, 
                      _max_depth: int = 100) -> Any:
    """
    Recursively clean NaN/Inf values, converting them to None (JSON-compatible).

    Note: Circualr reference detection is removed since JSON/CSV data sources are tree-structured and cannot contain cycles.

    Args:
        obj: Object to be processed (dict, list, or other types)
        Safety Measures:
            _depth: Current recursion depth (internal use)
            _max_depth: Tracks the IDs of visited objects to prevent infinite recursion caused by circular references (internal use)

    Returns:
        Cleaned object with NaN/Inf replaced by None.

    Example:
        >>> import numpy as np
        >>> data = {"mae": np.nan, "rmse": 0.5, "tags": [np.inf, 1.0]}
        >>> clean_nan_values(data)
        {'mae': None, 'rmse': 0.5, 'tags': [None, 1.0]}
    """
    # Depth protection
    if _depth > _max_depth:
        print(f"clean_nan_values: Recursion depth exceeded {_max_depth}, skipping remaining cleaning.")
        return obj

    if isinstance(obj, dict):
        return {k: clean_nan_values(v, _depth + 1, _max_depth) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_nan_values(item, _depth + 1, _max_depth) for item in obj]
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.floating, np.integer)):
        # Handle numpy numeric types
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    return obj

def load_json_with_nan(json_str: str) -> Any:
    """
    Safely parses JSON strings containing NaN / Infinity / -Infinity.

    Replaces non-standard JSON values with 'null' before parsing.

    Args:
        json_str: JSON string potentially containing NaN/Infinity values.

    Returns:
        Parsed Python object (dict, list, or primitive type).

    Raises:
        TypeError: If input is not a string.
        json.JSONDecodeError: If the sanitized string is not valid JSON.

    Note:
        The regex uses negative lookbehind/lookahead to ensure only
        standalone tokens are matched. For example, 'NaN' in "myNaN" will NOT be replaced.

    Example:
        >>> load_json_with_nan('{"value": NaN, "neg_inf": -Infinity, "text": "myNaN"}')
        {'value': None, 'neg_inf': None, 'text': 'myNaN'}
    """
    if not isinstance(json_str, str):
        raise TypeError(f"Expected str type, received {type(json_str).__name__}")

    # Replace non-standard JSON values using regex with negative lookbehind/lookahead
    # Handles: NaN, Infinity, -Infinity
    # Does NOT replace tokens inside strings like "myNaN"
    sanitized = re.sub(
        r'(?<![.\w])(NaN|-?Infinity)(?![.\w])',
        'null',
        json_str
    )

    return json.loads(sanitized)
