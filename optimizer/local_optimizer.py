from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from models.team import Team
from optimizer.evaluator.move_evaluator import MoveEvaluator
from optimizer.optimization_history import OptimizationHistory
from optimizer.optimization_iteration import OptimizationIteration
from optimizer.optimization_pipeline import OptimizationPipeline
from optimizer.optimization_result import OptimizationResult
from optimizer.strategies.search_result import SearchResult


class LocalOptimizer:
    """
    Ejecuta las fases de un OptimizationPipeline de forma segura.

    Garantías:

        - Cada movimiento temporal es evaluado por MoveEvaluator.
        - Cada movimiento definitivo se valida después de aplicarse.
        - La colección de jugadores debe permanecer intacta.
        - Ningún equipo puede cambiar de tamaño.
        - Se conserva la mejor solución encontrada.
        - Si una fase termina en un estado peor, se restaura la mejor.
        - El resultado final nunca debe ser peor que el inicial.
    """

    SCORE_TOLERANCE = 1e-9

    def __init__(
        self,
        evaluator: MoveEvaluator,
        pipeline: OptimizationPipeline,
    ) -> None:
        if evaluator is None:
            raise ValueError(
                "evaluator cannot be None."
            )

        if pipeline is None:
            raise ValueError(
                "pipeline cannot be None."
            )

        if pipeline.is_empty:
            raise ValueError(
                "pipeline must contain at least one phase."
            )

        self._evaluator = evaluator
        self._pipeline = pipeline

    def optimize(
        self,
        teams: Sequence[Team],
    ) -> OptimizationResult:
        """
        Optimiza los equipos recibidos.

        Los objetos Team se modifican durante la ejecución, pero al
        terminar contienen siempre la mejor solución encontrada.
        """
        team_list = self._validate_teams(
            teams
        )

        original_structure = self._capture_structure(
            team_list
        )

        initial_snapshot = self._snapshot(
            team_list
        )

        initial_evaluation = self._evaluator.current(
            team_list
        )

        initial_score = float(
            initial_evaluation.score
        )

        current_score = initial_score
        best_score = initial_score
        best_snapshot = initial_snapshot

        history = OptimizationHistory()

        self._pipeline.reset()

        for phase in self._pipeline:
            if not phase.enabled:
                continue

            phase.reset()

            current_score, best_score, best_snapshot = (
                self._execute_phase(
                    phase=phase,
                    teams=team_list,
                    current_score=current_score,
                    best_score=best_score,
                    best_snapshot=best_snapshot,
                    original_structure=original_structure,
                    history=history,
                )
            )

        self._restore(
            teams=team_list,
            snapshot=best_snapshot,
        )

        self._validate_structure(
            teams=team_list,
            expected=original_structure,
            stage="final best-solution restoration",
        )

        final_evaluation = self._evaluator.current(
            team_list
        )

        final_score = float(
            final_evaluation.score
        )

        if final_score + self.SCORE_TOLERANCE < initial_score:
            self._restore(
                teams=team_list,
                snapshot=initial_snapshot,
            )

            self._validate_structure(
                teams=team_list,
                expected=original_structure,
                stage="initial-solution fallback",
            )

            final_evaluation = self._evaluator.current(
                team_list
            )

            final_score = float(
                final_evaluation.score
            )

        if final_score + self.SCORE_TOLERANCE < initial_score:
            raise RuntimeError(
                "LocalOptimizer could not guarantee a final solution "
                "at least as good as the initial solution. "
                f"Initial score: {initial_score:.6f}. "
                f"Final score: {final_score:.6f}."
            )

        return OptimizationResult(
            teams=team_list,
            objective_result=final_evaluation.objective_result,
            history=history,
        )

    def _execute_phase(
        self,
        phase,
        teams: list[Team],
        current_score: float,
        best_score: float,
        best_snapshot: tuple[tuple[Any, ...], ...],
        original_structure: tuple[tuple[int, ...], tuple[int, ...]],
        history: OptimizationHistory,
    ) -> tuple[
        float,
        float,
        tuple[tuple[Any, ...], ...],
    ]:
        """
        Ejecuta una fase completa.

        Devuelve:

            - puntuación actual;
            - mejor puntuación global;
            - fotografía de la mejor solución global.
        """
        for iteration_number in range(
            1,
            phase.max_iterations + 1,
        ):
            search_result = phase.strategy.search(
                neighborhood=phase.neighborhood,
                teams=teams,
                evaluator=self._evaluator,
                current_score=current_score,
            )

            if not search_result.has_move:
                if phase.stop_when_no_move:
                    break

                continue

            move = search_result.move

            if move is None:
                if phase.stop_when_no_move:
                    break

                continue

            before_snapshot = self._snapshot(
                teams
            )

            score_before = current_score

            try:
                move.apply(
                    teams
                )

                self._validate_structure(
                    teams=teams,
                    expected=original_structure,
                    stage=(
                        f"phase '{phase.name}', "
                        f"iteration {iteration_number}, "
                        "after applying move"
                    ),
                )

                actual_evaluation = self._evaluator.current(
                    teams
                )

                actual_score = float(
                    actual_evaluation.score
                )

            except Exception:
                self._restore(
                    teams=teams,
                    snapshot=before_snapshot,
                )

                self._validate_structure(
                    teams=teams,
                    expected=original_structure,
                    stage=(
                        f"phase '{phase.name}', "
                        f"iteration {iteration_number}, "
                        "rollback after failed move"
                    ),
                )

                raise

            applied_result = SearchResult.from_move(
                move=move,
                score_before=score_before,
                score_after=actual_score,
                evaluations=search_result.evaluations,
                elapsed=search_result.elapsed,
            )

            history.add(
                OptimizationIteration(
                    phase=phase.name,
                    iteration=iteration_number,
                    strategy=phase.strategy_name,
                    neighborhood=phase.neighborhood_name,
                    result=applied_result,
                )
            )

            current_score = actual_score

            if (
                actual_score
                > best_score + self.SCORE_TOLERANCE
            ):
                best_score = actual_score
                best_snapshot = self._snapshot(
                    teams
                )

        self._restore(
            teams=teams,
            snapshot=best_snapshot,
        )

        self._validate_structure(
            teams=teams,
            expected=original_structure,
            stage=f"phase '{phase.name}' best-solution restoration",
        )

        restored_evaluation = self._evaluator.current(
            teams
        )

        current_score = float(
            restored_evaluation.score
        )

        if (
            abs(current_score - best_score)
            > self.SCORE_TOLERANCE
        ):
            raise RuntimeError(
                f"Restored score mismatch after phase '{phase.name}'. "
                f"Expected best score {best_score:.6f}, "
                f"obtained {current_score:.6f}."
            )

        return (
            current_score,
            best_score,
            best_snapshot,
        )

    @staticmethod
    def _snapshot(
        teams: Sequence[Team],
    ) -> tuple[tuple[Any, ...], ...]:
        """
        Guarda las listas de jugadores conservando las mismas instancias.
        """
        return tuple(
            tuple(team.players)
            for team in teams
        )

    @classmethod
    def _restore(
        cls,
        teams: Sequence[Team],
        snapshot: tuple[tuple[Any, ...], ...],
    ) -> None:
        """
        Restaura exactamente el contenido y orden de cada equipo.
        """
        if len(teams) != len(snapshot):
            raise RuntimeError(
                "The number of teams changed during optimization."
            )

        for team, original_players in zip(
            teams,
            snapshot,
            strict=True,
        ):
            players = getattr(
                team,
                "players",
                None,
            )

            if players is None:
                raise AttributeError(
                    f"{cls._describe_team(team)} does not expose players."
                )

            try:
                players[:] = original_players

            except TypeError:
                try:
                    team.players = list(original_players)

                except Exception as error:
                    raise RuntimeError(
                        f"Could not restore "
                        f"{cls._describe_team(team)}."
                    ) from error

            cls._invalidate_team_statistics(
                team
            )

        cls._validate_snapshot_restoration(
            teams=teams,
            snapshot=snapshot,
        )

    @classmethod
    def _validate_snapshot_restoration(
        cls,
        teams: Sequence[Team],
        snapshot: tuple[tuple[Any, ...], ...],
    ) -> None:
        """
        Comprueba que la restauración coincide por posición e identidad.
        """
        for team, original_players in zip(
            teams,
            snapshot,
            strict=True,
        ):
            current_players = getattr(
                team,
                "players",
                None,
            )

            if current_players is None:
                raise RuntimeError(
                    f"{cls._describe_team(team)} no longer exposes players."
                )

            if len(current_players) != len(original_players):
                raise RuntimeError(
                    f"{cls._describe_team(team)} was restored with "
                    "an incorrect number of players."
                )

            for position, (
                current_player,
                original_player,
            ) in enumerate(
                zip(
                    current_players,
                    original_players,
                    strict=True
                ),
                start=1,
            ):
                if current_player is not original_player:
                    raise RuntimeError(
                        f"{cls._describe_team(team)} was not restored "
                        f"correctly at position {position}. "
                        f"Expected "
                        f"{cls._describe_player(original_player)}, "
                        f"found "
                        f"{cls._describe_player(current_player)}."
                    )

    @staticmethod
    def _capture_structure(
        teams: Sequence[Team],
    ) -> tuple[
        tuple[int, ...],
        tuple[int, ...],
    ]:
        """
        Guarda la estructura inicial:

            - tamaño de cada equipo;
            - identidad de todas las instancias de Player.
        """
        team_sizes = tuple(
            len(team.players)
            for team in teams
        )

        player_object_ids = tuple(
            sorted(
                id(player)
                for team in teams
                for player in team.players
            )
        )

        if len(player_object_ids) != len(
            set(player_object_ids)
        ):
            raise ValueError(
                "The initial team distribution contains duplicated "
                "Player instances."
            )

        return (
            team_sizes,
            player_object_ids,
        )

    @classmethod
    def _validate_structure(
        cls,
        teams: Sequence[Team],
        expected: tuple[
            tuple[int, ...],
            tuple[int, ...],
        ],
        stage: str,
    ) -> None:
        """
        Verifica que un movimiento no cambie la colección de jugadores.
        """
        expected_sizes, expected_object_ids = expected

        current_sizes = tuple(
            len(team.players)
            for team in teams
        )

        if current_sizes != expected_sizes:
            raise RuntimeError(
                f"[{stage}] Team sizes changed. "
                f"Expected {expected_sizes}, "
                f"obtained {current_sizes}."
            )

        current_object_ids = tuple(
            sorted(
                id(player)
                for team in teams
                for player in team.players
            )
        )

        if len(current_object_ids) != len(
            set(current_object_ids)
        ):
            duplicates = cls._find_duplicate_players(
                teams
            )

            raise RuntimeError(
                f"[{stage}] Duplicated Player instances detected. "
                f"{duplicates}"
            )

        if current_object_ids != expected_object_ids:
            expected_set = set(
                expected_object_ids
            )

            current_set = set(
                current_object_ids
            )

            missing_ids = sorted(
                expected_set - current_set
            )

            unexpected_ids = sorted(
                current_set - expected_set
            )

            raise RuntimeError(
                f"[{stage}] The player collection changed. "
                f"Missing object IDs: {missing_ids}. "
                f"Unexpected object IDs: {unexpected_ids}."
            )

    @classmethod
    def _find_duplicate_players(
        cls,
        teams: Sequence[Team],
    ) -> str:
        locations: dict[int, list[str]] = {}
        players_by_id: dict[int, Any] = {}

        for team_index, team in enumerate(
            teams,
            start=1,
        ):
            team_name = (
                getattr(team, "name", None)
                or f"Team {team_index}"
            )

            for player_index, player in enumerate(
                team.players,
                start=1,
            ):
                object_id = id(player)

                players_by_id[object_id] = player

                locations.setdefault(
                    object_id,
                    [],
                ).append(
                    f"{team_name}[{player_index}]"
                )

        descriptions = []

        for object_id, player_locations in locations.items():
            if len(player_locations) <= 1:
                continue

            descriptions.append(
                f"{cls._describe_player(players_by_id[object_id])} "
                f"at {', '.join(player_locations)}"
            )

        return "; ".join(descriptions)

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        team_list = list(
            teams
        )

        if not team_list:
            raise ValueError(
                "At least one team is required."
            )

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            if team is None:
                raise ValueError(
                    f"Team {index} cannot be None."
                )

            players = getattr(
                team,
                "players",
                None,
            )

            if players is None:
                raise AttributeError(
                    f"Team {index} does not expose players."
                )

        return team_list

    @staticmethod
    def _invalidate_team_statistics(
        team: Team,
    ) -> None:
        statistics = getattr(
            team,
            "statistics",
            None,
        )

        if statistics is None:
            return

        invalidate = getattr(
            statistics,
            "invalidate",
            None,
        )

        if callable(invalidate):
            invalidate()

    @staticmethod
    def _describe_player(
        player,
    ) -> str:
        nickname = getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                "Unknown",
            ),
        )

        steam_id = getattr(
            player,
            "steam_id",
            None,
        )

        return (
            f"Player("
            f"nickname={nickname!r}, "
            f"steam_id={steam_id!r}, "
            f"object_id={id(player)})"
        )

    @staticmethod
    def _describe_team(
        team: Team,
    ) -> str:
        name = getattr(
            team,
            "name",
            None,
        )

        team_id = getattr(
            team,
            "id",
            None,
        )

        if name:
            return (
                f"Team("
                f"name={name!r}, "
                f"id={team_id!r})"
            )

        return f"Team(id={team_id!r})"

    @property
    def evaluator(
        self,
    ) -> MoveEvaluator:
        return self._evaluator

    @property
    def pipeline(
        self,
    ) -> OptimizationPipeline:
        return self._pipeline

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"phases={len(self._pipeline)}, "
            f"evaluator={self._evaluator.__class__.__name__})"
        )
