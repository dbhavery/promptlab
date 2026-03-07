"""Test runner that executes prompt tests against models and collects results."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from promptlab.assertions import AssertionResult, evaluate_assertion
from promptlab.config import PromptTest, TestCase
from promptlab.models import ModelAdapter, ModelResponse, create_adapter


@dataclass
class TestCaseResult:
    """Result of running a single test case."""

    test_name: str
    input: str
    model: str
    response: str
    latency_ms: float
    assertion_results: list[AssertionResult] = field(default_factory=list)
    error: str | None = None

    @property
    def passed(self) -> bool:
        """True if all assertions passed and there was no error."""
        if self.error:
            return False
        return all(ar.passed for ar in self.assertion_results)


@dataclass
class TestSuiteResult:
    """Aggregated results from running all prompt tests."""

    results: list[TestCaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of test cases."""
        return len(self.results)

    @property
    def passed(self) -> int:
        """Number of passing test cases."""
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        """Number of failing test cases (assertions failed, no error)."""
        return sum(
            1 for r in self.results
            if not r.passed and r.error is None
        )

    @property
    def errors(self) -> int:
        """Number of test cases that encountered errors."""
        return sum(1 for r in self.results if r.error is not None)

    @property
    def all_passed(self) -> bool:
        """True if every test case passed."""
        return all(r.passed for r in self.results)


async def run_test_case(
    adapter: ModelAdapter,
    prompt_test: PromptTest,
    test_case: TestCase,
) -> TestCaseResult:
    """Run a single test case against a model.

    Args:
        adapter: The model adapter to use.
        prompt_test: The parent prompt test (for name and prompt).
        test_case: The specific test case to run.

    Returns:
        A TestCaseResult with assertion evaluations.
    """
    response: ModelResponse = await adapter.generate(
        prompt=prompt_test.prompt,
        user_input=test_case.input,
    )

    if response.error:
        return TestCaseResult(
            test_name=prompt_test.name,
            input=test_case.input,
            model=response.model,
            response="",
            latency_ms=response.latency_ms,
            error=response.error,
        )

    assertion_results = [
        evaluate_assertion(response.text, spec)
        for spec in test_case.assertions
    ]

    return TestCaseResult(
        test_name=prompt_test.name,
        input=test_case.input,
        model=response.model,
        response=response.text,
        latency_ms=response.latency_ms,
        assertion_results=assertion_results,
    )


async def run_prompt_test(
    prompt_test: PromptTest,
    model_override: str | None = None,
) -> list[TestCaseResult]:
    """Run all test cases for a single prompt test.

    Args:
        prompt_test: The prompt test definition.
        model_override: If provided, use this model string instead of the one
            specified in the YAML file.

    Returns:
        List of TestCaseResult, one per test case.
    """
    model_string = model_override or prompt_test.model
    adapter = create_adapter(model_string)

    results = []
    for test_case in prompt_test.tests:
        result = await run_test_case(adapter, prompt_test, test_case)
        results.append(result)

    return results


async def run_suite(
    prompt_tests: list[PromptTest],
    model_overrides: list[str] | None = None,
) -> TestSuiteResult:
    """Run all prompt tests, optionally against multiple models.

    Args:
        prompt_tests: List of prompt test definitions.
        model_overrides: If provided, run every prompt test against each model
            in this list (instead of the model specified in the YAML).

    Returns:
        A TestSuiteResult aggregating all test case results.
    """
    suite = TestSuiteResult()

    for pt in prompt_tests:
        if model_overrides:
            for model in model_overrides:
                case_results = await run_prompt_test(pt, model_override=model)
                suite.results.extend(case_results)
        else:
            case_results = await run_prompt_test(pt)
            suite.results.extend(case_results)

    return suite


def run_suite_sync(
    prompt_tests: list[PromptTest],
    model_overrides: list[str] | None = None,
) -> TestSuiteResult:
    """Synchronous wrapper around run_suite.

    Args:
        prompt_tests: List of prompt test definitions.
        model_overrides: Optional list of model strings.

    Returns:
        A TestSuiteResult aggregating all test case results.
    """
    return asyncio.run(run_suite(prompt_tests, model_overrides))
