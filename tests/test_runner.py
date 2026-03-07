"""Tests for promptlab.runner — test execution with mocked model adapters."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from promptlab.config import AssertionSpec, PromptTest, TestCase
from promptlab.models import ModelAdapter, ModelResponse
from promptlab.runner import (
    TestCaseResult,
    TestSuiteResult,
    run_prompt_test,
    run_suite,
    run_test_case,
)


class FakeAdapter(ModelAdapter):
    """A fake model adapter that returns a predetermined response."""

    def __init__(self, text: str = "Hello, Don!", error: str | None = None) -> None:
        self._text = text
        self._error = error

    async def generate(self, prompt: str, user_input: str) -> ModelResponse:
        return ModelResponse(
            text=self._text,
            model="fake/test-model",
            latency_ms=42.0,
            error=self._error,
        )


def _make_prompt_test(
    assertions: list[AssertionSpec] | None = None,
    user_input: str = "Hello",
) -> PromptTest:
    """Helper to create a PromptTest with one test case."""
    if assertions is None:
        assertions = [AssertionSpec(type="contains", value="Hello")]
    return PromptTest(
        name="test-greeting",
        model="fake/test-model",
        prompt="Greet the user.",
        tests=[TestCase(input=user_input, assertions=assertions)],
    )


class TestRunTestCase:
    """Tests for run_test_case()."""

    def test_passing_case(self) -> None:
        adapter = FakeAdapter(text="Hello, Don!")
        pt = _make_prompt_test(
            assertions=[AssertionSpec(type="contains", value="Hello")]
        )
        result = asyncio.run(run_test_case(adapter, pt, pt.tests[0]))
        assert isinstance(result, TestCaseResult)
        assert result.passed is True
        assert result.error is None
        assert result.response == "Hello, Don!"

    def test_failing_case(self) -> None:
        adapter = FakeAdapter(text="Goodbye!")
        pt = _make_prompt_test(
            assertions=[AssertionSpec(type="contains", value="Hello")]
        )
        result = asyncio.run(run_test_case(adapter, pt, pt.tests[0]))
        assert result.passed is False
        assert result.assertion_results[0].passed is False

    def test_error_case(self) -> None:
        adapter = FakeAdapter(text="", error="Connection refused")
        pt = _make_prompt_test()
        result = asyncio.run(run_test_case(adapter, pt, pt.tests[0]))
        assert result.passed is False
        assert result.error == "Connection refused"
        assert len(result.assertion_results) == 0

    def test_multiple_assertions(self) -> None:
        adapter = FakeAdapter(text="Hello, Don! Welcome back.")
        pt = _make_prompt_test(
            assertions=[
                AssertionSpec(type="contains", value="Hello"),
                AssertionSpec(type="contains", value="Don"),
                AssertionSpec(type="not_contains", value="error"),
                AssertionSpec(type="max_tokens", value=50),
            ]
        )
        result = asyncio.run(run_test_case(adapter, pt, pt.tests[0]))
        assert result.passed is True
        assert len(result.assertion_results) == 4
        assert all(ar.passed for ar in result.assertion_results)


class TestTestSuiteResult:
    """Tests for TestSuiteResult aggregation."""

    def test_empty_suite(self) -> None:
        suite = TestSuiteResult()
        assert suite.total == 0
        assert suite.passed == 0
        assert suite.failed == 0
        assert suite.errors == 0
        assert suite.all_passed is True

    def test_mixed_results(self) -> None:
        suite = TestSuiteResult(results=[
            TestCaseResult(
                test_name="a", input="x", model="m", response="ok",
                latency_ms=10, assertion_results=[],
            ),
            TestCaseResult(
                test_name="b", input="y", model="m", response="bad",
                latency_ms=10,
                assertion_results=[
                    # Simulate a failed assertion
                    __import__("promptlab.assertions", fromlist=["AssertionResult"]).AssertionResult(
                        passed=False, message="nope", assertion_type="contains"
                    ),
                ],
            ),
            TestCaseResult(
                test_name="c", input="z", model="m", response="",
                latency_ms=10, error="timeout",
            ),
        ])
        assert suite.total == 3
        assert suite.passed == 1
        assert suite.failed == 1
        assert suite.errors == 1
        assert suite.all_passed is False


class TestRunSuite:
    """Tests for run_suite() with model override mocking."""

    def test_run_suite_single_test(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Run a suite with one prompt test, mocking create_adapter."""
        fake = FakeAdapter(text="Hello there!")
        monkeypatch.setattr(
            "promptlab.runner.create_adapter", lambda model_str: fake
        )

        pt = _make_prompt_test(
            assertions=[AssertionSpec(type="contains", value="Hello")]
        )
        suite = asyncio.run(run_suite([pt]))
        assert suite.total == 1
        assert suite.passed == 1
        assert suite.all_passed is True

    def test_run_suite_model_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Run suite with model overrides, each override produces a result."""
        call_log: list[str] = []

        def fake_create(model_str: str) -> FakeAdapter:
            call_log.append(model_str)
            return FakeAdapter(text="Hi!")

        monkeypatch.setattr("promptlab.runner.create_adapter", fake_create)

        pt = _make_prompt_test(
            assertions=[AssertionSpec(type="contains", value="Hi", case_insensitive=True)]
        )
        suite = asyncio.run(
            run_suite([pt], model_overrides=["ollama/a", "ollama/b"])
        )
        assert suite.total == 2
        assert suite.passed == 2
        assert "ollama/a" in call_log
        assert "ollama/b" in call_log
