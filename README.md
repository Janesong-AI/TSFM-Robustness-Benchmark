# TSFM Robustness Benchmark

[English](./README.md) | [中文](./README.zh-CN.md)

The TSFM Robustness Benchmark is a systematic testing tool designed to evaluate the engineering robustness of Time Series Foundation Models (TSFMs) in edge cases (e.g., frequency mismatch, data contamination, covariate interference). This release includes a systematic evaluation of TimechoAI as the first targeted model. More models will be integrated in subsequent iterations.

## 1. Core Architecture - Layered Architecture
- This project is developed with **Python 3.12+** and relies on `pytest`, `timecho-ai`, and `pandas` as core dependencies.
- The system adopts a clear layered architecture to ensure the decoupling of business logic, foundational utilities, and test execution.

## 2. Directory & File Structure

The project follows a standard layered architecture:

- `config/`: Global configuration management module
  - `constants.py`: Global constants definition.
  - `settings.py`: Global environment variables (e.g., `TIMECHO_API_KEY`).
- `core/`: Business Core Layer (Encapsulates logic and state)
  - `results.py`: Test result manager (batch buffering/persistence).
  - `resume.py`: Strategy controller (rate-limiting/checkpoint resume).
  - `timecho.py`: API interaction wrapper.
- `features/`: Business feature implementation layer, contains specific business scenario logic
- `utils/`: Utility Layer (Stateless pure functions)
  - `concurrent.py`: Concurrency control and process coordination module.
  - `client.py`: Low-level Client Connection.
  - `data_sanitizer.py`: Data Sanitization & Type Safety Utils.
  - `files.py`: File Operation Utils.
  - `log/`: Logging Management Module (Encapsulates core logging logic, formatters, and context handlers).
  - `metrics.py`: Evaluation Metrics Calculator.
  - `runner.py`: Test execution core primitives (AST static discovery + single-case execution + in-memory result tracking).
- `README.md`: Project documentation, providing an overview, usage instructions, and notes.
- `run.py`: **Unified project entry point**, responsible for bootstrapping `sys.path` and launching specific test scripts by module name or file path.

## 3. Testing Workflow

1. **Configuration Initialization**: Read environment variables from `config/settings.py`.
2. **Model Initialization**: Initialize the TimechoAI model using the provided API key.
3. **Test Execution**: Execute specific testing workflows based on command-line arguments.
4. **Result Output**: Output test results to the console or specified files.

## 4. Setup & Installation

### 4.1 Create Virtual Environment

```bash
python -m venv .venv
```

### 4.2 Activate Virtual Environment

Choose the corresponding command based on your operating system:

**macOS / Linux:**
```bash
source .venv/bin/activate
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

>  **Windows PowerShell users**: If you see an error about script execution being disabled, open PowerShell as Administrator and run:  
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 4.3 Quit Virtual Environment

**Deactivate the virtual environment (universal)** :
```bash
  deactivate
```

### 4.4 Install Dependencies

After activating the virtual environment, execute the following command to install the core dependencies:

```bash
python -m pip install timecho-ai pandas pytest pytest-xdist portalocker
```

> ** Platform Note:** 
> If you are running the code on Windows, it is recommended to install `portalocker` with the Windows extension to ensure proper cross-process file locking:
> ```bash
> python -m pip install "portalocker[win32]"
> ```

## 5. Quick Start

Launch tests via the unified project entry point `run.py`:

```bash
# Run tests by module name
python run.py <module_name>

# Or run tests by file path
python run.py <path/to/test_file.py>
```

## 6. Testing Objectives
- Edge case exploration: Systematically verify the engineering robustness of the model against boundary conditions such as complex queries, replica inconsistencies, and out-of-order time-series writes.  
- Defensive architecture verification: Apply strict engineering standards to test the model's degradation behavior and recovery capabilities under non-ideal inputs.

## 7. Scope of Testing Disclaimer
The test results of this framework are limited by the specific model version, data preprocessing strategy, and runtime environment. This tool aims to provide an objective reference perspective for the engineering defensive architecture design of time-series models, rather than an absolute assertion of the final performance of any commercial product.

