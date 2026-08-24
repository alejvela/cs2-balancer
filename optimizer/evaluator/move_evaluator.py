from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from evaluation.evaluation_result import EvaluationResult
from models.team import Team
from objective.objective_engine import ObjectiveEngine
from optimizer.moves.move import Move


class MoveEvaluator:
    """
    Evalúa movimientos de forma transaccional.

    Flujo:

        1. Guarda una fotografía exacta de las listas de jugadores.
        2. Aplica el movimiento.
        3. Evalúa la nueva distribución.
        4. Intenta ejecutar undo().
        5. Restaura siempre la fotografía original.

    La restauración final no depende de que undo() esté bien
    implementado. Por tanto, una evaluación nunca debe modificar
    permanentemente los equipos.
    """

    def __init__(
        self,
        objective: ObjectiveEngine,
    ) -> None:
        if objective is None:
            raise ValueError(
                "objective cannot be None."
            )

        self._objective = objective

    def evaluate(
        self,
        move: Move,
        teams: Sequence[Team],
    ) -> EvaluationResult:
        """
        Evalúa temporalmente un movimiento.

        Al terminar, los equipos deben contener exactamente las mismas
        instancias, en el mismo orden, que antes de la evaluación.
        """
        if move is None:
            raise ValueError(
                "move cannot be None."
            )

        team_list = self._validate_teams(
            teams
        )

        snapshot = self._snapshot(
            team_list
        )

        applied = False
        evaluation_error: Exception | None = None
        undo_error: Exception | None = None

        try:
            move.apply(
                team_list
            )

            applied = True

            objective_result = self._objective.evaluate(
                team_list
            )

            return EvaluationResult(
                move=move,
                objective_result=objective_result,
            )

        except Exception as error:
            evaluation_error = error
            raise

        finally:
            if applied:
                try:
                    move.undo(
                        team_list
                    )

                except Exception as error:
                    undo_error = error

            restoration_error = None

            try:
                self._restore(
                    teams=team_list,
                    snapshot=snapshot,
                )

            except Exception as error:
                restoration_error = error

            if evaluation_error is None:
                if restoration_error is not None:
                    raise RuntimeError(
                        "MoveEvaluator could not restore the original "
                        "team state after evaluating the movement."
                    ) from restoration_error

                if undo_error is not None:
                    raise RuntimeError(
                        "The movement evaluation succeeded, but undo() "
                        "failed. The original team state was restored "
                        "from the evaluator snapshot."
                    ) from undo_error

    def current(
        self,
        teams: Sequence[Team],
    ) -> EvaluationResult:
        """
        Evalúa el estado actual sin aplicar ningún movimiento.
        """
        team_list = self._validate_teams(
            teams
        )

        objective_result = self._objective.evaluate(
            team_list
        )

        return EvaluationResult(
            move=None,
            objective_result=objective_result,
        )

    @staticmethod
    def _snapshot(
        teams: Sequence[Team],
    ) -> tuple[tuple[Any, ...], ...]:
        """
        Guarda las listas de jugadores por referencia e identidad.

        No realiza deepcopy de Player, porque queremos conservar las
        mismas instancias.
        """
        return tuple(
            tuple(
                getattr(team, "players", ())
            )
            for team in teams
        )

    @classmethod
    def _restore(
        cls,
        teams: Sequence[Team],
        snapshot: tuple[tuple[Any, ...], ...],
    ) -> None:
        """
        Restaura exactamente las listas y su orden original.
        """
        if len(teams) != len(snapshot):
            raise RuntimeError(
                "The number of teams changed during move evaluation."
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
                replacement = list(
                    original_players
                )

                try:
                    team.players = replacement

                except Exception as error:
                    raise RuntimeError(
                        f"Could not restore players for "
                        f"{cls._describe_team(team)}."
                    ) from error

            cls._invalidate_team_statistics(
                team
            )

        cls._validate_restoration(
            teams=teams,
            snapshot=snapshot,
        )

    @classmethod
    def _validate_restoration(
        cls,
        teams: Sequence[Team],
        snapshot: tuple[tuple[Any, ...], ...],
    ) -> None:
        """
        Verifica por identidad y posición que la restauración sea exacta.
        """
        for team_index, (
            team,
            original_players,
        ) in enumerate(
            zip(teams, snapshot, strict=True),
            start=1,
        ):
            current_players = getattr(
                team,
                "players",
                None,
            )

            if current_players is None:
                raise RuntimeError(
                    f"Team {team_index} no longer exposes players."
                )

            if len(current_players) != len(original_players):
                raise RuntimeError(
                    f"{cls._describe_team(team)} was restored with an "
                    "incorrect number of players."
                )

            for player_index, (
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
                        f"correctly at position {player_index}. "
                        f"Expected "
                        f"{cls._describe_player(original_player)}, "
                        f"found "
                        f"{cls._describe_player(current_player)}."
                    )

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
        if player is None:
            return "None"

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
    def objective(
        self,
    ) -> ObjectiveEngine:
        return self._objective

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"objective={self._objective.__class__.__name__})"
        )
