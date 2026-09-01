#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
neuraxis_testkit/log - Neuraxis TestKit Logging Module

Provides a concise logging interface and hides internal implementation details.

Usage Examples:
    from neuraxis_testkit.log import get_logger, setup_logging

    logger = get_logger(__name__)
    logger.info("Hello World")
"""
import threading
from .core import Logger
from .decorators import log_execution, log_time
from .context import LogLevelContext
from .config import (
    get_log_file_path,
    get_log_level,
    LOGS_DIR,
    LOG_FILE_NAME,
    LOG_LEVEL,
)

# Convenience Functions
_default_logger_lock = threading.Lock()
_default_logger: Logger | None = None


def get_logger(name: str = "neuraxis", **kwargs) -> Logger:
    """
    Get a logger instance. Recommended to use module name for 'name'.

    Args:
        name: Name of the logger. It is recommended to use the module name.
        **kwargs: Optional configuration parameters to override defaults.

    Returns:
        Logger instance.

    Example:
        >>> logger = get_logger('testcases.futureCovs.dirtyData.test_dirty')
    """
    return Logger.get_logger(name, **kwargs)

def get_default_logger() -> Logger:
    """Get a default global logger for quick scripts."""
    global _default_logger
    with _default_logger_lock:
        if _default_logger is None:
            _default_logger = get_logger('default')
    return _default_logger


def setup_logging(**kwargs) -> Logger:
    """
    Initializes the logging system (typically called at project startup).

    Args:
        **kwargs: Optional configuration parameters to override defaults.

    Returns:
        Logger instance.
    
    Example:
        >>> # Called in run.py
        >>> logger = setup_logging(level='INFO')
    """
    return get_logger('root', **kwargs)

def set_global_level(level: str):
    """
    Modifies the log level for all instantiated loggers.

    Args:
        level: Log level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL).

    Raises:
        ValueError: If an invalid log level is provided.
    """
    from neuraxis_testkit.log.core import VALID_LEVELS
    level_upper = level.upper()
    if level_upper not in VALID_LEVELS:
        raise ValueError(f"Invalid log level: '{level}'. Valid options are: {', '.join(sorted(VALID_LEVELS))}")

    for logger in Logger._instances.values():
        logger.set_level(level_upper)


def flush_all_logs():
    """Forces all log handlers to flush immediately."""
    Logger.flush()


__all__ = [
    # Core Classes
    'Logger',
    # Convenience Functions
    'get_logger',
    'setup_logging',
    'get_default_logger',
    'set_global_level',
    'flush_all_logs',
    # Decorators
    'log_execution',
    'log_time',
    # Context Managers
    'LogLevelContext',
    # Configuration Related
    'get_log_file_path',
    'get_log_level',
    'LOGS_DIR',
    'LOG_FILE_NAME',
    'LOG_LEVEL',
]