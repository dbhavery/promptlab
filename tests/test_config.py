"""Tests for promptlab.config — YAML parsing and validation."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from promptlab.config import (
    AssertionSpec,
    PromptTest,
    TestCase,
    discover_test_files,
    load_all,
    load_prompt_test,
)


@pytest.fixture()
def valid_yaml(tmp_path: Path) -> Path:
    """Create a valid prompt test YAML file."""
    content = textwrap.dedent("""\
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
    """)
    p = tmp_path / "test_greeting.yaml"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def minimal_yaml(tmp_path: Path) -> Path:
    """Create a minimal valid YAML with one test."""
    content = textwrap.dedent("""\
        name: minimal
        model: ollama/llama3
        prompt: Say hi.
        tests:
          - input: "Hi"
            assertions:
              - type: contains
                value: "hi"
                case_insensitive: true
    """)
    p = tmp_path / "test_minimal.yaml"
    p.write_text(content, encoding="utf-8")
    return p


class TestLoadPromptTest:
    """Tests for load_prompt_test()."""

    def test_load_valid(self, valid_yaml: Path) -> None:
        result = load_prompt_test(valid_yaml)
        assert isinstance(result, PromptTest)
        assert result.name == "greeting-quality"
        assert result.model == "ollama/qwen3:8b"
        assert "helpful assistant" in result.prompt
        assert len(result.tests) == 2

    def test_test_case_structure(self, valid_yaml: Path) -> None:
        result = load_prompt_test(valid_yaml)
        tc0 = result.tests[0]
        assert isinstance(tc0, TestCase)
        assert tc0.input == "Hello"
        assert len(tc0.assertions) == 2
        assert tc0.assertions[0].type == "contains"
        assert tc0.assertions[0].value == "hello"
        assert tc0.assertions[0].case_insensitive is True

    def test_assertion_types_parsed(self, valid_yaml: Path) -> None:
        result = load_prompt_test(valid_yaml)
        types = [a.type for tc in result.tests for a in tc.assertions]
        assert "contains" in types
        assert "max_tokens" in types
        assert "not_contains" in types

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_prompt_test(tmp_path / "nonexistent.yaml")

    def test_missing_name(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("model: x\nprompt: x\ntests:\n  - input: hi\n    assertions:\n      - type: contains\n        value: hi\n")
        with pytest.raises(ValueError, match="name"):
            load_prompt_test(p)

    def test_missing_tests(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("name: x\nmodel: x\nprompt: x\n")
        with pytest.raises(ValueError, match="tests"):
            load_prompt_test(p)

    def test_empty_tests_list(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.yaml"
        p.write_text("name: x\nmodel: x\nprompt: x\ntests: []\n")
        with pytest.raises(ValueError, match="non-empty"):
            load_prompt_test(p)

    def test_invalid_assertion_type(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            name: x
            model: x
            prompt: x
            tests:
              - input: hi
                assertions:
                  - type: unknown_type
                    value: something
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(ValueError, match="Unknown assertion type"):
            load_prompt_test(p)

    def test_assertion_missing_value(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            name: x
            model: x
            prompt: x
            tests:
              - input: hi
                assertions:
                  - type: contains
        """)
        p = tmp_path / "bad.yaml"
        p.write_text(content)
        with pytest.raises(ValueError, match="value"):
            load_prompt_test(p)

    def test_source_file_recorded(self, valid_yaml: Path) -> None:
        result = load_prompt_test(valid_yaml)
        assert result.source_file == str(valid_yaml)


class TestDiscoverTestFiles:
    """Tests for discover_test_files()."""

    def test_single_file(self, valid_yaml: Path) -> None:
        files = discover_test_files(valid_yaml)
        assert files == [valid_yaml]

    def test_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.yaml").write_text("name: a\nmodel: x\nprompt: x\ntests:\n  - input: x\n    assertions:\n      - type: contains\n        value: x\n")
        (tmp_path / "b.yml").write_text("name: b\nmodel: x\nprompt: x\ntests:\n  - input: x\n    assertions:\n      - type: contains\n        value: x\n")
        (tmp_path / "c.txt").write_text("not a yaml")
        files = discover_test_files(tmp_path)
        assert len(files) == 2
        names = {f.name for f in files}
        assert "a.yaml" in names
        assert "b.yml" in names

    def test_nonexistent_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            discover_test_files(tmp_path / "nope")


class TestLoadAll:
    """Tests for load_all()."""

    def test_load_all_from_directory(self, valid_yaml: Path) -> None:
        results = load_all(valid_yaml.parent)
        assert len(results) == 1
        assert results[0].name == "greeting-quality"

    def test_load_all_single_file(self, valid_yaml: Path) -> None:
        results = load_all(valid_yaml)
        assert len(results) == 1
