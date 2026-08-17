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

