from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from numbers import Real
from time import perf_counter

from models.numeric import finite_real
from models.player_identity import logical_player_identity
from models.team import Team
from optimizer.global_search.global_bound_calculator import (
    GlobalBoundCalculator,
)
from optimizer.global_search.global_bound_safety import (
    assess_compatibility,
    certified_decision,
    select_root,
)
from optimizer.global_search.global_optimization_config import (
    GlobalOptimizationConfig,
)
from optimizer.global_search.global_optimization_result import (
    GlobalOptimizationResult,
)
from optimizer.global_search.global_proof_certificate import GlobalProofCertificate
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

        if bound_calculator.pruning_policy != config.pruning_policy:
            raise ValueError("Bound calculator pruning policy must match GLOBAL config.")

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

        self._best_score: float | None = None
        self._initial_incumbent_score: float | None = None
        self._best_teams: tuple[Team, ...] | None = None

    def optimize(
        self,
        problem: GlobalSearchProblem,
        incumbent_teams: Sequence[Team] | None = None,
        incumbent_score: float | None = None,
    ) -> GlobalOptimizationResult:
        """
        Ejecuta la búsqueda GLOBAL.

        El incumbent se vuelve a evaluar con ObjectiveEngine para garantizar
        que score y composición pertenecen exactamente al mismo estado.
        """

        started = perf_counter()

        if not isinstance(
            problem,
            GlobalSearchProblem,
        ):
            raise TypeError(
                "problem must be a GlobalSearchProblem."
            )

        if not self._config.use_incumbent:
            if incumbent_teams is not None or incumbent_score is not None:
                raise ValueError("Incumbent data is forbidden when use_incumbent=False.")
            incumbent_team_list = None
        else:
            incumbent_team_list = self._validate_incumbent(problem, incumbent_teams)
        supplied_score = (
            finite_real(incumbent_score, "incumbent_score")
            if incumbent_score is not None else None
        )

        self._reset(problem, started=started)
        if incumbent_team_list is not None:
            verified_incumbent_score = self._evaluate_score(incumbent_team_list)
            if supplied_score is not None and abs(
                supplied_score - verified_incumbent_score
            ) > self._config.score_tolerance:
                raise RuntimeError(
                    "The supplied incumbent score does not match the ObjectiveEngine evaluation. "
                    f"Supplied={supplied_score:.8f}, verified={verified_incumbent_score:.8f}."
                )
            self._best_score = verified_incumbent_score
            self._initial_incumbent_score = verified_incumbent_score
            self._best_teams = tuple(incumbent_team_list)
            canonical = self._canonical_incumbent(problem, incumbent_team_list)
            # Metadata equality cannot establish a score witness: incoming caches
            # or object-sensitive objectives can differ from a fresh assignment.
            self._incumbent_in_domain = self._evaluate_score(canonical) == verified_incumbent_score
            if self._config.require_proof and not self._incumbent_in_domain:
                raise RuntimeError("Incumbent score has no exact witness in the canonical problem domain.")

        self._search(
            self._search_root
        )

        if self._best_teams is None:
            raise RuntimeError(
                "GLOBAL finished without a valid solution."
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

        final_exact = verified_best_score == self._best_score
        if self._config.require_proof and not final_exact:
            raise RuntimeError("GLOBAL proof requires an exact independent final score.")
        self._best_score = verified_best_score
        exhausted = not self._stopped and self._stop_reason == "SEARCH_EXHAUSTED"
        certificate = GlobalProofCertificate(
            search_exhausted=exhausted,
            root_complete=self._root_complete,
            symmetry_safe=not self._use_symmetry or self._compatibility.bitwise_symmetric,
            score_pruning_safe=self._score_prunes_safe,
            feasibility_pruning_safe=self._feasibility_prunes_safe and self._assignments_safe,
            ranking_exact=self._ranking_exact,
            incumbent_in_domain=self._incumbent_in_domain,
            final_score_exact=final_exact,
            bound_strategy=self._compatibility.strategy,
            root_expanded=self._search_root is not problem.root_state,
            traversal_verified=self._traversal_verified and self._verified_traversal(),
        )
        optimality_proven = certificate.optimality_proven

        if (
            self._config.require_proof
            and exhausted
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
            elapsed_seconds=perf_counter() - self._start_time,
            optimality_proven=optimality_proven,
            stopped_by_limit=self._stopped,
            stop_reason=self._stop_reason,
            proof_certificate=certificate,
        )

    @staticmethod
    def _validate_incumbent(
        problem: GlobalSearchProblem, teams: Sequence[Team] | None
    ) -> list[Team]:
        if teams is None:
            raise ValueError("incumbent_teams is required when use_incumbent=True.")
        team_list = list(teams)
        if len(team_list) != problem.number_of_teams:
            raise ValueError("Incumbent team count does not match the problem.")
        if any(not isinstance(team, Team) for team in team_list):
            raise TypeError("incumbent_teams must contain Team instances.")
        if len({id(team) for team in team_list}) != len(team_list):
            raise ValueError("Incumbent contains duplicated Team instances.")
        if any(len(team.players) != problem.team_size for team in team_list):
            raise ValueError("Incumbent team size does not match the problem.")
        metrics_by_identity = {logical_player_identity(item.player): item for item in problem.players}
        if len(metrics_by_identity) != problem.player_count:
            raise ValueError("Problem contains duplicated logical identities.")
        identities = [logical_player_identity(player) for team in team_list for player in team.players]
        if len(set(identities)) != len(identities):
            raise ValueError("Incumbent contains duplicated logical identities.")
        if Counter(identities) != Counter(metrics_by_identity.keys()):
            raise ValueError("Incumbent logical player pool does not match the problem.")
        for team in team_list:
            protected_count = sum(
                problem.protected_seed_level is not None
                and metrics_by_identity[logical_player_identity(player)].seed == problem.protected_seed_level
                for player in team.players
            )
            if protected_count > problem.maximum_protected_seeds_per_team:
                raise ValueError("Incumbent violates the protected seed hard constraint.")
        return team_list

    @staticmethod
    def _canonical_incumbent(problem, teams):
        by_identity = {logical_player_identity(item.player): index for index, item in enumerate(problem.players)}
        return [Team(index + 1, [problem.players[player_index].player for player_index in sorted(
            by_identity[logical_player_identity(player)] for player in team.players)])
            for index, team in enumerate(teams)]

    def _verified_traversal(self) -> bool:
        for name, (expected, code) in _PROOF_TRAVERSAL.items():
            method = getattr(self, name)
            function = getattr(method, "__func__", method)
            if function is not expected or getattr(function, "__code__", None) is not code:
                return False
        return True

    def _reset(
        self,
        problem: GlobalSearchProblem,
        *,
        started: float | None = None,
    ) -> None:
        self._problem = problem
        self._start_time = perf_counter() if started is None else started

        self._nodes_visited = 0
        self._complete_evaluations = 0
        self._pruned_nodes = 0
        self._capacity_prunes = 0
        self._seed_prunes = 0
        self._bound_prunes = 0

        self._stopped = False
        self._stop_reason = "SEARCH_EXHAUSTED"

        self._best_score = None
        self._initial_incumbent_score = None
        self._best_teams = None
        self._compatibility = assess_compatibility(self._objective_engine, problem, self._bound_calculator)
        self._search_root, self._root_complete = select_root(problem, self._compatibility, self._config.require_proof)
        self._use_symmetry = self._config.use_symmetry_breaking and (
            self._compatibility.bitwise_symmetric if self._config.require_proof else self._compatibility.symmetric)
        self._score_prunes_safe = True
        self._feasibility_prunes_safe = True
        self._assignments_safe = True
        self._traversal_verified = self._verified_traversal()
        if self._config.require_proof and not self._traversal_verified:
            raise RuntimeError("require_proof needs a verified traversal implementation.")
        self._ranking_exact = True
        self._incumbent_in_domain = True

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

        bound, safe = certified_decision(
            self._bound_calculator, self._compatibility, problem, state,
            self._best_score, self._config.require_proof,
        )

        if bound.prune:
            if bound.reason == "upper_bound":
                self._score_prunes_safe = self._score_prunes_safe and safe
            else:
                self._feasibility_prunes_safe = self._feasibility_prunes_safe and safe
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

        if player is not problem.players[state.next_player_index]:
            if self._config.require_proof:
                raise RuntimeError("next_player must match the canonical problem prefix.")
            self._assignments_safe = False

        if player is None:
            raise RuntimeError(
                "Incomplete state does not expose a next player."
            )

        if self._use_symmetry:
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

        if self._use_symmetry:
            expected = []
            empty_seen = False
            for index, team in enumerate(state.teams):
                if team.player_count >= problem.team_size:
                    continue
                if team.player_count == 0:
                    if empty_seen:
                        continue
                    empty_seen = True
                expected.append(index)
            if tuple(team_indices) != tuple(expected):
                if self._config.require_proof:
                    raise RuntimeError("Unverified symmetry rule changed the candidate set.")
                self._assignments_safe = False

        if not team_indices:
            return

        allowed = tuple(team_indices)
        team_indices = self._order_candidate_teams(
            state=state,
            team_indices=team_indices,
            player=player,
        )

        if sorted(team_indices) != sorted(allowed):
            if self._config.require_proof:
                raise RuntimeError("Branch ordering must be a permutation of available candidates.")
            self._assignments_safe = False

        for team_index in team_indices:
            if self._stopped:
                return

            team = state.teams[team_index]
            hard_rejection = team.player_count >= problem.team_size or (
                problem.protected_seed_level is not None and player.seed == problem.protected_seed_level
                and team.protected_seed_count >= problem.maximum_protected_seeds_per_team)
            if hard_rejection:
                continue
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
                # Overflow/unknown failures are not hard-constraint proofs.
                self._assignments_safe = False
                if self._config.require_proof:
                    raise
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

        if self._limit_reached(entering_node=False):
            return

        teams = self._build_teams_from_state(
            state
        )

        score = self._evaluate_score(
            teams
        )

        self._complete_evaluations += 1

        if self._best_score is not None:
            improved = score > self._best_score if self._config.require_proof else self._config.score_improves(
                candidate=score, current_best=self._best_score)
            if not improved:
                if score > self._best_score:
                    self._ranking_exact = False
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

        if isinstance(result, Real):
            return finite_real(result, "objective score")

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

        return finite_real(score, "objective score")

    def _limit_reached(self, *, entering_node: bool = True) -> bool:
        if self._stopped:
            return True

        config = self._config

        if (
            entering_node
            and config.maximum_nodes is not None
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
    def best_score(self) -> float | None:
        return self._best_score

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
        score_label = "None" if self._best_score is None else f"{self._best_score:.4f}"
        return (
            f"{self.__class__.__name__}("
            f"nodes={self._nodes_visited}, "
            f"evaluations={self._complete_evaluations}, "
            f"best_score={score_label}, "
            f"stopped={self._stopped}, "
            f"stop_reason={self._stop_reason!r})"
        )


# Proof relies on the audited DFS/evaluation/validation, not just a stop label.
# Reordering remains customizable: _search separately validates its permutation.
_PROOF_TRAVERSAL = {
    name: (getattr(GlobalOptimizer, name), getattr(GlobalOptimizer, name).__code__)
    for name in ("_search", "_reset", "_evaluate_complete_state", "_evaluate_score",
                 "_build_teams_from_state", "_create_team", "_validate_incumbent",
                 "_canonical_incumbent", "_require_problem", "_limit_reached")
}
