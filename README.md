# Wumpus World: Comparing A*, Rule-Based, and Genetic Agents

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)
[![Version](https://img.shields.io/badge/version-8.1.1-success.svg)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://github.com/mahan-vzmz/Wumpus-World-Genetic/actions/workflows/tests.yml/badge.svg)](https://github.com/mahan-vzmz/Wumpus-World-Genetic/actions)

> 🇮🇷 **Persian speakers:** For the Persian documentation, please read [README_FA.md](README_FA.md).

A reproducible, fully-tested Python implementation of the classic AI environment **Wumpus World** on an 8x8 grid. This project compares three different artificial intelligence paradigms:

1.  **A-Star Search (Oracle)**: Has full map knowledge. Acts as the theoretical upper bound for performance.
2.  **Rule-Based Agent (Online)**: Uses Propositional Logic, a Knowledge Base, and safe backtracking based purely on local perceptions (Breeze, Stench).
3.  **Hybrid Genetic Agent (Online)**: Combines local logic reasoning with a heuristic policy whose 10 numerical weights are evolved through a Genetic Algorithm.


## Main Results

Evaluated on 30 unseen test maps (10 easy, 10 medium, 10 hard) over 90 episodes:

| Agent | Success Rate | Average Score | Avg Steps (All) | Avg Steps (Success) |
|---|---:|---:|---:|---:|
| **A-Star** | 100.00% | 157.60 | 12.40 | 12.40 |
| **Rule-Based** | 90.00% | 117.93 | 32.90 | 32.30 |
| **Hybrid Genetic** | 83.33% | 120.97 | 31.80 | 24.60 |

*Scientific Note*: A-Star is an Oracle with perfect information. The real comparison is between the Rule-Based and Genetic agents. The Rule-Based agent is more reliable (higher success rate), but the Hybrid Genetic agent finds much shorter paths during successful episodes.

## Quick Installation

```bash
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux / Mac)
source .venv/bin/activate

# Install package and dependencies
pip install -e .
```

## Quick Start & Usage

Run all three agents on a sample map and print the benchmark results:
```bash
wumpus-world-demo --map maps/sample_01.txt
```

Run a specific agent individually:
```bash
wumpus-world --agent astar --map maps/sample_astar_pit.txt
wumpus-world --agent rule --map maps/sample_rule_reasoning.txt --max-steps 250
wumpus-world --agent genetic --map maps/sample_01.txt
```

You can also run the package directly:
```bash
python -m wumpus_world --help
```

*Note: `best_weights.json` is the canonical weight file for version 8.1.x and contains trained gene values and training metadata. To use default hardcoded weights instead, pass `--use-default-weights`.*

## Documentation

- [Persian README](README_FA.md)
- [Final PDF Report](docs/final_report/final_report.pdf)
- [Project Audit](PROJECT_AUDIT.md)
- [Experiment Results](results/final/summary_results.csv)
- [Changelog](CHANGELOG.md)

## Experiment & Training

To run the full benchmark experiment (generates 30 maps, tests all agents, outputs CSV/PNGs):
```bash
python experiment.py
```

To re-train the genetic algorithm from scratch on new random maps:
```bash
python train_genetic.py --regenerate-training-maps
```

## Architecture & Structure

```text
src/wumpus_world/
├── __init__.py
├── __main__.py
├── cli.py
├── demo.py
├── runner.py
├── environment.py         # Rules, Grid, Percepts, Game loop
├── knowledge_base.py      # Logic inference for online agents
├── map_parser.py          # Strict validation and parsing
├── map_generator.py       # Procedural generation (Easy/Medium/Hard)
├── agents/
│   ├── base_agent.py      # Base interface
│   ├── astar_agent.py     # Oracle pathfinding
│   ├── rule_based_agent.py# Logical inference agent
│   └── genetic_agent.py   # Weighted heuristic + logic
└── training/
    └── genetic_algorithm.py

tests/                     # Automated tests suite
maps/                      # Static map samples
results/                   # Experiment outputs (CSV, Charts)
docs/                      # Reports and assets
```

## Limitations

- The Genetic agent uses a linear policy combination and does not guarantee optimal performance.
- Execution times rely on hardware and are reported using repeated medians.
- The A-Star agent solves the problem fundamentally differently (offline/oracle) and is only included as a theoretical ceiling.

## License

This project is licensed under the [MIT License](LICENSE).
