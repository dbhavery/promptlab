"""YAML prompt test file parsing and dataclass definitions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AssertionSpec:
    """Specification for a single assertion on a model response."""

    type: str
    value: Any = None
    case_insensitive: bool = False

    def __post_init__(self) -> None:
        valid_types = {
            "contains",
            "not_contains",
            "regex",
            "max_tokens",
            "min_tokens",
        }
        if self.type not in valid_types:
            raise ValueError(
                f"Unknown assertion type '{self.type}'. "
                f"Valid types: {', '.join(sorted(valid_types))}"
            )
        if self.value is None:
            raise ValueError(
                f"Assertion type '{self.type}' requires a 'value' field."
            )
        if self.type in ("max_tokens", "min_tokens"):
            if not isinstance(self.value, int) or self.value < 0:
                raise ValueError(
                    f"Assertion type '{self.type}' requires a non-negative integer value, "
                    f"got {self.value!r}."
                )
        if self.type == "regex":
            try:
                re.compile(str(self.value))
            except re.error as exc:
                raise ValueError(
                    f"Invalid regex pattern '{self.value}': {exc}"
                ) from exc


@dataclass
class TestCase:
    """A single test case: an input string and its assertions."""

    input: str
    assertions: list[AssertionSpec] = field(default_factory=list)


@dataclass
class PromptTest:
    """A complete prompt test definition loaded from a YAML file."""

    name: str
    model: str
    prompt: str
    tests: list[TestCase] = field(default_factory=list)
    source_file: str = ""


def _parse_assertion(raw: dict[str, Any]) -> AssertionSpec:
    """Parse a raw assertion dictionary into an AssertionSpec."""
    if not isinstance(raw, dict):
        raise ValueError(f"Assertion must be a dict, got {type(raw).__name__}.")
    if "type" not in raw:
        raise ValueError("Assertion is missing required field 'type'.")
    if "value" not in raw:
        raise ValueError(
            f"Assertion type '{raw['type']}' is missing required field 'value'."
        )
    return AssertionSpec(
        type=raw["type"],
        value=raw["value"],
        case_insensitive=raw.get("case_insensitive", False),
    )


def _parse_test_case(raw: dict[str, Any]) -> TestCase:
    """Parse a raw test case dictionary into a TestCase."""
    if not isinstance(raw, dict):
        raise ValueError(f"Test case must be a dict, got {type(raw).__name__}.")
    if "input" not in raw:
        raise ValueError("Test case is missing required field 'input'.")
    assertions = [
        _parse_assertion(a) for a in raw.get("assertions", [])
    ]
    return TestCase(input=raw["input"], assertions=assertions)


def load_prompt_test(path: Path) -> PromptTest:
    """Load a single YAML prompt test file and return a PromptTest.

    Args:
        path: Path to the YAML file.

    Returns:
        A fully parsed PromptTest dataclass.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the YAML is malformed or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt test file not found: {path}")

    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict):
        raise ValueError(f"Expected a YAML mapping at top level in {path}, got {type(raw).__name__}.")

    for required in ("name", "model", "prompt", "tests"):
        if required not in raw:
            raise ValueError(f"Missing required field '{required}' in {path}.")

    if not isinstance(raw["tests"], list) or len(raw["tests"]) == 0:
        raise ValueError(f"'tests' must be a non-empty list in {path}.")

    test_cases = [_parse_test_case(tc) for tc in raw["tests"]]

    return PromptTest(
        name=raw["name"],
        model=raw["model"],
        prompt=raw["prompt"],
        tests=test_cases,
        source_file=str(path),
    )


def discover_test_files(path: Path) -> list[Path]:
    """Discover YAML test files from a path.

    If *path* is a file, returns it in a list.
    If *path* is a directory, recursively finds all ``*.yaml`` and ``*.yml`` files.

    Args:
        path: File or directory path.

    Returns:
        Sorted list of discovered YAML file paths.

    Raises:
        FileNotFoundError: If the path does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if path.is_file():
        return [path]

    files = sorted(
        p for p in path.rglob("*")
        if p.suffix in (".yaml", ".yml") and p.is_file()
    )
    return files


def load_all(path: Path) -> list[PromptTest]:
    """Discover and load all prompt test files from a path.

    Args:
        path: File or directory path.

    Returns:
        List of parsed PromptTest objects.
    """
    files = discover_test_files(path)
    return [load_prompt_test(f) for f in files]
