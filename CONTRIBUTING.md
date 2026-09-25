# Contributing to ALLIGENT

Thank you for your interest in contributing to **ALLIGENT — AI-Powered Industrial Investigation & Decision Support**.

As an industrial reliability and engineering intelligence platform, ALLIGENT adheres to rigorous software engineering and safety verification standards.

---

## 1. Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior through the channels detailed in [SUPPORT.md](SUPPORT.md).

---

## 2. Development Workflow

### 2.1 Branching Strategy
* `main`: Stable release branch. All code must pass unit tests, static analysis, and benchmark verification.
* `feature/<feature-name>`: Dedicated branch for new agent specialists, physics models, or UI features.
* `fix/<bug-description>`: Targeted bug fixes.

### 2.2 Local Environment Setup
```bash
# Clone the repository
git clone https://github.com/pavanmnaikcse/ALLIGENT-.git
cd ALLIGENT-

# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements.txt
pip install pytest flake8 black mypy
```

### 2.3 Running Tests & Benchmarks
Before submitting a pull request, ensure all test suites pass without regression:
```bash
# Run unit and integration tests
pytest -v tests/

# Execute the diagnostic benchmark suite
python -m backend.run_benchmark
```

---

## 3. Contribution Guidelines & Rules

1. **Safety Boundaries:**
   * Never introduce autonomous physical machine actuation. All maintenance recommendations, speed derates, and parts purchases must retain human-in-the-loop authorization gates.
2. **Deterministic Fallbacks:**
   * Any agent or feature integrating with Large Language Models must provide a calibrated deterministic fallback to ensure the system functions reliably in offline or air-gapped manufacturing environments.
3. **Secret Hygiene:**
   * Never commit API keys, tokens, or credentials. Always use `os.environ` and `.env.example`.
4. **Pydantic Validation:**
   * All API payloads and agent messages must define and validate against Pydantic v2 models.

---

## 4. Pull Request Process

1. Fork the repository and create your feature branch.
2. Ensure your code passes all linters (`flake8`, `black --check`).
3. Add automated tests in `tests/` covering new logic or bug fixes.
4. Update the relevant documentation in `docs/` if modifying schemas or algorithms.
5. Submit a pull request following the provided [Pull Request Template](.github/pull_request_template.md).
