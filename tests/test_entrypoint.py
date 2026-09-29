"""Guards that the CLI entry point actually imports and runs.

Every command routes through ``cli.main()``, so a missing runtime dependency or an
import error there breaks the whole tool on a fresh install while every unit test
still passes. Running the entry point in a subprocess is the only thing that
catches it — this is the regression guard for #8, where ``import click`` failed
because ``click`` was used but never declared.
"""

import subprocess
import sys

from flipperkit import __version__


def test_module_entry_point_runs():
    result = subprocess.run(
        [sys.executable, "-m", "flipperkit", "version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert __version__ in result.stdout


def test_help_entry_point_runs():
    result = subprocess.run(
        [sys.executable, "-m", "flipperkit", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
