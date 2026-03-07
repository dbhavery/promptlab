"""Tests for promptlab.report — terminal report formatting."""

from __future__ import annotations

from promptlab.assertions import AssertionResult
from promptlab.report import (
    _plain_summary,
    format_result_line,
    format_summary,
    render_report_string,
)
from promptlab.runner import TestCaseResult, TestSuiteResult


def _make_result(
    passed: bool = True,
    error: str | None = None,
    name: str = "test-name",
    user_input: str = "Hello",
    model: str = "ollama/test",
) -> TestCaseResult:
    """Helper to create a TestCaseResult for report tests."""
    assertion_results = []
    if error is None:
        assertion_results.append(
            AssertionResult(
                passed=passed,
                message="contains 'Hello'" if passed else "does not contain 'Hello'",
                assertion_type="contains",
            )
        )
    return TestCaseResult(
        test_name=name,
        input=user_input,
        model=model,
        response="Hello, world!" if passed else "Goodbye!",
        latency_ms=42.0,
        assertion_results=assertion_results,
        error=error,
    )


class TestFormatResultLine:
    """Tests for format_result_line()."""

    def test_passing_line(self) -> None:
        result = _make_result(passed=True)
        line = format_result_line(result)
        plain = line.plain
        assert "[PASS]" in plain
        assert "test-name" in plain

    def test_failing_line(self) -> None:
        result = _make_result(passed=False)
        line = format_result_line(result)
        plain = line.plain
        assert "[FAIL]" in plain

    def test_error_line(self) -> None:
        result = _make_result(error="Connection refused")
        line = format_result_line(result)
        plain = line.plain
        assert "[ERR]" in plain


class TestFormatSummary:
    """Tests for format_summary()."""

    def test_all_passed(self) -> None:
        suite = TestSuiteResult(results=[_make_result(passed=True)])
        text = format_summary(suite)
        assert "1 passed" in text.plain

    def test_mixed(self) -> None:
        suite = TestSuiteResult(results=[
            _make_result(passed=True),
            _make_result(passed=False),
            _make_result(error="boom"),
        ])
        text = format_summary(suite)
        plain = text.plain
        assert "1 passed" in plain
        assert "1 failed" in plain
        assert "1 error" in plain


class TestPlainSummary:
    """Tests for the _plain_summary helper."""

    def test_only_passed(self) -> None:
        suite = TestSuiteResult(results=[_make_result(passed=True)] * 3)
        assert _plain_summary(suite) == "3 passed"

    def test_only_failed(self) -> None:
        suite = TestSuiteResult(results=[_make_result(passed=False)] * 2)
        assert _plain_summary(suite) == "2 failed"

    def test_only_errors(self) -> None:
        suite = TestSuiteResult(results=[_make_result(error="e")] * 1)
        assert _plain_summary(suite) == "1 error(s)"


class TestRenderReportString:
    """Tests for render_report_string()."""

    def test_report_contains_summary(self) -> None:
        suite = TestSuiteResult(results=[
            _make_result(passed=True),
            _make_result(passed=False),
        ])
        output = render_report_string(suite)
        assert "Summary:" in output
        assert "1 passed" in output
        assert "1 failed" in output

    def test_verbose_shows_response(self) -> None:
        suite = TestSuiteResult(results=[_make_result(passed=True)])
        output = render_report_string(suite, verbose=True)
        assert "42ms" in output
        assert "Hello, world!" in output

    def test_error_shows_error_message(self) -> None:
        suite = TestSuiteResult(results=[_make_result(error="Connection refused")])
        output = render_report_string(suite)
        assert "Connection refused" in output
