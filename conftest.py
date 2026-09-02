
"""
Usage Examples: 用法示例
  pytest testcases/

  pytest testcases/ -k dirty
  pytest testcases/ -k dirty -v

  pytest testcases/ -m dirty
  pytest testcases/ -m "concept_drift and not slow"

  pytest testcases/futureCovs/dirtyData/test_dirty.py

  pytest testcases/futureCovs/dirtyData/test_dirty.py::test_dirty_basic

  pytest testcases/ -n auto

  pytest testcases/ --reruns 3 --reruns-delay 5

  pytest testcases/ --junitxml=outputs/reports/report.xml

  pytest testcases/ --lf
  pytest testcases/xxx --resume --resume-file "outputs/reports/report-<run-ts>.csv"

  pytest testcases/ -s --pdb

  python -m pytest --collect-only -q --output-dir=/tmp/x
"""

import pytest
from config.settings import PROJECT_ROOT, OUTPUT_DIR, LOGS_DIR, RESULTS_DIR

pytest_plugins = ["neuraxis_testkit.pytest_infra.conftest"]

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.set_defaults(
        project_root=str(PROJECT_ROOT),
        output_dir=str(OUTPUT_DIR),
        results_dir=str(RESULTS_DIR),
        logs_dir=str(LOGS_DIR),
    )
