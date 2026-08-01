# Experiment Results

This directory contains generated outputs from running `train_genetic.py` and `experiment.py`. 

## Source vs Generated
- These files are **generated automatically** and should not be manually edited.
- The only tracked source file is `best_weights.json` (at the repository root) which is the output of the genetic algorithm training phase.

## Contents
- **`final/`**: Contains the final evaluation results on the unseen test maps.
  - `summary_results.csv`: Aggregate statistics (Success rate, Avg Score, etc.) for each agent.
  - `difficulty_results.csv`: Breakdown of success rates by map difficulty.
  - `experiment_results.csv`: Raw episode-by-episode logs for all 90 evaluation runs.
- **Charts (`*.png`)**: Visualizations of the results (success rates, failures, runtimes, etc.).
- **`genetic_history.csv` / `genetic_fitness.png`**: Logs and learning curve for the genetic algorithm training phase.

*Note: Results are reproducible given the fixed seeds defined in the root scripts (`seed=17` for training, `seed=20260730` for testing).*
