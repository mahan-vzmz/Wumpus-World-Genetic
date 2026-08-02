from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

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


def _get_cli_cmd() -> list[str]:
    # Use python -m to avoid issues if wumpus-world is not in PATH
    try:
        subprocess.run([wumpus_world_cmd, "--help"], capture_output=True, check=True)
        return [wumpus_world_cmd]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [sys.executable, "-m", "wumpus_world"]


def test_cli_runs_outside_repository(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        _get_cli_cmd()
        + [
            "--agent",
            "astar",
            "--map",
            str(project_root / "maps" / "sample_astar_pit.txt"),
            "--quiet",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_missing_weights_returns_nonzero(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        _get_cli_cmd()
        + [
            "--agent",
            "genetic",
            "--map",
            str(project_root / "maps" / "sample_01.txt"),
            "--weights",
            str(tmp_path / "missing.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
