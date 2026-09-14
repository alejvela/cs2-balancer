"""Immutable production data consumed explicitly by composition factories."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from optimizer.global_search.global_optimization_config import GlobalOptimizationConfig
from optimizer.modes.optimization_mode import OptimizationMode
from optimizer.modes.stable_optimization_config import StableOptimizationConfig


def _nonnegative(**values: float) -> None:
    for name, value in values.items():
        if value < 0:
            raise ValueError(f"{name} cannot be negative")


@dataclass(frozen=True, slots=True)
class EventConfig:
    number_of_teams: int = 4
    team_size: int = 5
    name: str = "LAN CS2"
    report_title: str = "LAN CS2 — Análisis de equipos"
    team_name_prefix: str = "Equipo"
    preassigned_title: str = "Evaluación de equipos predeterminados"
    require_all_teams: bool = True
    importer_strict: bool = True

    def __post_init__(self) -> None:
        if self.number_of_teams <= 0 or self.team_size <= 0:
            raise ValueError("Team count and size must be positive")

    @property
    def expected_player_count(self) -> int:
        return self.number_of_teams * self.team_size


@dataclass(frozen=True, slots=True)
class PathsConfig:
    source_players: Path = Path("data/players.csv")
    generated_stats: Path = Path("data/players_stats.csv")
    faceit_errors: Path = Path("data/faceit_errors.csv")
    output_report: Path = Path("output/lan_report.html")


@dataclass(frozen=True, slots=True)
class FaceitConfig:
    run_import: bool = True
    preferred_game_id: str = "cs2"
    fallback_game_ids: tuple[str, ...] = ("csgo",)
    recent_matches: int = 30
    strict: bool = False
    delay_seconds: float = 0.25
    timeout_seconds: float = 20.0
    retries: int = 3
    retry_delay_seconds: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "fallback_game_ids", tuple(self.fallback_game_ids))
        _nonnegative(
            recent_matches=self.recent_matches,
            retries=self.retries,
            delay_seconds=self.delay_seconds,
            timeout_seconds=self.timeout_seconds,
            retry_delay_seconds=self.retry_delay_seconds,
        )


@dataclass(frozen=True, slots=True)
class ScoringComponentConfig:
    name: str
    attribute: str
    weight: float
    midpoint: float
    steepness: float
    default_score: float = 0.0

    def __post_init__(self) -> None:
        _nonnegative(weight=self.weight)


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    components: tuple[ScoringComponentConfig, ...] = field(
        default_factory=lambda: (
            ScoringComponentConfig("ELO", "elo", 40.0, 1800.0, -0.003),
            ScoringComponentConfig("KD", "kd", 25.0, 1.0, -8.0),
            ScoringComponentConfig("ADR", "adr", 15.0, 75.0, -0.10),
            ScoringComponentConfig("KPR", "kpr", 10.0, 0.70, -12.0),
            ScoringComponentConfig("Winrate", "winrate", 7.0, 50.0, -0.12),
            ScoringComponentConfig("HS", "hs", 3.0, 45.0, -0.08),
        )
    )
    minimum_available_weight: float = 40.0
    default_power: float = 0.0
    activity_factor: Literal["engine_defaults"] = "engine_defaults"

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", tuple(self.components))
        if len({c.name for c in self.components}) != len(self.components):
            raise ValueError("Scoring component names must be unique")
        if self.activity_factor != "engine_defaults":
            raise ValueError("Unsupported activity factor configuration")


@dataclass(frozen=True, slots=True)
class ObjectiveConfig:
    power_weight: float = 55.0
    elo_balance_weight: float = 10.0
    elo_spread_weight: float = 5.0
    kd_weight: float = 20.0
    team_size_weight: float = 9.0
    seed_weight: float = 1.0
    elo_midpoint: float = 120.0
    elo_steepness: float = 0.025
    ideal_spread: float = 100.0
    good_spread: float = 150.0
    acceptable_spread: float = 200.0
    poor_spread: float = 300.0
    maximum_spread: float = 400.0
    kd_max_deviation: float = 0.35
    penalty_per_position: float = 25.0
    seed_level: int = 1
    maximum_per_team: int = 1
    penalty_per_excess_player: float = 100.0
    maximum_penalty: float = 100.0

    def __post_init__(self) -> None:
        _nonnegative(
            **{
                name: getattr(self, name)
                for name in (
                    "power_weight",
                    "elo_balance_weight",
                    "elo_spread_weight",
                    "kd_weight",
                    "team_size_weight",
                    "seed_weight",
                )
            }
        )


@dataclass(frozen=True, slots=True)
class PhaseConfig:
    name: str
    strategy: Literal["first_improvement", "exhaustive"]
    max_iterations: int
    neighborhood: Literal["swap"] = "swap"
    minimum_improvement: float = 0.01
    enabled: bool = True
    stop_when_no_move: bool = True

    def __post_init__(self) -> None:
        if self.max_iterations <= 0:
            raise ValueError("max_iterations must be positive")
        if self.neighborhood != "swap" or self.strategy not in (
            "first_improvement",
            "exhaustive",
        ):
            raise ValueError("Unsupported pipeline component")


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    phases: tuple[PhaseConfig, ...] = field(
        default_factory=lambda: (
            PhaseConfig("Quick Swap Improvement", "first_improvement", 100),
            PhaseConfig("Final Swap Polish", "exhaustive", 30),
        )
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "phases", tuple(self.phases))
        if not self.phases:
            raise ValueError("Pipeline cannot be empty")
        if len({p.name for p in self.phases}) != len(self.phases):
            raise ValueError("Phase names must be unique")


@dataclass(frozen=True, slots=True)
class RestartConfig:
    separated_seed_level: int = 1
    maximum_seeded_players_per_team: int = 1
    minimum_swaps: int = 1
    maximum_swaps: int = 6
    partial_redistribution_ratio: float = 0.50

    def __post_init__(self) -> None:
        _nonnegative(minimum_swaps=self.minimum_swaps, maximum_swaps=self.maximum_swaps)
        if self.maximum_swaps < self.minimum_swaps:
            raise ValueError("maximum_swaps must be >= minimum_swaps")
        if not 0 <= self.partial_redistribution_ratio <= 1:
            raise ValueError("partial_redistribution_ratio must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class ApplicationConfig:
    event: EventConfig = field(default_factory=EventConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    faceit: FaceitConfig = field(default_factory=FaceitConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    objective: ObjectiveConfig = field(default_factory=ObjectiveConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    restart: RestartConfig = field(default_factory=RestartConfig)
    optimization_mode: OptimizationMode = OptimizationMode.GLOBAL
    debug_players: bool = False
    debug_final_teams: bool = True
    stable: StableOptimizationConfig = field(
        default_factory=lambda: StableOptimizationConfig(
            target_score=100.0,
            maximum_restarts=150,
            minimum_restarts=30,
            convergence_patience=30,
            score_tolerance=1e-6,
            base_seed=2026,
            target_confirmation_restarts=10,
            minimum_unique_solutions=20,
            maximum_total_evaluations=None,
            maximum_elapsed_seconds=None,
            stop_on_perfect_score=False,
            perfect_score=100.0,
        )
    )
    global_search: GlobalOptimizationConfig = field(
        default_factory=lambda: GlobalOptimizationConfig(
            maximum_nodes=500_000,
            maximum_evaluations=100_000,
            maximum_elapsed_seconds=60.0,
            score_tolerance=1e-6,
            minimum_improvement=1e-6,
            use_incumbent=True,
            use_symmetry_breaking=True,
            use_seed_pruning=True,
            use_capacity_pruning=True,
            use_power_bound=True,
            use_elo_bound=False,
            deterministic=True,
            require_proof=False,
            base_seed=2026,
        )
    )

    @classmethod
    def production_defaults(cls) -> "ApplicationConfig":
        """Return a fresh immutable production configuration."""
        return cls()
