# Changelog

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
- Added GitHub Actions, MIT License, reproducible report/slide generation, and synchronized documentation.
