from __future__ import annotations
from pathlib import Path
import pytest
from map_parser import load_map


def write_map(tmp_path: Path, rows: list[str], config: list[str]) -> Path:
    path = tmp_path / "map.txt"
    path.write_text("\n".join(rows + config) + "\n", encoding="utf-8")
    return path


def valid_rows() -> list[str]:
    rows = ["********" for _ in range(8)]
    rows[3] = "***G****"
    return rows


def test_parser_rejects_extra_lines(tmp_path: Path) -> None:
    path = write_map(tmp_path, valid_rows(), ["120", "50", "10", "8 8", "extra"])
    with pytest.raises(ValueError, match="exactly"):
        load_map(path)


def test_parser_rejects_invalid_symbol(tmp_path: Path) -> None:
    rows = valid_rows()
    rows[1] = "***X****"
    path = write_map(tmp_path, rows, ["120", "50", "10", "8 8"])
    with pytest.raises(ValueError, match="Invalid map symbols"):
        load_map(path)


def test_parser_rejects_unsafe_exit(tmp_path: Path) -> None:
    rows = valid_rows()
    rows[7] = "*******P"
    path = write_map(tmp_path, rows, ["120", "50", "10", "8 8"])
    with pytest.raises(ValueError, match="Exit cell must be empty"):
        load_map(path)


def test_parser_rejects_missing_gold(tmp_path: Path) -> None:
    rows = ["********" for _ in range(8)]
    path = write_map(tmp_path, rows, ["120", "50", "10", "8 8"])
    with pytest.raises(ValueError, match="at least one gold"):
        load_map(path)


def test_parser_accepts_key_value_configuration(tmp_path: Path) -> None:
    path = write_map(
        tmp_path,
        valid_rows(),
        ["health=120", "gold=50", "pit=10", "exit=8,8"],
    )
    config = load_map(path)
    assert config.initial_health == 120
    assert config.exit_position == (7, 7)
