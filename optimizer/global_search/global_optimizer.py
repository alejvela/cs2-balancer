from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter

from models.team import Team
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
)
from optimizer.global_search.global_optimization_config import (
    GlobalOptimizationConfig,
)
from optimizer.global_search.global_optimization_result import (
    GlobalOptimizationResult,
)
from optimizer.global_search.global_search_problem import (
    GlobalSearchProblem,
)
from optimizer.global_search.global_search_state import (
    GlobalSearchState,
)


class GlobalOptimizer:
    """
    Solver GLOBAL mediante Depth First Search + Branch & Bound.

    Principios:
        - determinismo;
        - incumbent fuerte procedente de STABLE;
        - podas matemáticamente seguras;
        - conservación exacta de los Team evaluados;
        - verificación final contra ObjectiveEngine.
    """

    def __init__(
        self,
        objective_engine,
        config: GlobalOptimizationConfig,
        bound_calculator: GlobalBoundCalculator,
    ) -> None:
        if objective_engine is None:
            raise ValueError(
                "objective_engine cannot be None."
            )

        if not isinstance(
            config,
            GlobalOptimizationConfig,
        ):
            raise TypeError(
                "config must be a GlobalOptimizationConfig."
            )

        if not isinstance(
            bound_calculator,
            GlobalBoundCalculator,
        ):
            raise TypeError(
                "bound_calculator must be a GlobalBoundCalculator."
            )

        self._objective_engine = objective_engine
        self._config = config
        self._bound_calculator = bound_calculator

        self._problem: GlobalSearchProblem | None = None
        self._start_time = 0.0

        self._nodes_visited = 0
        self._complete_evaluations = 0
        self._pruned_nodes = 0
        self._capacity_prunes = 0
        self._seed_prunes = 0
        self._bound_prunes = 0

        self._stopped = False
        self._stop_reason = "SEARCH_EXHAUSTED"

        self._best_score = float("-inf")
        self._initial_incumbent_score = float("-inf")
        self._best_teams: tuple[Team, ...] | None = None

    def optimize(
        self,
        problem: GlobalSearchProblem,
        incumbent_teams: Sequence[Team],
        incumbent_score: float | None = None,
    ) -> GlobalOptimizationResult:
        """
        Ejecuta la búsqueda GLOBAL.

        El incumbent se vuelve a evaluar con ObjectiveEngine para garantizar
        que score y composición pertenecen exactamente al mismo estado.
        """

        if not isinstance(
            problem,
            GlobalSearchProblem,
        ):
            raise TypeError(
                "problem must be a GlobalSearchProblem."
            )

        if incumbent_teams is None:
            raise ValueError(
                "incumbent_teams cannot be None."
            )

        incumbent_team_list = list(
            incumbent_teams
        )

        if not incumbent_team_list:
            raise ValueError(
                "incumbent_teams cannot be empty."
            )

        for index, team in enumerate(
            incumbent_team_list,
            start=1,
        ):
            if not isinstance(team, Team):
                raise TypeError(
                    "incumbent_teams must contain Team instances. "
                    f"Invalid item at position {index}."
                )

        self._reset(problem)

        verified_incumbent_score = self._evaluate_score(
            incumbent_team_list
        )

        if incumbent_score is not None:
            supplied_incumbent_score = float(
                incumbent_score
            )

            if abs(
                supplied_incumbent_score
                - verified_incumbent_score
            ) > self._config.score_tolerance:
                raise RuntimeError(
                    "The supplied incumbent score does not match "
                    "the ObjectiveEngine evaluation. "
                    f"Supplied={supplied_incumbent_score:.8f}, "
                    f"verified={verified_incumbent_score:.8f}."
                )

        self._best_score = verified_incumbent_score
        self._initial_incumbent_score = verified_incumbent_score
        self._best_teams = tuple(
            incumbent_team_list
        )

        self._search(
            problem.root_state
        )

        elapsed = (
            perf_counter()
            - self._start_time
        )

        if self._best_teams is None:
            raise RuntimeError(
                "GLOBAL finished without a valid incumbent."
            )

        verified_best_score = self._evaluate_score(
            self._best_teams
        )

        if abs(
            verified_best_score
            - self._best_score
        ) > self._config.score_tolerance:
            raise RuntimeError(
                "GLOBAL internal consistency error: "
                "the stored best score does not match "
                "the stored best teams. "
                f"Stored={self._best_score:.8f}, "
                f"verified={verified_best_score:.8f}."
            )

        self._best_score = verified_best_score

        optimality_proven = (
            not self._stopped
            and self._stop_reason
            == "SEARCH_EXHAUSTED"
        )

        if (
            self._config.require_proof
            and not optimality_proven
        ):
            self._stop_reason = (
                "PROOF_NOT_COMPLETED"
            )

        return GlobalOptimizationResult(
            teams=self._best_teams,
            score=self._best_score,
            initial_incumbent_score=(
                self._initial_incumbent_score
            ),
            nodes_visited=(
                self._nodes_visited
            ),
            complete_solutions_evaluated=(
                self._complete_evaluations
            ),
            pruned_nodes=(
                self._pruned_nodes
            ),
            capacity_prunes=(
                self._capacity_prunes
            ),
            seed_prunes=(
                self._seed_prunes
            ),
            bound_prunes=(
                self._bound_prunes
            ),
            elapsed_seconds=elapsed,
            optimality_proven=optimality_proven,
            stopped_by_limit=self._stopped,
            stop_reason=self._stop_reason,
        )

    def _reset(
        self,
        problem: GlobalSearchProblem,
    ) -> None:
        self._problem = problem
        self._start_time = perf_counter()

        self._nodes_visited = 0
        self._complete_evaluations = 0
        self._pruned_nodes = 0
        self._capacity_prunes = 0
        self._seed_prunes = 0
        self._bound_prunes = 0

        self._stopped = False
        self._stop_reason = "SEARCH_EXHAUSTED"

        self._best_score = float("-inf")
        self._initial_incumbent_score = float("-inf")
        self._best_teams = None

    def _search(
        self,
        state: GlobalSearchState,
    ) -> None:
        if self._stopped:
            return

        if self._limit_reached():
            return

        self._nodes_visited += 1

        problem = self._require_problem()

        bound = self._bound_calculator.evaluate(
            problem=problem,
            state=state,
            incumbent_score=self._best_score,
        )

        if bound.prune:
            self._pruned_nodes += 1

            if bound.reason == "capacity_impossible":
                self._capacity_prunes += 1
            elif bound.reason == "seed_impossible":
                self._seed_prunes += 1
            elif bound.reason == "upper_bound":
                self._bound_prunes += 1

            return

        if state.is_complete(
            problem.player_count
        ):
            self._evaluate_complete_state(
                state
            )
            return

        player = problem.next_player(
            state
        )

        if player is None:
            raise RuntimeError(
                "Incomplete state does not expose a next player."
            )

        if self._config.use_symmetry_breaking:
            team_indices = (
                state.canonical_available_team_indices(
                    problem.team_size
                )
            )
        else:
            team_indices = tuple(
                index
                for index, team in enumerate(
                    state.teams
                )
                if team.player_count < problem.team_size
            )

        if not team_indices:
            return

        team_indices = self._order_candidate_teams(
            state=state,
            team_indices=team_indices,
            player=player,
        )

        for team_index in team_indices:
            if self._stopped:
                return

            if self._limit_reached():
                return

            try:
                child = state.assign_next_player(
                    team_index=team_index,
                    metrics=player,
                    team_size=problem.team_size,
                    protected_seed_level=(
                        problem.protected_seed_level
                    ),
                    maximum_protected_seeds_per_team=(
                        problem.maximum_protected_seeds_per_team
                    ),
                )
            except ValueError:
                continue

            self._search(
                child
            )

    def _order_candidate_teams(
        self,
        state: GlobalSearchState,
        team_indices: tuple[int, ...],
        player,
    ) -> tuple[int, ...]:
        """
        Ordena ramas sin podarlas, explorando primero las que acercan
        el Power acumulado al objetivo medio por equipo.
        """

        if not team_indices:
            return ()

        problem = self._require_problem()

        total_power = sum(
            metric.power
            for metric in problem.players
        )

        target_team_power = (
            total_power
            / problem.number_of_teams
        )

        def key(
            team_index: int,
        ) -> tuple[float, int, int]:
            team = state.teams[
                team_index
            ]

            projected_power = (
                team.power_sum
                + player.power
            )

            distance = abs(
                target_team_power
                - projected_power
            )

            return (
                distance,
                team.player_count,
                team_index,
            )

        return tuple(
            sorted(
                team_indices,
                key=key,
            )
        )

    def _evaluate_complete_state(
        self,
        state: GlobalSearchState,
    ) -> None:
        if self._stopped:
            return

        if self._limit_reached():
            return

        teams = self._build_teams_from_state(
            state
        )

        score = self._evaluate_score(
            teams
        )

        self._complete_evaluations += 1

        if not self._config.score_improves(
            candidate=score,
            current_best=self._best_score,
        ):
            return

        self._best_score = float(
            score
        )

        # Guardamos exactamente los Team que ObjectiveEngine acaba
        # de evaluar. No se clonan después de calcular el score.
        self._best_teams = tuple(
            teams
        )

    def _build_teams_from_state(
        self,
        state: GlobalSearchState,
    ) -> list[Team]:
        problem = self._require_problem()
        teams: list[Team] = []

        for team_index, team_state in enumerate(
            state.teams,
            start=1,
        ):
            players = [
                problem.players[player_index].player
                for player_index in team_state.player_indices
            ]

            teams.append(
                self._create_team(
                    team_index=team_index,
                    players=players,
                )
            )

        return teams

    @staticmethod
    def _create_team(
        team_index: int,
        players,
    ) -> Team:
        if (
            isinstance(team_index, bool)
            or not isinstance(team_index, int)
        ):
            raise TypeError(
                "team_index must be an integer."
            )

        if team_index <= 0:
            raise ValueError(
                "team_index must be greater than zero."
            )

        return Team(
            id=team_index,
            players=list(players),
        )

    def _evaluate_score(
        self,
        teams: Sequence[Team],
    ) -> float:
        result = self._objective_engine.evaluate(
            teams
        )

        if isinstance(result, bool):
            raise TypeError(
                "ObjectiveEngine cannot return bool."
            )

        if isinstance(result, (int, float)):
            return float(result)

        score = getattr(
            result,
            "score",
            None,
        )

        if score is None:
            score = getattr(
                result,
                "final_score",
                None,
            )

        if score is None:
            raise AttributeError(
                "ObjectiveEngine result does not expose "
                "score or final_score."
            )

        return float(score)

    def _limit_reached(self) -> bool:
        if self._stopped:
            return True

        config = self._config

        if (
            config.maximum_nodes is not None
            and self._nodes_visited
            >= config.maximum_nodes
        ):
            self._stopped = True
            self._stop_reason = "NODE_LIMIT"
            return True

        if (
            config.maximum_evaluations is not None
            and self._complete_evaluations
            >= config.maximum_evaluations
        ):
            self._stopped = True
            self._stop_reason = "EVALUATION_LIMIT"
            return True

        if config.maximum_elapsed_seconds is not None:
            elapsed = (
                perf_counter()
                - self._start_time
            )

            if elapsed >= config.maximum_elapsed_seconds:
                self._stopped = True
                self._stop_reason = "TIME_LIMIT"
                return True

        return False

    def _require_problem(self) -> GlobalSearchProblem:
        if self._problem is None:
            raise RuntimeError(
                "GLOBAL search problem has not been initialized."
            )
        return self._problem

    @property
    def nodes_visited(self) -> int:
        return self._nodes_visited

    @property
    def complete_evaluations(self) -> int:
        return self._complete_evaluations

    @property
    def pruned_nodes(self) -> int:
        return self._pruned_nodes

    @property
    def best_score(self) -> float:
        return float(
            self._best_score
        )

    @property
    def best_teams(self) -> tuple[Team, ...] | None:
        return self._best_teams

    @property
    def stopped(self) -> bool:
        return self._stopped

    @property
    def stop_reason(self) -> str:
        return self._stop_reason

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"nodes={self._nodes_visited}, "
            f"evaluations={self._complete_evaluations}, "
            f"best_score={self._best_score:.4f}, "
            f"stopped={self._stopped}, "
            f"stop_reason={self._stop_reason!r})"
        )
