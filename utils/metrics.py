#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
utils/metrics.py —— Evaluation Metrics Calculator

Provides standard evaluation metrics for time series forecasting models.

Functions:
  - calc_metrics(): Compute MAE, RMSE, MAPE
  - calc_diff(): Compute mean absolute difference between predictions

Author: Janesong
Create Date: 2026/08/17.
"""

import numpy as np


def calc_metrics(
    predictions: np.ndarray | None,
    ground_truth: np.ndarray,
    threshold: float = 1e-7   # Threshold for valid MAPE calculation
) -> dict[str, float | None]:
    """
    Calculate MAE / RMSE / MAPE.

    Args:
        predictions: Predicted values array
        ground_truth: Ground truth values array
        threshold: Minimum |ground_truth| for valid MAPE calculation to prevent division by zero.

    Returns:
        dict: {"MAE": ..., "RMSE": ..., "MAPE": ...}
        MAE: Mean Absolute Error
        RMSE: Root Mean Squared Error
        MAPE: Mean Absolute Percentage Error
    """
    if predictions is None:
        return {"MAE": None, "RMSE": None, "MAPE": None}

    # 1. Calculate MAE and RMSE on the full dataset
    mae = float(np.mean(np.abs(predictions - ground_truth)))
    rmse = float(np.sqrt(np.mean((predictions - ground_truth) ** 2)))

    # 2. MAPE: Calculate only on data points with valid denominators (mask out near-zero/zero values)
    mask = np.abs(ground_truth) > threshold
    
    if np.any(mask):
        # Calculate MAPE only for valid points
        mape = float(np.mean(
            np.abs((predictions[mask] - ground_truth[mask]) / ground_truth[mask])
        ) * 100)
    else:
        # All ground truth values are close to 0; MAPE is undefined
        mape = None

    return {"MAE": mae, "RMSE": rmse, "MAPE": mape}


def calc_diff(pred1: np.ndarray | None, pred2: np.ndarray | None) -> float | None:
    """
    Calculate the mean absolute difference between two prediction arrays.

    Args:
        pred1: First prediction array
        pred2: Second prediction array

    Returns:
        Mean absolute difference; returns None if either input is None.
    """
    if pred1 is None or pred2 is None:
        return None

    return float(np.mean(np.abs(pred1 - pred2)))

