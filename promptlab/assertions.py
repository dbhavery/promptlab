"""Assertion checkers for prompt test results."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from promptlab.config import AssertionSpec


@dataclass
class AssertionResult:
    """Result of evaluating a single assertion."""

    passed: bool
    message: str
    assertion_type: str = ""


def check_contains(response: str, spec: AssertionSpec) -> AssertionResult:
    """Check that the response contains a given substring.

    Args:
        response: The model's response text.
        spec: The assertion specification (value = expected substring).

    Returns:
        AssertionResult indicating pass or fail.
    """
    expected = str(spec.value)
    haystack = response
    needle = expected

    if spec.case_insensitive:
        haystack = haystack.lower()
        needle = needle.lower()

    if needle in haystack:
        return AssertionResult(
            passed=True,
            message=f"Response contains '{expected}'.",
            assertion_type="contains",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"Response does not contain '{expected}'.",
            assertion_type="contains",
        )


def check_not_contains(response: str, spec: AssertionSpec) -> AssertionResult:
    """Check that the response does NOT contain a given substring.

    Args:
        response: The model's response text.
        spec: The assertion specification (value = forbidden substring).

    Returns:
        AssertionResult indicating pass or fail.
    """
    forbidden = str(spec.value)
    haystack = response
    needle = forbidden

    if spec.case_insensitive:
        haystack = haystack.lower()
        needle = needle.lower()

    if needle not in haystack:
        return AssertionResult(
            passed=True,
            message=f"Response does not contain '{forbidden}'.",
            assertion_type="not_contains",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"Response unexpectedly contains '{forbidden}'.",
            assertion_type="not_contains",
        )


def check_regex(response: str, spec: AssertionSpec) -> AssertionResult:
    """Check that the response matches a regex pattern.

    Args:
        response: The model's response text.
        spec: The assertion specification (value = regex pattern string).

    Returns:
        AssertionResult indicating pass or fail.
    """
    pattern = str(spec.value)
    flags = re.IGNORECASE if spec.case_insensitive else 0

    if re.search(pattern, response, flags):
        return AssertionResult(
            passed=True,
            message=f"Response matches pattern '{pattern}'.",
            assertion_type="regex",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"Response does not match pattern '{pattern}'.",
            assertion_type="regex",
        )


def check_max_tokens(response: str, spec: AssertionSpec) -> AssertionResult:
    """Check that the response does not exceed a maximum word count.

    Uses whitespace-split word count as a proxy for token count.

    Args:
        response: The model's response text.
        spec: The assertion specification (value = max allowed words).

    Returns:
        AssertionResult indicating pass or fail.
    """
    max_count = int(spec.value)
    word_count = len(response.split())

    if word_count <= max_count:
        return AssertionResult(
            passed=True,
            message=f"Response has {word_count} words (max {max_count}).",
            assertion_type="max_tokens",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"Response has {word_count} words, exceeds max of {max_count}.",
            assertion_type="max_tokens",
        )


def check_min_tokens(response: str, spec: AssertionSpec) -> AssertionResult:
    """Check that the response meets a minimum word count.

    Uses whitespace-split word count as a proxy for token count.

    Args:
        response: The model's response text.
        spec: The assertion specification (value = min required words).

    Returns:
        AssertionResult indicating pass or fail.
    """
    min_count = int(spec.value)
    word_count = len(response.split())

    if word_count >= min_count:
        return AssertionResult(
            passed=True,
            message=f"Response has {word_count} words (min {min_count}).",
            assertion_type="min_tokens",
        )
    else:
        return AssertionResult(
            passed=False,
            message=f"Response has {word_count} words, below min of {min_count}.",
            assertion_type="min_tokens",
        )


# Registry mapping assertion type names to checker functions.
ASSERTION_CHECKERS: dict[str, Any] = {
    "contains": check_contains,
    "not_contains": check_not_contains,
    "regex": check_regex,
    "max_tokens": check_max_tokens,
    "min_tokens": check_min_tokens,
}


def evaluate_assertion(response: str, spec: AssertionSpec) -> AssertionResult:
    """Evaluate a single assertion against a model response.

    Args:
        response: The model's response text.
        spec: The assertion specification.

    Returns:
        AssertionResult indicating pass or fail.

    Raises:
        ValueError: If the assertion type is not recognized.
    """
    checker = ASSERTION_CHECKERS.get(spec.type)
    if checker is None:
        raise ValueError(f"No checker registered for assertion type '{spec.type}'.")
    return checker(response, spec)
