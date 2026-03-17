"""Tests for `atk version` and `atk version completion` commands."""

import pytest

from atk_cli.main import app


def test_version_display(runner):
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "atk-cli" in result.output


def test_completion_bash(runner):
    result = runner.invoke(app, ["version", "completion", "bash"])
    assert result.exit_code == 0
    assert "_ATK_COMPLETE=bash_source" in result.output


def test_completion_zsh(runner):
    result = runner.invoke(app, ["version", "completion", "zsh"])
    assert result.exit_code == 0
    assert "_ATK_COMPLETE=zsh_source" in result.output


def test_completion_fish(runner):
    result = runner.invoke(app, ["version", "completion", "fish"])
    assert result.exit_code == 0
    assert "_ATK_COMPLETE=fish_source" in result.output


def test_completion_unsupported(runner):
    result = runner.invoke(app, ["version", "completion", "powershell"])
    assert result.exit_code == 1
    assert "Unsupported shell" in result.output
