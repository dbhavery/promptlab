# PromptLab

CLI tool for testing LLM prompts across multiple providers simultaneously, catching regressions before they reach production.

## Why I Built This

LLM prompts are code, but nobody tests them like code. A prompt that works on Qwen can fail on Claude. A model update can silently break outputs you depend on. I needed a way to define assertions against prompt outputs and run them in CI, the same way I run unit tests against functions.

## What It Does

- **Test prompts against 3 providers in parallel** (Ollama, Claude, Gemini) -- async calls run simultaneously, 3x faster than sequential
- **5 assertion types** -- `contains`, `not_contains`, `regex`, `max_tokens`, `min_tokens` with case-insensitive options
- **YAML test definitions** -- non-developers can write prompt tests without touching Python
- **CI-friendly exit codes** -- exit 0 on pass, exit 1 on fail, exit 2 on config error; drop into any GitHub Actions workflow
- **Rich terminal output** -- color-coded pass/fail with per-model timing breakdowns

## Key Technical Decisions

- **Click CLI over argparse** -- subcommands, auto-generated help, composable option decorators. Argparse would require manual wiring for the `run` subcommand and model override flags.
- **Async provider calls** -- `asyncio` for parallel model invocation. Testing the same prompt against 3 models takes wall-clock time of the slowest model, not the sum of all three.
- **YAML configs over Python test files** -- prompt tests are data, not logic. YAML is version-controllable, diffable, and writable by anyone who can edit a config file.
- **Optional dependency extras** -- `pip install promptlab` works without API keys; `promptlab[claude]` and `promptlab[gemini]` pull in provider SDKs only when needed.

## Quick Start

```bash
pip install promptlab            # Core + Ollama
pip install promptlab[all]       # All providers

# Write a test
cat > test_greeting.yaml << 'EOF'
name: greeting-quality
model: ollama/qwen3:8b
prompt: |
  You are a helpful assistant. Greet the user warmly.
tests:
  - input: "My name is Don"
    assertions:
      - type: contains
        value: "Don"
      - type: max_tokens
        value: 100
EOF

# Run it
promptlab run test_greeting.yaml

# Multi-model comparison
promptlab run tests/ -m ollama/qwen3:8b -m claude/claude-sonnet-4-6 -m gemini/gemini-2.5-flash
```

## Lessons Learned

**Model response variance is higher than expected.** The same prompt sent to the same model twice can produce different assertion results. Deterministic assertions like `contains` work reliably, but any assertion that depends on output structure (token count, formatting) needs either low temperature or retry logic with statistical pass thresholds. I added retry support after discovering that a 90% pass rate over 3 runs is more meaningful than a single binary result.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

MIT License. See [LICENSE](LICENSE).
