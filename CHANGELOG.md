# Changelog

## Version 8.1.1

### Fixed

- Synchronized root source and packaged genetic weights hash.
- Added strict experiment metadata validation and tracked `source_commit`.
- Fixed report data drift: all success rates and training parameters are now generated dynamically from results.
- Fixed Matplotlib headless backend initialization order (`MPLBACKEND` / `matplotlib.use("Agg")`).
- Separated public (`project_info.public.json`) and local academic (`project_info.json`) report metadata.

### Added

- Added `tools/sync_packaged_weights.py` to synchronize packaged data weights.
- Added comprehensive repository consistency checks in `tools/check_repository_consistency.py`.
- Added wheel installation validation and delivery verification jobs in CI.
- Packaged default maps and trained weights into wheel data.

## Version 8.1.0

### Added

- Added package-based CLI entry points: `wumpus-world` and `wumpus-world-demo`.
- Added `wumpus_world.runner`, `wumpus_world.cli`, and `wumpus_world.demo`.
- Added support for `python -m wumpus_world`.
- Added automated CLI smoke tests.
- Added experiment artifact uploads in GitHub Actions.

### Changed

- Migrated runtime imports to the `src/wumpus_world` package.
- Updated setuptools package discovery for the `src` layout.
- Updated CI to install the project before linting and testing.
- Synchronized English and Persian documentation with the package layout.
- Updated project version to `8.1.0`.

### Removed

- Removed the root-level `main.py`.
- Removed the root-level `demo_all.py`.
- Removed outdated references to presentation artifacts.
- Removed the broken README demo image placeholder.

### Fixed

- Fixed clean-environment imports in GitHub Actions.
- Fixed console scripts so they work outside the repository root.
- Added a clear error when `project_info.json` is missing.

## Version 8.0.0 - Final delivery candidate

- Fixed correct `max_steps` termination and reporting.
- Added strict map validation and clear input errors.
- Added explicit knowledge of a pit after the agent survives entering it.
- Removed duplicate A-Star planning from benchmark timing.
- Made missing genetic weight files fail explicitly instead of silently using defaults.
- Redesigned deterministic map generation with varied exits, gold positions, path lengths, and equal initial health.
- Added successful-episode step metrics and repeated median runtime measurement.
- Re-trained the genetic policy on 12 training maps and evaluated all agents on 30 separate test maps.
- Expanded the test suite to 44 tests.
- Added GitHub Actions, MIT License, reproducible PDF report generation, and synchronized documentation.
