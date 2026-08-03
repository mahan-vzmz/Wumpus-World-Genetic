from __future__ import annotations

import os
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
    try:
        subprocess.run([wumpus_world_cmd, "--help"], capture_output=True, check=True)
        return [wumpus_world_cmd]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [sys.executable, "-m", "wumpus_world"]


def _get_demo_cmd() -> list[str]:
    try:
        subprocess.run([wumpus_world_demo_cmd, "--help"], capture_output=True, check=True)
        return [wumpus_world_demo_cmd]
    except (FileNotFoundError, subprocess.CalledProcessError):
        return [sys.executable, "-m", "wumpus_world.demo"]


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


def test_default_cli_runs_outside_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        _get_cli_cmd() + ["--quiet"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_default_demo_runs_outside_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        _get_demo_cmd(),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_missing_map_returns_nonzero(tmp_path: Path) -> None:
    result = subprocess.run(
        _get_cli_cmd() + ["--map", str(tmp_path / "missing.txt"), "--quiet"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0


def test_missing_map_prints_error_to_stderr(tmp_path: Path) -> None:
    result = subprocess.run(
        _get_cli_cmd() + ["--map", str(tmp_path / "missing.txt"), "--quiet"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stderr.strip() != ""


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
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_missing_weights_prints_error_to_stderr(tmp_path: Path) -> None:
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
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stderr.strip() != ""


def test_default_genetic_agent_loads_packaged_weights(tmp_path: Path) -> None:
    result = subprocess.run(
        _get_cli_cmd() + ["--agent", "genetic", "--quiet"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"


def test_regenerate_works_without_existing_maps(tmp_path: Path) -> None:
    # Set up a fake project structure
    maps_dir = tmp_path / "maps" / "training"
    # Ensure it's empty/doesn't exist
    assert not maps_dir.exists()

    # We need to run train_genetic.py directly
    project_root = Path(__file__).resolve().parents[1]
    train_script = project_root / "train_genetic.py"

    # Copy src code so imports work?
    # No, just run with PYTHONPATH
    env = dict(os.environ)
    env["PYTHONPATH"] = str(project_root / "src")

    # Run the training script, but only for 1 generation so it's fast
    result = subprocess.run(
        [sys.executable, str(train_script), "--regenerate-training-maps", "--generations", "1", "--population", "4"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"stdout: {result.stdout}\nstderr: {result.stderr}"

    # Verify that it created maps
    generated_maps = list(maps_dir.glob("training_*.txt"))
    assert len(generated_maps) == 12


def test_maps_and_regenerate_mutually_exclusive(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    train_script = project_root / "train_genetic.py"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, str(train_script), "--regenerate-training-maps", "--maps", "custom1.txt", "custom2.txt"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "not allowed with argument" in result.stderr
