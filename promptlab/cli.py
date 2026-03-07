"""Click CLI entry point for promptlab."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from promptlab import __version__
from promptlab.config import load_all
from promptlab.report import print_report
from promptlab.runner import run_suite_sync


@click.group()
@click.version_option(version=__version__, prog_name="promptlab")
def main() -> None:
    """promptlab -- Prompt testing framework for LLMs.

    Define prompt tests as YAML, run them against multiple models,
    check assertions, and track regressions in CI.
    """


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--models",
    "-m",
    multiple=True,
    help=(
        "Override model(s) to test against. Can be specified multiple times. "
        "Format: provider/model-name (e.g. ollama/qwen3:8b)."
    ),
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show model responses and detailed assertion results.",
)
def run(path: str, models: tuple[str, ...], verbose: bool) -> None:
    """Run prompt tests from a YAML file or directory.

    PATH can be a single YAML file or a directory containing YAML files.

    Examples:

        promptlab run tests/prompts/

        promptlab run test_greeting.yaml --verbose

        promptlab run tests/ -m ollama/qwen3:8b -m claude/claude-sonnet-4-6
    """
    resolved = Path(path).resolve()
    click.echo(f"Loading tests from: {resolved}")

    try:
        prompt_tests = load_all(resolved)
    except (FileNotFoundError, ValueError) as exc:
        click.echo(f"Error loading tests: {exc}", err=True)
        sys.exit(2)

    if not prompt_tests:
        click.echo("No test files found.", err=True)
        sys.exit(2)

    click.echo(
        f"Found {len(prompt_tests)} test file(s) with "
        f"{sum(len(pt.tests) for pt in prompt_tests)} test case(s)."
    )

    model_overrides = list(models) if models else None
    if model_overrides:
        click.echo(f"Model override(s): {', '.join(model_overrides)}")

    suite_result = run_suite_sync(prompt_tests, model_overrides=model_overrides)
    print_report(suite_result, verbose=verbose)

    if suite_result.all_passed:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
