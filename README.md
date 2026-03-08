# promptlab
[![CI](https://github.com/dbhavery/promptlab/actions/workflows/ci.yml/badge.svg)](https://github.com/dbhavery/promptlab/actions/workflows/ci.yml)

**Prompt testing framework -- pytest for LLM prompts.**

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![PyPI](https://img.shields.io/badge/pypi-v0.1.0-orange)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Define prompt tests as YAML. Run them against Ollama, Claude, or Gemini. Assert on the output. Track regressions in CI.

---

## Quick Start

**1. Install**

```bash
pip install promptlab
```

With optional model support:

```bash
pip install promptlab[claude]   # Anthropic Claude
pip install promptlab[gemini]   # Google Gemini
pip install promptlab[all]      # Everything
```

**2. Write a test file** (`test_greeting.yaml`)

```yaml
name: greeting-quality
model: ollama/qwen3:8b
prompt: |
  You are a helpful assistant. Greet the user warmly.
tests:
  - input: "Hello"
    assertions:
      - type: contains
        value: "hello"
        case_insensitive: true
      - type: max_tokens
        value: 100
  - input: "My name is Don"
    assertions:
      - type: contains
        value: "Don"
      - type: not_contains
        value: "I don't know"
```

**3. Run it**

```bash
promptlab run test_greeting.yaml
```

Output:

```
Loading tests from: /path/to/test_greeting.yaml
Found 1 test file(s) with 2 test case(s).

────────────────── promptlab results ──────────────────

[PASS] greeting-quality | input='Hello' | ollama/qwen3:8b
[PASS] greeting-quality | input='My name is Don' | ollama/qwen3:8b

───────────────────────────────────────────────────────
Summary: 2 passed
```

---

## YAML Test Format

Each YAML file defines one prompt test suite:

```yaml
name: <test-suite-name>        # Required. Identifier for this test group.
model: <provider>/<model-id>   # Required. Default model to test against.
prompt: |                      # Required. The system prompt / instruction.
  Your prompt here.
tests:                         # Required. List of test cases.
  - input: "User message"     # Required. The user input to send.
    assertions:                # Required. List of assertions on the response.
      - type: contains
        value: "expected text"
```

---

## Assertion Types

| Type | Description | Options |
|------|-------------|---------|
| `contains` | Response must contain the substring | `case_insensitive: true` |
| `not_contains` | Response must NOT contain the substring | `case_insensitive: true` |
| `regex` | Response must match the regex pattern | `case_insensitive: true` |
| `max_tokens` | Response word count must not exceed value | -- |
| `min_tokens` | Response word count must be at least value | -- |

---

## Supported Models

| Provider | Format | Example | Requires |
|----------|--------|---------|----------|
| Ollama | `ollama/<model>` | `ollama/qwen3:8b` | Local Ollama server |
| Claude | `claude/<model-id>` | `claude/claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| Gemini | `gemini/<model-id>` | `gemini/gemini-2.5-flash` | `GOOGLE_API_KEY` |

---

## Multi-Model Comparison

Run the same prompt tests against multiple models:

```bash
promptlab run tests/ -m ollama/qwen3:8b -m claude/claude-sonnet-4-6 -m gemini/gemini-2.5-flash
```

This runs every test case against all three models and reports results per model.

---

## CLI Reference

```
Usage: promptlab [OPTIONS] COMMAND [ARGS]...

  promptlab -- Prompt testing framework for LLMs.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  run  Run prompt tests from a YAML file or directory.
```

### `promptlab run`

```
Usage: promptlab run [OPTIONS] PATH

  Run prompt tests from a YAML file or directory.

Options:
  -m, --models TEXT  Override model(s). Can be repeated.
  -v, --verbose      Show model responses and assertion details.
  --help             Show this message and exit.
```

- **Exit code 0** if all tests pass (CI-friendly).
- **Exit code 1** if any test fails.
- **Exit code 2** if there is a configuration error.

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Prompt Tests
on: [push, pull_request]

jobs:
  prompt-tests:
    runs-on: ubuntu-latest
    services:
      ollama:
        image: ollama/ollama
        ports:
          - 11434:11434
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install promptlab
        run: pip install promptlab

      - name: Pull model
        run: docker exec $(docker ps -q) ollama pull qwen3:8b

      - name: Run prompt tests
        run: promptlab run tests/prompts/ --verbose
```

---

## Architecture

```
promptlab/
  cli.py          Click CLI entry point
  config.py       YAML parsing into dataclasses
  models.py       Async model adapters (Ollama, Claude, Gemini)
  assertions.py   Assertion checkers (contains, regex, token count)
  runner.py       Test orchestration and result aggregation
  report.py       Rich terminal output formatting
```

The flow:

1. **CLI** receives a path and options.
2. **Config** discovers YAML files and parses them into `PromptTest` dataclasses.
3. **Runner** creates model adapters and executes each test case.
4. **Assertions** evaluate each response against the defined checks.
5. **Report** formats and prints results with colored output.

---

## Development

```bash
git clone https://github.com/dbhavery/promptlab.git
cd promptlab
pip install -e ".[dev]"
pytest tests/ -v
```

---

## License

MIT -- see [LICENSE](LICENSE).
