#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
core/dataResults.py —— Result Data Processing
====================================
Function: Provides common utility functions for data cleaning, result querying, etc.

Author: Janesong
Create Date: 2026/07/19
"""

import numpy as np
from typing import Dict, List, Optional, Any, Set


def clean_nan_values(obj: Any, _depth: int = 0, _seen: Set[int] = None, _max_depth: int = 100) -> Any:
    """
    Recursively clean NaN values, converting to None (JSON-compatible)

    Args:
        obj: Object to be processed (dict, list, or other types)
        Safety Measures:
            _depth: Current recursion depth (internal use)  当前递归深度（内部使用）
            _max_depth: Tracks the IDs of visited objects to prevent infinite recursion caused by circular references (internal use)
            _seen: Maximum recursion depth to prevent stack overflow due to excessive nesting (internal use)

    Returns:
        Cleaned object, NaN/Inf replaced with None.

    Example:
        >>> data = {"mae": np.nan, "rmse": 0.5, "tags": [np.inf, 1.0]}
        >>> clean_nan_values(data)
        {'mae': None, 'rmse': 0.5, 'tags': [None, 1.0]}
    """
    if _depth > _max_depth:
        print(f"clean_nan_values: Recursion depth exceeded {_max_depth}, skipping remaining cleaning.")
        return obj

    # Circular reference protection (Detection required for mutable objects like dict and list)
    if isinstance(obj, (dict, list)):
        if _seen is None:
            _seen = set()
        obj_id = id(obj)
        if obj_id in _seen:
            return obj
        _seen.add(obj_id)

    if isinstance(obj, dict):
        return {k: clean_nan_values(v, _depth + 1, _seen, _max_depth) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan_values(item, _depth + 1, _seen, _max_depth) for item in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, (np.floating, np.integer)):
        # Handle numpy numeric types
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    return obj


def get_results(results_data: List[Dict[str, Any]], 
               model_id: str, 
               scene_prefix: str, 
               pass_name: str = "Preprocessed") -> Optional[Dict[str, Any]]:
    """
    Precisely retrieve test results for a specific model, scene, and round from result list
    
    Args:
        results_data: Result data list (records read from CSV)
        model_id: Model ID (e.g., "Timer-XL-1.0", "TimesFM-2.0")
        scene_prefix: Scene prefix (e.g., "S0", "S1", "S4")
        pass_name: Round name ("Raw" or "Preprocessed")
    
    Returns:
        Matching result dictionary, returns None if not found
    
    Example:
        >>> results = [
        ...     {"model_id": "Timer-3.5", "scene": "S0-Clean[Preprocessed]", "pass": "Preprocessed", "mae": 0.5},
        ...     {"model_id": "Timer-3.5", "scene": "S1-Missing5%[Raw]", "pass": "Raw", "mae": None}
        ... ]
        >>> get_results(results, "Timer-3.5", "S0", "Preprocessed")
        {'model_id': 'Timer-XL-1.0', 'scene': 'S0-Clean[Preprocessed]', 'pass': 'Preprocessed', 'mae': 0.5}
    """
    for r in results_data:
        if r["model_id"] == model_id and r["scene"].startswith(scene_prefix) and r["pass"] == pass_name:
            return r
    return None


