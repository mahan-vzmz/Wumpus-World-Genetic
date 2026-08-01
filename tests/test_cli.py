from __future__ import annotations

import shutil
import subprocess
import sys

wumpus_world_cmd = shutil.which("wumpus-world") or "wumpus-world"
wumpus_world_demo_cmd = shutil.which("wumpus-world-demo") or "wumpus-world-demo"


def test_cli_help() -> None:
    try:
        result = subprocess.run(
            [wumpus_world_cmd, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = subprocess.run(
            [sys.executable, "-m", "wumpus_world.cli", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0
    assert "--agent" in result.stdout


def test_demo_help() -> None:
    try:
        result = subprocess.run(
            [wumpus_world_demo_cmd, "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        result = subprocess.run(
            [sys.executable, "-m", "wumpus_world.demo", "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
    assert result.returncode == 0


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "wumpus_world", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
