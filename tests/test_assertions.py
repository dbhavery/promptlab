"""Tests for promptlab.assertions — all assertion types."""

from __future__ import annotations

import pytest

from promptlab.assertions import (
    AssertionResult,
    check_contains,
    check_max_tokens,
    check_min_tokens,
    check_not_contains,
    check_regex,
    evaluate_assertion,
)
from promptlab.config import AssertionSpec


class TestContainsAssertion:
    """Tests for the 'contains' assertion."""

    def test_pass_case_sensitive(self) -> None:
        spec = AssertionSpec(type="contains", value="Hello")
        result = check_contains("Hello, world!", spec)
        assert result.passed is True

    def test_fail_case_sensitive(self) -> None:
        spec = AssertionSpec(type="contains", value="hello")
        result = check_contains("Hello, world!", spec)
        assert result.passed is False

    def test_pass_case_insensitive(self) -> None:
        spec = AssertionSpec(type="contains", value="hello", case_insensitive=True)
        result = check_contains("Hello, world!", spec)
        assert result.passed is True

    def test_fail_not_present(self) -> None:
        spec = AssertionSpec(type="contains", value="xyz")
        result = check_contains("Hello, world!", spec)
        assert result.passed is False
        assert "does not contain" in result.message


class TestNotContainsAssertion:
    """Tests for the 'not_contains' assertion."""

    def test_pass_not_present(self) -> None:
        spec = AssertionSpec(type="not_contains", value="error")
        result = check_not_contains("Everything is fine.", spec)
        assert result.passed is True

    def test_fail_present(self) -> None:
        spec = AssertionSpec(type="not_contains", value="fine")
        result = check_not_contains("Everything is fine.", spec)
        assert result.passed is False
        assert "unexpectedly contains" in result.message

    def test_case_insensitive(self) -> None:
        spec = AssertionSpec(type="not_contains", value="FINE", case_insensitive=True)
        result = check_not_contains("Everything is fine.", spec)
        assert result.passed is False


class TestRegexAssertion:
    """Tests for the 'regex' assertion."""

    def test_pass_simple_pattern(self) -> None:
        spec = AssertionSpec(type="regex", value=r"\d{3}-\d{4}")
        result = check_regex("Call me at 555-1234.", spec)
        assert result.passed is True

    def test_fail_no_match(self) -> None:
        spec = AssertionSpec(type="regex", value=r"\d{3}-\d{4}")
        result = check_regex("No phone number here.", spec)
        assert result.passed is False

    def test_case_insensitive(self) -> None:
        spec = AssertionSpec(type="regex", value=r"hello", case_insensitive=True)
        result = check_regex("HELLO world", spec)
        assert result.passed is True

    def test_case_sensitive_fail(self) -> None:
        spec = AssertionSpec(type="regex", value=r"^hello")
        result = check_regex("HELLO world", spec)
        assert result.passed is False


class TestMaxTokensAssertion:
    """Tests for the 'max_tokens' assertion."""

    def test_pass_under_limit(self) -> None:
        spec = AssertionSpec(type="max_tokens", value=10)
        result = check_max_tokens("This is short.", spec)
        assert result.passed is True

    def test_fail_over_limit(self) -> None:
        spec = AssertionSpec(type="max_tokens", value=2)
        result = check_max_tokens("This sentence has more than two words.", spec)
        assert result.passed is False
        assert "exceeds" in result.message

    def test_exact_limit(self) -> None:
        spec = AssertionSpec(type="max_tokens", value=3)
        result = check_max_tokens("one two three", spec)
        assert result.passed is True


class TestMinTokensAssertion:
    """Tests for the 'min_tokens' assertion."""

    def test_pass_over_minimum(self) -> None:
        spec = AssertionSpec(type="min_tokens", value=2)
        result = check_min_tokens("This has enough words.", spec)
        assert result.passed is True

    def test_fail_under_minimum(self) -> None:
        spec = AssertionSpec(type="min_tokens", value=100)
        result = check_min_tokens("Too short.", spec)
        assert result.passed is False
        assert "below min" in result.message

    def test_exact_minimum(self) -> None:
        spec = AssertionSpec(type="min_tokens", value=3)
        result = check_min_tokens("one two three", spec)
        assert result.passed is True


class TestEvaluateAssertion:
    """Tests for the evaluate_assertion dispatcher."""

    def test_dispatch_contains(self) -> None:
        spec = AssertionSpec(type="contains", value="yes")
        result = evaluate_assertion("yes indeed", spec)
        assert result.passed is True

    def test_dispatch_not_contains(self) -> None:
        spec = AssertionSpec(type="not_contains", value="no")
        result = evaluate_assertion("yes indeed", spec)
        assert result.passed is True

    def test_dispatch_regex(self) -> None:
        spec = AssertionSpec(type="regex", value=r"\byes\b")
        result = evaluate_assertion("yes indeed", spec)
        assert result.passed is True

    def test_unknown_type_raises(self) -> None:
        spec = AssertionSpec.__new__(AssertionSpec)
        spec.type = "bogus"
        spec.value = "x"
        spec.case_insensitive = False
        with pytest.raises(ValueError, match="No checker"):
            evaluate_assertion("text", spec)
