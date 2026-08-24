from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from application.results.base_report_result import (
    BaseReportResult,
)
from application.results.report_mode import (
    ReportMode,
)
from scoring.scoring_model import (
    ScoringModel,
)


@dataclass(
    frozen=True,
    slots=True,
)
class PlayerReportData:
    """
    Representación de un jugador preparada para el informe HTML.

    Esta clase no recalcula Power ni actividad.

    Todos los valores relacionados con el scoring proceden de:

        ScoringModel.evaluate(player)

    Se conservan por separado:

        activity_score
            Actividad objetiva observada.

        base_activity_factor
            Factor que correspondería antes del ajuste por nivel.

        level_penalty_strength
            Intensidad aplicada a la pérdida según nivel FACEIT.

        activity_factor
            Factor efectivo utilizado finalmente.

        base_power
            Power antes de actividad.

        final_power
            Power realmente utilizado por el balanceador.
    """

    nickname: str

    team_index: int
    team_id: Any
    team_name: str

    assigned_team_number: int | None

    steam_id: str | None
    profile_url: str | None
    role: str | None
    seed: int | None

    elo: int | None
    level: int | None

    kd: float | None
    rating: float | None
    adr: float | None
    kpr: float | None
    dpr: float | None
    hs: float | None
    kast: float | None
    winrate: float | None
    clutch: float | None
    matches: int | None

    base_power: float
    final_power: float

    activity_enabled: bool
    activity_score: float

    base_activity_factor: float
    level_penalty_strength: float
    activity_factor: float

    faceit_level: int | None

    has_activity_data: bool
    activity_history_complete: bool | None

    matches_0_7_days: int | None
    matches_8_30_days: int | None
    matches_31_90_days: int | None
    total_matches_90_days: int | None
    days_since_last_match: int | None

    @property
    def power_penalty(
        self,
    ) -> float:
        return max(
            0.0,
            self.base_power - self.final_power,
        )

    @property
    def power_penalty_percentage(
        self,
    ) -> float:
        if self.base_power <= 0.0:
            return 0.0

        return (
            self.power_penalty
            / self.base_power
            * 100.0
        )

    @property
    def activity_percentage(
        self,
    ) -> float:
        """
        Factor efectivo que realmente se aplica al Power.

        Se mantiene esta propiedad por compatibilidad con las
        secciones HTML existentes.
        """
        return (
            self.activity_factor
            * 100.0
        )

    @property
    def raw_activity_percentage(
        self,
    ) -> float:
        """
        Actividad observada antes de transformarla en factor de Power.
        """
        return (
            self.activity_score
            * 100.0
        )

    @property
    def base_activity_percentage(
        self,
    ) -> float:
        return (
            self.base_activity_factor
            * 100.0
        )

    @property
    def effective_activity_percentage(
        self,
    ) -> float:
        return (
            self.activity_factor
            * 100.0
        )

    @property
    def level_adjustment(
        self,
    ) -> float:
        """
        Diferencia entre el factor final y el factor base.

        Positivo:
            el nivel FACEIT ha suavizado la penalización.

        Negativo:
            el nivel FACEIT ha endurecido la penalización.

        Cero:
            penalización neutra.
        """
        return (
            self.activity_factor
            - self.base_activity_factor
        )

    @property
    def level_adjustment_percentage(
        self,
    ) -> float:
        return (
            self.level_adjustment
            * 100.0
        )

    @property
    def level_adjustment_label(
        self,
    ) -> str:
        if abs(
            self.level_adjustment
        ) <= 1e-9:
            return "Neutro"

        if self.level_adjustment > 0.0:
            return "Penalización suavizada"

        return "Penalización endurecida"

    @property
    def is_activity_penalized(
        self,
    ) -> bool:
        return (
            self.activity_factor
            < 0.999999
        )

    @property
    def is_seeded(
        self,
    ) -> bool:
        return self.seed is not None

    @property
    def is_preassigned(
        self,
    ) -> bool:
        return (
            self.assigned_team_number
            is not None
        )


@dataclass(
    frozen=True,
    slots=True,
)
class TeamReportData:
    """
    Datos agregados de un equipo para el informe.
    """

    index: int

    id: Any
    name: str

    players: tuple[
        PlayerReportData,
        ...,
    ]

    average_base_power: float
    average_final_power: float

    average_activity_score: float
    average_base_activity_factor: float
    average_activity_factor: float

    average_elo: float | None
    average_kd: float | None
    average_adr: float | None
    average_rating: float | None
    average_winrate: float | None

    @property
    def player_count(
        self,
    ) -> int:
        return len(
            self.players
        )

    @property
    def seeded_players(
        self,
    ) -> tuple[PlayerReportData, ...]:
        return tuple(
            player
            for player in self.players
            if player.seed is not None
        )

    @property
    def seed_count(
        self,
    ) -> int:
        return len(
            self.seeded_players
        )

    @property
    def penalized_players(
        self,
    ) -> tuple[PlayerReportData, ...]:
        return tuple(
            player
            for player in self.players
            if player.is_activity_penalized
        )

    @property
    def penalized_player_count(
        self,
    ) -> int:
        return len(
            self.penalized_players
        )

    @property
    def activity_percentage(
        self,
    ) -> float:
        """
        Factor efectivo medio del equipo, en porcentaje.

        Se conserva este alias por compatibilidad con TeamsSection.
        """
        return (
            self.average_activity_factor
            * 100.0
        )

    @property
    def raw_activity_percentage(
        self,
    ) -> float:
        return (
            self.average_activity_score
            * 100.0
        )

    @property
    def base_activity_percentage(
        self,
    ) -> float:
        return (
            self.average_base_activity_factor
            * 100.0
        )

    @property
    def power_penalty(
        self,
    ) -> float:
        return max(
            0.0,
            (
                self.average_base_power
                - self.average_final_power
            ),
        )

    @property
    def level_adjustment(
        self,
    ) -> float:
        """
        Efecto medio del ajuste por nivel FACEIT sobre el factor.
        """
        return (
            self.average_activity_factor
            - self.average_base_activity_factor
        )

    @property
    def level_adjustment_percentage(
        self,
    ) -> float:
        return (
            self.level_adjustment
            * 100.0
        )


class ReportContext:
    """
    Contexto de lectura utilizado por HtmlExporterV2.

    El objetivo de esta clase es desacoplar por completo las secciones
    HTML de:

        - OptimizationResult.
        - EvaluationResult.
        - Team.
        - Player.
        - ScoringModel.

    Durante su construcción se evalúa cada jugador una sola vez y se
    almacenan todos los datos necesarios para el informe.

    Esto garantiza que:

        RankingSection
        ActivitySection
        TeamsSection
        SummarySection

    muestran exactamente los mismos valores.
    """

    def __init__(
        self,
        result: BaseReportResult,
        scoring_model: ScoringModel | None = None,
        title: str | None = None,
    ) -> None:
        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not isinstance(
            result,
            BaseReportResult,
        ):
            raise TypeError(
                "result must be a BaseReportResult instance."
            )

        if (
            scoring_model is not None
            and not isinstance(
                scoring_model,
                ScoringModel,
            )
        ):
            raise TypeError(
                "scoring_model must be a ScoringModel or None."
            )

        self._result = result
        self._scoring_model = (
            scoring_model
        )

        self._title = self._resolve_title(
            result=result,
            title=title,
        )

        self._teams = self._build_teams(
            result=result,
            scoring_model=scoring_model,
        )

        self._players = tuple(
            player
            for team in self._teams
            for player in team.players
        )

        self._ranking = tuple(
            sorted(
                self._players,
                key=self._ranking_key,
                reverse=True,
            )
        )

    # ========================================================
    # Construcción
    # ========================================================

    @classmethod
    def _build_teams(
        cls,
        result: BaseReportResult,
        scoring_model: ScoringModel | None,
    ) -> tuple[TeamReportData, ...]:
        report_teams: list[
            TeamReportData
        ] = []

        for team_index, team in enumerate(
            result.teams,
            start=1,
        ):
            team_id = getattr(
                team,
                "id",
                team_index,
            )

            team_name = cls._team_name(
                team=team,
                fallback_index=team_index,
            )

            report_players = tuple(
                cls._build_player(
                    player=player,
                    team_index=team_index,
                    team_id=team_id,
                    team_name=team_name,
                    scoring_model=scoring_model,
                )
                for player in getattr(
                    team,
                    "players",
                    (),
                )
            )

            report_teams.append(
                TeamReportData(
                    index=team_index,

                    id=team_id,

                    name=team_name,

                    players=report_players,

                    average_base_power=(
                        cls._average(
                            player.base_power
                            for player
                            in report_players
                        )
                    ),

                    average_final_power=(
                        cls._average(
                            player.final_power
                            for player
                            in report_players
                        )
                    ),

                    average_activity_score=(
                        cls._average(
                            player.activity_score
                            for player
                            in report_players
                        )
                    ),

                    average_base_activity_factor=(
                        cls._average(
                            player.base_activity_factor
                            for player
                            in report_players
                        )
                    ),

                    average_activity_factor=(
                        cls._average(
                            player.activity_factor
                            for player
                            in report_players
                        )
                    ),

                    average_elo=(
                        cls._average_optional(
                            player.elo
                            for player
                            in report_players
                        )
                    ),

                    average_kd=(
                        cls._average_optional(
                            player.kd
                            for player
                            in report_players
                        )
                    ),

                    average_adr=(
                        cls._average_optional(
                            player.adr
                            for player
                            in report_players
                        )
                    ),

                    average_rating=(
                        cls._average_optional(
                            player.rating
                            for player
                            in report_players
                        )
                    ),

                    average_winrate=(
                        cls._average_optional(
                            player.winrate
                            for player
                            in report_players
                        )
                    ),
                )
            )

        return tuple(
            report_teams
        )

    @classmethod
    def _build_player(
        cls,
        player,
        team_index: int,
        team_id: Any,
        team_name: str,
        scoring_model: ScoringModel | None,
    ) -> PlayerReportData:
        evaluation = (
            cls._evaluate_player(
                player=player,
                scoring_model=scoring_model,
            )
        )

        activity = evaluation.get(
            "activity"
        )

        if not isinstance(
            activity,
            dict,
        ):
            activity = {}

        base_power = cls._safe_float(
            evaluation.get(
                "base_power"
            ),
            default=0.0,
        )

        final_power = cls._safe_float(
            evaluation.get(
                "power",
                evaluation.get(
                    "adjusted_power"
                ),
            ),
            default=base_power,
        )

        activity_score = cls._safe_factor(
            evaluation.get(
                "activity_score",
                activity.get(
                    "activity_score"
                ),
            ),
            default=1.0,
        )

        base_activity_factor = (
            cls._safe_factor(
                evaluation.get(
                    "base_activity_factor",
                    activity.get(
                        "base_activity_factor"
                    ),
                ),
                default=1.0,
            )
        )

        level_penalty_strength = (
            cls._safe_float(
                evaluation.get(
                    "level_penalty_strength",
                    activity.get(
                        "level_penalty_strength"
                    ),
                ),
                default=1.0,
            )
        )

        if (
            level_penalty_strength
            < 0.0
        ):
            level_penalty_strength = 1.0

        activity_factor = cls._safe_factor(
            evaluation.get(
                "activity_factor",
                activity.get(
                    "activity_factor"
                ),
            ),
            default=1.0,
        )

        level = cls._optional_integer(
            cls._first_not_none(
                evaluation.get(
                    "faceit_level"
                ),
                activity.get(
                    "faceit_level"
                ),
                getattr(
                    player,
                    "level",
                    None,
                ),
                getattr(
                    player,
                    "faceit_level",
                    None,
                ),
            )
        )

        assigned_team_number = (
            cls._optional_integer(
                cls._first_not_none(
                    getattr(
                        player,
                        "team_number",
                        None,
                    ),
                    getattr(
                        player,
                        "assigned_team_number",
                        None,
                    ),
                )
            )
        )

        role = cls._role_value(
            getattr(
                player,
                "role",
                None,
            )
        )

        activity_object = getattr(
            player,
            "activity",
            None,
        )

        has_activity_data = bool(
            activity.get(
                "has_activity_data",
                activity_object
                is not None,
            )
        )

        return PlayerReportData(
            nickname=cls._player_name(
                player
            ),

            team_index=team_index,
            team_id=team_id,
            team_name=team_name,

            assigned_team_number=(
                assigned_team_number
            ),

            steam_id=cls._optional_text(
                getattr(
                    player,
                    "steam_id",
                    None,
                )
            ),

            profile_url=cls._optional_text(
                cls._first_not_none(
                    getattr(
                        player,
                        "profile_url",
                        None,
                    ),
                    getattr(
                        player,
                        "faceit_url",
                        None,
                    ),
                )
            ),

            role=role,

            seed=cls._optional_integer(
                getattr(
                    player,
                    "seed",
                    None,
                )
            ),

            elo=cls._optional_integer(
                cls._first_not_none(
                    getattr(
                        player,
                        "elo",
                        None,
                    ),
                    getattr(
                        player,
                        "faceit_elo",
                        None,
                    ),
                )
            ),

            level=level,

            kd=cls._optional_float(
                getattr(
                    player,
                    "kd",
                    None,
                )
            ),

            rating=cls._optional_float(
                getattr(
                    player,
                    "rating",
                    None,
                )
            ),

            adr=cls._optional_float(
                getattr(
                    player,
                    "adr",
                    None,
                )
            ),

            kpr=cls._optional_float(
                getattr(
                    player,
                    "kpr",
                    None,
                )
            ),

            dpr=cls._optional_float(
                getattr(
                    player,
                    "dpr",
                    None,
                )
            ),

            hs=cls._optional_float(
                getattr(
                    player,
                    "hs",
                    None,
                )
            ),

            kast=cls._optional_float(
                getattr(
                    player,
                    "kast",
                    None,
                )
            ),

            winrate=cls._optional_float(
                getattr(
                    player,
                    "winrate",
                    None,
                )
            ),

            clutch=cls._optional_float(
                getattr(
                    player,
                    "clutch",
                    None,
                )
            ),

            matches=cls._optional_integer(
                getattr(
                    player,
                    "matches",
                    None,
                )
            ),

            base_power=base_power,
            final_power=final_power,

            activity_enabled=bool(
                evaluation.get(
                    "activity_enabled",
                    activity.get(
                        "enabled",
                        False,
                    ),
                )
            ),

            activity_score=activity_score,

            base_activity_factor=(
                base_activity_factor
            ),

            level_penalty_strength=(
                level_penalty_strength
            ),

            activity_factor=(
                activity_factor
            ),

            faceit_level=level,

            has_activity_data=(
                has_activity_data
            ),

            activity_history_complete=(
                cls._optional_boolean(
                    cls._first_not_none(
                        activity.get(
                            "history_complete"
                        ),
                        getattr(
                            activity_object,
                            "history_complete",
                            None,
                        ),
                        getattr(
                            player,
                            "activity_history_complete",
                            None,
                        ),
                    )
                )
            ),

            matches_0_7_days=(
                cls._optional_integer(
                    cls._first_not_none(
                        activity.get(
                            "matches_0_7_days"
                        ),
                        getattr(
                            activity_object,
                            "matches_0_7_days",
                            None,
                        ),
                        getattr(
                            player,
                            "matches_0_7_days",
                            None,
                        ),
                    )
                )
            ),

            matches_8_30_days=(
                cls._optional_integer(
                    cls._first_not_none(
                        activity.get(
                            "matches_8_30_days"
                        ),
                        getattr(
                            activity_object,
                            "matches_8_30_days",
                            None,
                        ),
                        getattr(
                            player,
                            "matches_8_30_days",
                            None,
                        ),
                    )
                )
            ),

            matches_31_90_days=(
                cls._optional_integer(
                    cls._first_not_none(
                        activity.get(
                            "matches_31_90_days"
                        ),
                        getattr(
                            activity_object,
                            "matches_31_90_days",
                            None,
                        ),
                        getattr(
                            player,
                            "matches_31_90_days",
                            None,
                        ),
                    )
                )
            ),

            total_matches_90_days=(
                cls._optional_integer(
                    cls._first_not_none(
                        activity.get(
                            "total_matches_90_days"
                        ),
                        getattr(
                            activity_object,
                            "total_matches_90_days",
                            None,
                        ),
                        getattr(
                            player,
                            "total_matches_90_days",
                            None,
                        ),
                    )
                )
            ),

            days_since_last_match=(
                cls._optional_integer(
                    cls._first_not_none(
                        activity.get(
                            "days_since_last_match"
                        ),
                        getattr(
                            activity_object,
                            "days_since_last_match",
                            None,
                        ),
                        getattr(
                            player,
                            "days_since_last_match",
                            None,
                        ),
                    )
                )
            ),
        )

    @staticmethod
    def _evaluate_player(
        player,
        scoring_model: ScoringModel | None,
    ) -> dict[str, Any]:
        """
        Evalúa una única vez el jugador.

        Si el informe se genera sin ScoringModel se utiliza un fallback
        neutro, evitando inventar una penalización por actividad.
        """
        if scoring_model is None:
            return {
                "base_power": 0.0,
                "power": 0.0,
                "adjusted_power": 0.0,

                "activity_score": 1.0,
                "base_activity_factor": 1.0,
                "level_penalty_strength": 1.0,
                "activity_factor": 1.0,
                "activity_enabled": False,

                "activity": {
                    "enabled": False,
                    "activity_score": 1.0,
                    "base_activity_factor": 1.0,
                    "level_penalty_strength": 1.0,
                    "activity_factor": 1.0,
                },
            }

        evaluation = scoring_model.evaluate(
            player
        )

        if not isinstance(
            evaluation,
            dict,
        ):
            raise TypeError(
                "ScoringModel.evaluate() must return a dictionary."
            )

        return evaluation

    # ========================================================
    # Resultado
    # ========================================================

    @property
    def result(
        self,
    ) -> BaseReportResult:
        return self._result

    @property
    def scoring_model(
        self,
    ) -> ScoringModel | None:
        return self._scoring_model

    @property
    def title(
        self,
    ) -> str:
        return self._title

    # ========================================================
    # Modalidad
    # ========================================================

    @property
    def mode(
        self,
    ) -> ReportMode:
        return self._result.mode

    @property
    def mode_value(
        self,
    ) -> str:
        value = getattr(
            self.mode,
            "value",
            self.mode,
        )

        return str(
            value
        )

    @property
    def mode_label(
        self,
    ) -> str:
        value = getattr(
            self.mode,
            "label",
            None,
        )

        if value:
            return str(
                value
            )

        if self.evaluation_only:
            return (
                "Evaluación de equipos predeterminados"
            )

        return "Optimización automática"

    @property
    def mode_short_label(
        self,
    ) -> str:
        value = getattr(
            self.mode,
            "short_label",
            None,
        )

        if value:
            return str(
                value
            )

        return (
            "Preasignado"
            if self.evaluation_only
            else "Optimizado"
        )

    @property
    def optimized(
        self,
    ) -> bool:
        return bool(
            getattr(
                self._result,
                "optimized",
                not self.evaluation_only,
            )
        )

    @property
    def evaluation_only(
        self,
    ) -> bool:
        explicit = getattr(
            self._result,
            "evaluation_only",
            None,
        )

        if explicit is not None:
            return bool(
                explicit
            )

        return (
            self.mode
            is ReportMode.PREASSIGNED
        )

    @property
    def result_description(
        self,
    ) -> str:
        if self.evaluation_only:
            return (
                "Evaluación estadística de una composición "
                "predeterminada de equipos."
            )

        if self.is_global_optimization:
            if self.global_optimality_proven:
                return (
                    "Distribución optimizada mediante búsqueda global "
                    "Branch & Bound con optimalidad demostrada."
                )

            return (
                "Distribución optimizada mediante búsqueda global "
                "Branch & Bound."
            )

        return (
            "Distribución generada y optimizada automáticamente "
            "por el motor de balanceo."
        )

    # ========================================================
    # Metadata de optimización
    # ========================================================

    @property
    def metadata(
        self,
    ) -> dict[str, Any]:
        value = getattr(
            self._result,
            "metadata",
            {},
        )

        if not isinstance(
            value,
            dict,
        ):
            try:
                value = dict(
                    value
                )
            except (
                TypeError,
                ValueError,
            ):
                return {}

        return dict(
            value
        )

    @property
    def optimization_mode(
        self,
    ) -> str | None:
        value = self.metadata.get(
            "optimization_mode"
        )

        if value is None:
            return None

        normalized = str(
            value
        ).strip().casefold()

        return (
            normalized
            or None
        )

    @property
    def optimization_mode_label(
        self,
    ) -> str | None:
        value = self.metadata.get(
            "optimization_mode_label"
        )

        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return (
            normalized
            or None
        )

    @property
    def optimization_deterministic(
        self,
    ) -> bool:
        return bool(
            self.metadata.get(
                "optimization_deterministic",
                False,
            )
        )

    @property
    def is_global_optimization(
        self,
    ) -> bool:
        return (
            self.optimization_mode
            == "global"
        )

    @property
    def global_optimization(
        self,
    ) -> dict[str, Any]:
        value = self.metadata.get(
            "global_optimization",
            {},
        )

        if not isinstance(
            value,
            dict,
        ):
            return {}

        return dict(
            value
        )

    @property
    def global_initial_incumbent_score(
        self,
    ) -> float:
        return self._safe_float(
            self.global_optimization.get(
                "initial_incumbent_score",
                self.initial_score,
            ),
            default=self.initial_score,
        )

    @property
    def global_final_score(
        self,
    ) -> float:
        return self._safe_float(
            self.global_optimization.get(
                "final_score",
                self.final_score,
            ),
            default=self.final_score,
        )

    @property
    def global_improvement(
        self,
    ) -> float:
        return self._safe_float(
            self.global_optimization.get(
                "improvement",
                (
                    self.global_final_score
                    - self.global_initial_incumbent_score
                ),
            ),
            default=(
                self.global_final_score
                - self.global_initial_incumbent_score
            ),
        )

    @property
    def global_nodes_visited(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                self.global_optimization.get(
                    "nodes_visited",
                    0,
                )
            )
            or 0,
        )

    @property
    def global_complete_solutions_evaluated(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                self.global_optimization.get(
                    "complete_solutions_evaluated",
                    0,
                )
            )
            or 0,
        )

    @property
    def global_pruned_nodes(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                self.global_optimization.get(
                    "pruned_nodes",
                    0,
                )
            )
            or 0,
        )

    @property
    def global_capacity_prunes(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                self.global_optimization.get(
                    "capacity_prunes",
                    0,
                )
            )
            or 0,
        )

    @property
    def global_seed_prunes(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                self.global_optimization.get(
                    "seed_prunes",
                    0,
                )
            )
            or 0,
        )

    @property
    def global_bound_prunes(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                self.global_optimization.get(
                    "bound_prunes",
                    0,
                )
            )
            or 0,
        )

    @property
    def global_elapsed_seconds(
        self,
    ) -> float:
        return max(
            0.0,
            self._safe_float(
                self.global_optimization.get(
                    "elapsed_seconds",
                    0.0,
                ),
                default=0.0,
            ),
        )

    @property
    def global_optimality_proven(
        self,
    ) -> bool:
        return bool(
            self.global_optimization.get(
                "optimality_proven",
                False,
            )
        )

    @property
    def global_stopped_by_limit(
        self,
    ) -> bool:
        return bool(
            self.global_optimization.get(
                "stopped_by_limit",
                False,
            )
        )

    @property
    def global_stop_reason(
        self,
    ) -> str:
        value = self.global_optimization.get(
            "stop_reason",
            "UNKNOWN",
        )

        normalized = str(
            value
        ).strip()

        return (
            normalized
            or "UNKNOWN"
        )

    @property
    def global_search_exhausted(
        self,
    ) -> bool:
        return (
            self.global_stop_reason
            == "SEARCH_EXHAUSTED"
        )

    # ========================================================
    # Equipos y jugadores
    # ========================================================

    @property
    def teams(
        self,
    ) -> tuple[TeamReportData, ...]:
        return self._teams

    @property
    def players(
        self,
    ) -> tuple[PlayerReportData, ...]:
        return self._players

    @property
    def ranking(
        self,
    ) -> tuple[PlayerReportData, ...]:
        return self._ranking

    @property
    def team_count(
        self,
    ) -> int:
        return len(
            self._teams
        )

    @property
    def player_count(
        self,
    ) -> int:
        return len(
            self._players
        )

    @property
    def seeded_players(
        self,
    ) -> tuple[PlayerReportData, ...]:
        return tuple(
            player
            for player in self._players
            if player.seed is not None
        )

    @property
    def preassigned_players(
        self,
    ) -> tuple[PlayerReportData, ...]:
        return tuple(
            player
            for player in self._players
            if (
                player.assigned_team_number
                is not None
            )
        )

    # ========================================================
    # Puntuación del resultado
    # ========================================================

    @property
    def score(
        self,
    ) -> float:
        return self.final_score

    @property
    def initial_score(
        self,
    ) -> float:
        return self._safe_float(
            getattr(
                self._result,
                "initial_score",
                self.final_score,
            ),
            default=self.final_score,
        )

    @property
    def final_score(
        self,
    ) -> float:
        return self._safe_float(
            getattr(
                self._result,
                "final_score",
                getattr(
                    self._result,
                    "score",
                    0.0,
                ),
            ),
            default=0.0,
        )

    @property
    def improvement(
        self,
    ) -> float:
        return self._safe_float(
            getattr(
                self._result,
                "improvement",
                (
                    self.final_score
                    - self.initial_score
                ),
            ),
            default=0.0,
        )

    @property
    def penalty(
        self,
    ) -> float:
        return self._safe_float(
            getattr(
                self._result,
                "penalty",
                0.0,
            ),
            default=0.0,
        )

    @property
    def is_valid(
        self,
    ) -> bool:
        return bool(
            getattr(
                self._result,
                "is_valid",
                self.penalty <= 0.0,
            )
        )

    @property
    def balance_label(
        self,
    ) -> str:
        value = getattr(
            self._result,
            "balance_label",
            None,
        )

        if value:
            return str(
                value
            )

        if not self.is_valid:
            return "Composición inválida"

        if self.final_score >= 95.0:
            return "Muy equilibrados"

        if self.final_score >= 85.0:
            return "Bien equilibrados"

        if self.final_score >= 70.0:
            return "Aceptablemente equilibrados"

        if self.final_score >= 50.0:
            return "Desequilibrados"

        return "Muy desequilibrados"

    @property
    def balance_level(
        self,
    ) -> str:
        value = getattr(
            self._result,
            "balance_level",
            None,
        )

        if value:
            return str(
                value
            )

        if not self.is_valid:
            return "invalid"

        if self.final_score >= 95.0:
            return "excellent"

        if self.final_score >= 85.0:
            return "good"

        if self.final_score >= 70.0:
            return "acceptable"

        if self.final_score >= 50.0:
            return "poor"

        return "critical"

    @property
    def iterations(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                getattr(
                    self._result,
                    "iterations",
                    0,
                )
            )
            or 0,
        )

    @property
    def total_evaluations(
        self,
    ) -> int:
        return max(
            0,
            self._optional_integer(
                getattr(
                    self._result,
                    "total_evaluations",
                    0,
                )
            )
            or 0,
        )

    @property
    def elapsed_ms(
        self,
    ) -> float:
        return max(
            0.0,
            self._safe_float(
                getattr(
                    self._result,
                    "elapsed_ms",
                    0.0,
                ),
                default=0.0,
            ),
        )

    @property
    def restrictions(
        self,
    ) -> dict:
        value = getattr(
            self._result,
            "restrictions",
            {},
        )

        if isinstance(
            value,
            dict,
        ):
            return dict(
                value
            )

        try:
            return {
                restriction.name: restriction
                for restriction in value
            }

        except TypeError:
            return {}

    # ========================================================
    # Agregados de Power
    # ========================================================

    @property
    def average_base_power(
        self,
    ) -> float:
        return self._average(
            player.base_power
            for player in self._players
        )

    @property
    def average_final_power(
        self,
    ) -> float:
        return self._average(
            player.final_power
            for player in self._players
        )

    @property
    def average_activity_score(
        self,
    ) -> float:
        return self._average(
            player.activity_score
            for player in self._players
        )

    @property
    def average_base_activity_factor(
        self,
    ) -> float:
        return self._average(
            player.base_activity_factor
            for player in self._players
        )

    @property
    def average_activity_factor(
        self,
    ) -> float:
        return self._average(
            player.activity_factor
            for player in self._players
        )

    @property
    def average_level_penalty_strength(
        self,
    ) -> float:
        return self._average(
            player.level_penalty_strength
            for player in self._players
        )

    @property
    def average_level_adjustment(
        self,
    ) -> float:
        return (
            self.average_activity_factor
            - self.average_base_activity_factor
        )

    @property
    def strongest_team(
        self,
    ) -> TeamReportData | None:
        if not self._teams:
            return None

        return max(
            self._teams,
            key=lambda team: (
                team.average_final_power,
                -team.index,
            ),
        )

    @property
    def weakest_team(
        self,
    ) -> TeamReportData | None:
        if not self._teams:
            return None

        return min(
            self._teams,
            key=lambda team: (
                team.average_final_power,
                team.index,
            ),
        )

    @property
    def power_spread(
        self,
    ) -> float:
        return self._team_spread(
            team.average_final_power
            for team in self._teams
        ) or 0.0

    @property
    def base_power_spread(
        self,
    ) -> float:
        return self._team_spread(
            team.average_base_power
            for team in self._teams
        ) or 0.0

    @property
    def elo_spread(
        self,
    ) -> float | None:
        return self._team_spread(
            team.average_elo
            for team in self._teams
        )

    @property
    def kd_spread(
        self,
    ) -> float | None:
        return self._team_spread(
            team.average_kd
            for team in self._teams
        )

    @property
    def activity_factor_spread(
        self,
    ) -> float:
        return self._team_spread(
            team.average_activity_factor
            for team in self._teams
        ) or 0.0

    # ========================================================
    # Helpers
    # ========================================================

    @staticmethod
    def _ranking_key(
        player: PlayerReportData,
    ) -> tuple[
        float,
        float,
        float,
        str,
    ]:
        return (
            player.final_power,
            player.base_power,
            float(
                player.elo
                or 0
            ),
            player.nickname.casefold(),
        )

    @staticmethod
    def _team_name(
        team,
        fallback_index: int,
    ) -> str:
        name = getattr(
            team,
            "name",
            None,
        )

        if name:
            normalized = str(
                name
            ).strip()

            if normalized:
                return normalized

        team_id = getattr(
            team,
            "id",
            fallback_index,
        )

        return (
            f"Equipo {team_id}"
        )

    @staticmethod
    def _player_name(
        player,
    ) -> str:
        value = getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                None,
            ),
        )

        if value is None:
            return "Unknown player"

        normalized = str(
            value
        ).strip()

        return (
            normalized
            or "Unknown player"
        )

    @staticmethod
    def _role_value(
        role,
    ) -> str | None:
        if role is None:
            return None

        value = getattr(
            role,
            "value",
            role,
        )

        normalized = str(
            value
        ).strip()

        return (
            normalized
            or None
        )

    @staticmethod
    def _resolve_title(
        result: BaseReportResult,
        title: str | None,
    ) -> str:
        candidate = (
            title
            if title is not None
            else getattr(
                result,
                "title",
                None,
            )
        )

        if candidate is None:
            return (
                "LAN CS2 — Análisis de equipos"
            )

        normalized = str(
            candidate
        ).strip()

        return (
            normalized
            or "LAN CS2 — Análisis de equipos"
        )

    @staticmethod
    def _first_not_none(
        *values,
    ):
        for value in values:
            if value is not None:
                return value

        return None

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        if (
            value is None
            or isinstance(
                value,
                bool,
            )
        ):
            return float(
                default
            )

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return float(
                default
            )

    @classmethod
    def _safe_factor(
        cls,
        value: Any,
        default: float = 1.0,
    ) -> float:
        numeric = cls._safe_float(
            value,
            default=default,
        )

        return max(
            0.0,
            min(
                1.0,
                numeric,
            ),
        )

    @staticmethod
    def _optional_float(
        value: Any,
    ) -> float | None:
        if (
            value is None
            or isinstance(
                value,
                bool,
            )
        ):
            return None

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    @staticmethod
    def _optional_integer(
        value: Any,
    ) -> int | None:
        if (
            value is None
            or isinstance(
                value,
                bool,
            )
        ):
            return None

        try:
            numeric = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if not numeric.is_integer():
            return None

        return int(
            numeric
        )

    @staticmethod
    def _optional_boolean(
        value: Any,
    ) -> bool | None:
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return value

        normalized = (
            str(value)
            .strip()
            .casefold()
        )

        if normalized in {
            "1",
            "true",
            "yes",
            "si",
            "sí",
        }:
            return True

        if normalized in {
            "0",
            "false",
            "no",
        }:
            return False

        return None

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return (
            normalized
            or None
        )

    @staticmethod
    def _average(
        values,
    ) -> float:
        numeric_values = [
            float(value)
            for value in values
            if (
                value is not None
                and not isinstance(
                    value,
                    bool,
                )
            )
        ]

        if not numeric_values:
            return 0.0

        return float(
            mean(
                numeric_values
            )
        )

    @staticmethod
    def _average_optional(
        values,
    ) -> float | None:
        numeric_values: list[
            float
        ] = []

        for value in values:
            if (
                value is None
                or isinstance(
                    value,
                    bool,
                )
            ):
                continue

            try:
                numeric_values.append(
                    float(value)
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        if not numeric_values:
            return None

        return float(
            mean(
                numeric_values
            )
        )

    @staticmethod
    def _team_spread(
        values,
    ) -> float | None:
        numeric_values: list[
            float
        ] = []

        for value in values:
            if (
                value is None
                or isinstance(
                    value,
                    bool,
                )
            ):
                continue

            try:
                numeric_values.append(
                    float(value)
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

        if not numeric_values:
            return None

        return (
            max(numeric_values)
            - min(numeric_values)
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"mode={self.mode_value!r}, "
            f"teams={self.team_count}, "
            f"players={self.player_count}, "
            f"score={self.final_score:.2f}, "
            f"average_power="
            f"{self.average_final_power:.2f})"
        )
