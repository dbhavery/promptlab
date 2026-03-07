"""Terminal report formatter with colored output."""

from __future__ import annotations

from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from promptlab.runner import TestCaseResult, TestSuiteResult

# Module-level console — force_terminal avoids Windows encoding crashes.
_console = Console(force_terminal=True)


def format_result_line(result: TestCaseResult) -> Text:
    """Format a single test case result as a Rich Text line.

    Args:
        result: The test case result.

    Returns:
        A Rich Text object with colored pass/fail indicator.
    """
    if result.error:
        icon = Text("[ERR]", style="bold yellow")
        label = Text(
            f" {result.test_name} | input={result.input!r} | {result.model}",
            style="yellow",
        )
        return icon + label
    elif result.passed:
        icon = Text("[PASS]", style="bold green")
        label = Text(
            f" {result.test_name} | input={result.input!r} | {result.model}",
            style="green",
        )
        return icon + label
    else:
        icon = Text("[FAIL]", style="bold red")
        label = Text(
            f" {result.test_name} | input={result.input!r} | {result.model}",
            style="red",
        )
        return icon + label


def format_summary(suite: TestSuiteResult) -> Text:
    """Format the summary line.

    Args:
        suite: The test suite result.

    Returns:
        A Rich Text object with the summary.
    """
    parts: list[Text] = []

    if suite.passed > 0:
        parts.append(Text(f"{suite.passed} passed", style="bold green"))
    if suite.failed > 0:
        parts.append(Text(f"{suite.failed} failed", style="bold red"))
    if suite.errors > 0:
        parts.append(Text(f"{suite.errors} error(s)", style="bold yellow"))

    summary = Text("")
    for i, part in enumerate(parts):
        if i > 0:
            summary.append(", ")
        summary.append_text(part)

    return summary


def print_report(suite: TestSuiteResult, verbose: bool = False) -> None:
    """Print the full test report to the terminal.

    Args:
        suite: The test suite result.
        verbose: If True, print model responses and assertion details.
    """
    console = _console

    console.print()
    console.rule("[bold]promptlab results[/bold]")
    console.print()

    for result in suite.results:
        line = format_result_line(result)
        console.print(line)

        if result.error:
            console.print(f"    Error: {result.error}", style="yellow")

        if verbose and not result.error:
            console.print(
                f"    Response ({result.latency_ms:.0f}ms): "
                f"{escape(_truncate(result.response, 200))}",
                style="dim",
            )

        if not result.passed or verbose:
            for ar in result.assertion_results:
                if ar.passed:
                    console.print(f"      [green]+ {ar.message}[/green]")
                else:
                    console.print(f"      [red]- {ar.message}[/red]")

    console.print()
    console.rule()
    summary = format_summary(suite)
    console.print(Text("Summary: ").append_text(summary))
    console.print()


def render_report_string(suite: TestSuiteResult, verbose: bool = False) -> str:
    """Render the test report as a plain string (for testing/capture).

    Args:
        suite: The test suite result.
        verbose: If True, include model responses and assertion details.

    Returns:
        The report as a string with ANSI codes stripped.
    """
    string_console = Console(file=None, force_terminal=False, no_color=True, width=120)
    buf: list[str] = []

    # Use string capture
    with string_console.capture() as capture:
        string_console.print()
        string_console.rule("promptlab results")
        string_console.print()

        for result in suite.results:
            line = format_result_line(result)
            string_console.print(line)

            if result.error:
                string_console.print(f"    Error: {result.error}")

            if verbose and not result.error:
                string_console.print(
                    f"    Response ({result.latency_ms:.0f}ms): "
                    f"{_truncate(result.response, 200)}"
                )

            if not result.passed or verbose:
                for ar in result.assertion_results:
                    if ar.passed:
                        string_console.print(f"      + {ar.message}")
                    else:
                        string_console.print(f"      - {ar.message}")

        string_console.print()
        string_console.rule()
        summary_text = _plain_summary(suite)
        string_console.print(f"Summary: {summary_text}")
        string_console.print()

    return capture.get()


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max_len characters, adding ellipsis if needed."""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _plain_summary(suite: TestSuiteResult) -> str:
    """Build a plain-text summary string."""
    parts: list[str] = []
    if suite.passed > 0:
        parts.append(f"{suite.passed} passed")
    if suite.failed > 0:
        parts.append(f"{suite.failed} failed")
    if suite.errors > 0:
        parts.append(f"{suite.errors} error(s)")
    return ", ".join(parts)
