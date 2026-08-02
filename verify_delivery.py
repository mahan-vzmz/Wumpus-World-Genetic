from __future__ import annotations

import csv
import json
from pathlib import Path

from wumpus_world.agents.genetic_agent import GeneticWeights
from wumpus_world.map_parser import load_map
from wumpus_world.runner import run_episode

ROOT = Path(__file__).resolve().parent


def main() -> None:
    maps = sorted((ROOT / "maps").glob("**/*.txt"))
    if not maps:
        raise SystemExit("No maps found.")
    for path in maps:
        load_map(path)

    GeneticWeights.load(ROOT / "best_weights.json")

    test_manifest = json.loads((ROOT / "maps" / "test" / "manifest.json").read_text(encoding="utf-8"))
    training_manifest = json.loads((ROOT / "maps" / "training" / "manifest.json").read_text(encoding="utf-8"))
    if len(test_manifest) != 30:
        raise SystemExit(f"Expected 30 test maps; got {len(test_manifest)}")
    if len(training_manifest) != 12:
        raise SystemExit(f"Expected 12 training maps; got {len(training_manifest)}")

    with (ROOT / "results" / "final" / "experiment_results.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 90:
        raise SystemExit(f"Expected 90 experiment rows; got {len(rows)}")
    if any(row["error"] for row in rows):
        errors = [row for row in rows if row["error"]]
        raise SystemExit(f"Experiment contains {len(errors)} error rows.")
    if any(row["termination_reason"] in {"", "None", "unknown"} for row in rows):
        raise SystemExit("Experiment contains an invalid termination reason.")

    for agent in ("astar", "rule", "genetic"):
        result = run_episode(
            str(ROOT / "maps" / "sample_01.txt"),
            agent,
            max_steps=250,
            weights_path=str(ROOT / "best_weights.json"),
            verbose=False,
        )
        if not result["success"]:
            raise SystemExit(f"Sample demo failed for {agent}: {result}")

    pdf_path = ROOT / "docs" / "final_report" / "final_report.pdf"
    required = [
        pdf_path,
        ROOT / "results" / "final" / "summary_results.csv",
        ROOT / "results" / "genetic_fitness.png",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing delivery files: {missing}")

    pdf_data = pdf_path.read_bytes()
    if not pdf_data.startswith(b"%PDF-"):
        raise SystemExit(f"Final report is not a valid PDF file (missing %PDF- header): {pdf_path}")
    if b"%%EOF" not in pdf_data[-2048:]:
        raise SystemExit(f"Final report PDF has no valid EOF marker: {pdf_path}")

    try:
        import pypdf

        reader = pypdf.PdfReader(str(pdf_path))
        if len(reader.pages) < 1:
            raise SystemExit("Final report PDF has 0 pages.")
    except ImportError:
        pass

    print(f"maps_valid={len(maps)}")
    print("training_maps=12")
    print("test_maps=30")
    print("experiment_rows=90")
    print("sample_agents_success=3/3")
    print("delivery_artifacts=ok")


if __name__ == "__main__":
    main()
