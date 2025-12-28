"""Tests covering CLI entry point behaviors."""
import argparse

import pytest

import main


def _validation_result(valid: bool):
    return {"valid": valid, "issues": [], "details": {"google": [], "ollama": []}}


def test_check_flag_valid_configuration(monkeypatch):
    monkeypatch.setattr(main, "validate_config", lambda: _validation_result(True))
    args = argparse.Namespace(check=True, query=[])

    with pytest.raises(SystemExit) as excinfo:
        main._run_with_args(args)

    assert excinfo.value.code == 0


def test_check_flag_invalid_configuration(monkeypatch):
    monkeypatch.setattr(main, "validate_config", lambda: _validation_result(False))
    args = argparse.Namespace(check=True, query=[])

    with pytest.raises(SystemExit) as excinfo:
        main._run_with_args(args)

    assert excinfo.value.code == 1


def test_argument_parser_setup(monkeypatch):
    recorded = []

    class FakeParser:
        def __init__(self, *args, **kwargs):
            pass

        def add_argument(self, *args, **kwargs):
            recorded.append(args)

        def parse_args(self):
            return argparse.Namespace(check=False, query=["ai"])

    monkeypatch.setattr(main.argparse, "ArgumentParser", FakeParser)
    monkeypatch.setattr(main, "_run_with_args", lambda args: None)

    main.main()

    assert any("-c" in args or "--check" in args for args in recorded)
    assert any("query" in args for args in recorded)
