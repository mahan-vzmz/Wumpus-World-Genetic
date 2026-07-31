from __future__ import annotations
import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable, Sequence
from environment import WumpusEnvironment
from genetic_agent import GENE_BOUNDS, GENE_NAMES, GeneticAgent, GeneticWeights
from map_parser import MapConfig, load_map

Genome = list[float]


@dataclass(frozen=True)
class EpisodeEvaluation:
    success: bool
    fitness: float
    steps: int
    remaining_health: int
    collected_gold: int
    pit_entries: int
    termination_reason: str
    score: int


@dataclass(frozen=True)
class GenerationRecord:
    generation: int
    best_fitness: float
    average_fitness: float
    worst_fitness: float


@dataclass(frozen=True)
class TrainingResult:
    best_weights: GeneticWeights
    best_fitness: float
    history: tuple[GenerationRecord, ...]
    seed: int
    map_count: int


class GeneticTrainer:
    def __init__(
        self,
        configs: Sequence[MapConfig],
        *,
        population_size: int = 24,
        generations: int = 24,
        mutation_rate: float = 0.10,
        mutation_sigma: float = 2.0,
        crossover_rate: float = 0.90,
        elite_count: int = 2,
        tournament_size: int = 3,
        max_steps: int = 250,
        seed: int = 17,
        patience: int | None = 8,
    ):
        if not configs:
            raise ValueError("At least one training map is required.")
        if population_size < 4:
            raise ValueError("Population size must be at least 4.")
        if generations < 1:
            raise ValueError("Generations must be positive.")
        if not 0.0 <= mutation_rate <= 1.0:
            raise ValueError("Mutation rate must be between 0 and 1.")
        if mutation_sigma < 0:
            raise ValueError("Mutation sigma cannot be negative.")
        if not 0.0 <= crossover_rate <= 1.0:
            raise ValueError("Crossover rate must be between 0 and 1.")
        if not 1 <= elite_count < population_size:
            raise ValueError("Elite count must be between 1 and population_size - 1.")
        if not 2 <= tournament_size <= population_size:
            raise ValueError("Invalid tournament size.")
        if max_steps < 1:
            raise ValueError("max_steps must be positive.")
        if patience is not None and patience < 1:
            raise ValueError("patience must be positive or None.")

        self.configs = list(configs)
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.mutation_sigma = mutation_sigma
        self.crossover_rate = crossover_rate
        self.elite_count = elite_count
        self.tournament_size = tournament_size
        self.max_steps = max_steps
        self.seed = seed
        self.patience = patience
        self.rng = random.Random(seed)
        self._fitness_cache: dict[tuple[float, ...], float] = {}

    def train(self, verbose: bool = True) -> TrainingResult:
        population = self._initial_population()
        history: list[GenerationRecord] = []
        global_best: Genome | None = None
        global_best_fitness = -math.inf
        stale_generations = 0

        for generation in range(self.generations):
            fitnesses = [self.evaluate_genome(genome) for genome in population]
            ranked = sorted(
                zip(population, fitnesses), key=lambda item: item[1], reverse=True
            )
            generation_best_genome, generation_best = ranked[0]
            record = GenerationRecord(
                generation=generation,
                best_fitness=generation_best,
                average_fitness=mean(fitnesses),
                worst_fitness=min(fitnesses),
            )
            history.append(record)

            if verbose:
                print(
                    f"generation={generation:02d} best={record.best_fitness:.2f} "
                    f"average={record.average_fitness:.2f} worst={record.worst_fitness:.2f}"
                )

            if generation_best > global_best_fitness + 1e-9:
                global_best = list(generation_best_genome)
                global_best_fitness = generation_best
                stale_generations = 0
            else:
                stale_generations += 1

            if self.patience is not None and stale_generations >= self.patience:
                if verbose:
                    print(
                        f"early_stop=True reason=no_improvement_for_{self.patience}_generations"
                    )
                break

            next_population = [
                list(genome) for genome, _ in ranked[: self.elite_count]
            ]
            while len(next_population) < self.population_size:
                parent1 = self._tournament_select(population, fitnesses)
                parent2 = self._tournament_select(population, fitnesses)
                child1, child2 = self._crossover(parent1, parent2)
                next_population.append(self._mutate(child1))
                if len(next_population) < self.population_size:
                    next_population.append(self._mutate(child2))
            population = next_population

        if global_best is None:
            raise RuntimeError("Genetic training produced no candidate.")
        return TrainingResult(
            best_weights=GeneticWeights.from_genome(global_best).clipped(),
            best_fitness=global_best_fitness,
            history=tuple(history),
            seed=self.seed,
            map_count=len(self.configs),
        )

    def evaluate_genome(self, genome: Sequence[float]) -> float:
        clipped = tuple(round(value, 8) for value in self._clip_genome(genome))
        cached = self._fitness_cache.get(clipped)
        if cached is not None:
            return cached
        weights = GeneticWeights.from_genome(clipped)
        evaluations = [
            evaluate_episode(config, weights, max_steps=self.max_steps)
            for config in self.configs
        ]
        value = mean(item.fitness for item in evaluations)
        self._fitness_cache[clipped] = value
        return value

    def _initial_population(self) -> list[Genome]:
        population: list[Genome] = [GeneticWeights().as_genome()]
        while len(population) < self.population_size:
            population.append(
                [self.rng.uniform(*GENE_BOUNDS[name]) for name in GENE_NAMES]
            )
        return population

    def _tournament_select(
        self, population: Sequence[Genome], fitnesses: Sequence[float]
    ) -> Genome:
        indexes = self.rng.sample(range(len(population)), self.tournament_size)
        winner = max(indexes, key=lambda index: fitnesses[index])
        return list(population[winner])

    def _crossover(self, parent1: Genome, parent2: Genome) -> tuple[Genome, Genome]:
        if self.rng.random() >= self.crossover_rate:
            return list(parent1), list(parent2)
        child1: Genome = []
        child2: Genome = []
        for value1, value2 in zip(parent1, parent2):
            alpha = self.rng.random()
            child1.append(alpha * value1 + (1.0 - alpha) * value2)
            child2.append((1.0 - alpha) * value1 + alpha * value2)
        return self._clip_genome(child1), self._clip_genome(child2)

    def _mutate(self, genome: Genome) -> Genome:
        mutated = list(genome)
        for index, name in enumerate(GENE_NAMES):
            if self.rng.random() < self.mutation_rate:
                mutated[index] += self.rng.gauss(0.0, self.mutation_sigma)
        return self._clip_genome(mutated)

    @staticmethod
    def _clip_genome(genome: Iterable[float]) -> Genome:
        values = list(genome)
        if len(values) != len(GENE_NAMES):
            raise ValueError(
                f"Genome must contain {len(GENE_NAMES)} genes; got {len(values)}."
            )
        clipped: Genome = []
        for name, value in zip(GENE_NAMES, values):
            lower, upper = GENE_BOUNDS[name]
            clipped.append(max(lower, min(upper, float(value))))
        return clipped


def evaluate_episode(
    config: MapConfig,
    weights: GeneticWeights,
    *,
    max_steps: int = 250,
) -> EpisodeEvaluation:
    env = WumpusEnvironment(config)
    agent = GeneticAgent(config, weights)
    observation = env.reset()
    agent.reset()

    for _ in range(max_steps):
        try:
            action = agent.choose_action(observation)
        except RuntimeError:
            env.terminate("agent_stopped")
            break
        observation, _, done, _ = env.step(action)
        if done:
            break
    if not env.state.done:
        env.terminate("max_steps")

    reason = env.state.termination_reason or "unknown"
    fitness = episode_fitness(
        success=env.state.success,
        collected_gold=env.state.collected_gold,
        remaining_health=env.state.health,
        steps=env.state.steps,
        pit_entries=env.state.pit_entries,
        termination_reason=reason,
    )
    return EpisodeEvaluation(
        success=env.state.success,
        fitness=fitness,
        steps=env.state.steps,
        remaining_health=env.state.health,
        collected_gold=env.state.collected_gold,
        pit_entries=env.state.pit_entries,
        termination_reason=reason,
        score=env.state.score,
    )


def episode_fitness(
    *,
    success: bool,
    collected_gold: int,
    remaining_health: int,
    steps: int,
    pit_entries: int,
    termination_reason: str,
) -> float:

    value = 1500.0 if success else 0.0
    value += 250.0 * collected_gold
    value += 2.0 * remaining_health
    value -= 2.0 * steps
    value -= 180.0 * pit_entries
    terminal_penalties = {
        "wumpus": -1400.0,
        "health_depleted": -800.0,
        "escaped_without_gold": -700.0,
        "max_steps": -400.0,
        "agent_stopped": -500.0,
    }
    value += terminal_penalties.get(termination_reason, 0.0)
    return value


def load_training_configs(paths: Sequence[str | Path]) -> list[MapConfig]:
    return [load_map(path) for path in paths]


def save_training_artifacts(
    result: TrainingResult,
    *,
    weights_path: str | Path,
    history_csv_path: str | Path,
    summary_json_path: str | Path,
) -> None:
    result.best_weights.save(
        weights_path,
        metadata={
            "best_fitness": result.best_fitness,
            "seed": result.seed,
            "map_count": result.map_count,
            "generations_run": len(result.history),
        },
    )

    history_path = Path(history_csv_path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "generation",
                "best_fitness",
                "average_fitness",
                "worst_fitness",
            ),
        )
        writer.writeheader()
        for record in result.history:
            writer.writerow(
                {
                    "generation": record.generation,
                    "best_fitness": f"{record.best_fitness:.6f}",
                    "average_fitness": f"{record.average_fitness:.6f}",
                    "worst_fitness": f"{record.worst_fitness:.6f}",
                }
            )

    summary = {
        "best_fitness": result.best_fitness,
        "seed": result.seed,
        "map_count": result.map_count,
        "generations_run": len(result.history),
        "best_weights": {
            name: getattr(result.best_weights, name) for name in GENE_NAMES
        },
    }
    summary_path = Path(summary_json_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def plot_history(result: TrainingResult, path: str | Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    generations = [item.generation for item in result.history]
    best = [item.best_fitness for item in result.history]
    average = [item.average_fitness for item in result.history]
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    plt.plot(generations, best, label="Best fitness")
    plt.plot(generations, average, label="Average fitness")
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title("Genetic Algorithm Training Progress")
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()
