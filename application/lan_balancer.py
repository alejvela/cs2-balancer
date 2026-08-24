from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from application.results.base_report_result import (
    BaseReportResult,
)
from application.results.optimization_result import (
    OptimizationResult,
)
from application.results.report_mode import (
    ReportMode,
)
from evaluation.preassigned_team_evaluator import (
    PreassignedTeamEvaluator,
)
from generators.preassigned_team_generator import (
    PreassignedTeamGenerator,
)
from generators.snake_draft_generator import (
    SnakeDraftGenerator,
)
from importers.csstats_importer import (
    CssStatsImporter,
)
from models.player import Player
from optimizer.local_optimizer import (
    LocalOptimizer,
)
from optimizer.modes.optimization_mode import (
    OptimizationMode,
)
from optimizer.stable.stable_optimizer import (
    StableOptimizationRun,
    StableOptimizer,
)


class LanBalancer:
    """
    Fachada principal de la aplicación.

    Coordina los dos flujos soportados:

    ============================================================
    MODO PREASSIGNED
    ============================================================

        Player[]
            ↓
        PreassignedTeamGenerator
            ↓
        equipos exactamente como indica CSV.Team
            ↓
        PreassignedTeamEvaluator
            ↓
        EvaluationResult

    En este modo NO existe optimización.

    ============================================================
    MODO OPTIMIZED
    ============================================================

        Player[]
            ↓
        SnakeDraftGenerator
            ↓
        distribución inicial
            ↓
        FAST o STABLE
            ↓
        OptimizationResult

    FAST:

        Snake Draft
            ↓
        LocalOptimizer
            ↓
        resultado rápido

    STABLE:

        Snake Draft
            ↓
        StableOptimizer
            ↓
        múltiples búsquedas deterministas
            ↓
        mejor solución estable encontrada

    La selección entre FAST y STABLE es independiente de ReportMode.

    ReportMode indica:

        PREASSIGNED
        OPTIMIZED

    OptimizationMode indica únicamente cómo se ejecuta OPTIMIZED:

        FAST
        STABLE
        GLOBAL
    """

    def __init__(
        self,
        importer: CssStatsImporter,
        generator: SnakeDraftGenerator,
        optimizer: LocalOptimizer,
        preassigned_generator: (
            PreassignedTeamGenerator
            | None
        ) = None,
        preassigned_evaluator: (
            PreassignedTeamEvaluator
            | None
        ) = None,
        exporter: Any | None = None,
        optimization_mode: (
            OptimizationMode
            | str
        ) = OptimizationMode.FAST,
        stable_optimizer: (
            StableOptimizer
            | None
        ) = None,
    ) -> None:
        # ====================================================
        # Dependencias principales
        # ====================================================

        if importer is None:
            raise ValueError(
                "importer cannot be None."
            )

        if not isinstance(
            importer,
            CssStatsImporter,
        ):
            raise TypeError(
                "importer must be a CssStatsImporter instance."
            )

        if generator is None:
            raise ValueError(
                "generator cannot be None."
            )

        if not isinstance(
            generator,
            SnakeDraftGenerator,
        ):
            raise TypeError(
                "generator must be a SnakeDraftGenerator instance."
            )

        if optimizer is None:
            raise ValueError(
                "optimizer cannot be None."
            )

        if not isinstance(
            optimizer,
            LocalOptimizer,
        ):
            raise TypeError(
                "optimizer must be a LocalOptimizer instance."
            )

        # ====================================================
        # PREASSIGNED
        # ====================================================

        if (
            preassigned_generator is not None
            and not isinstance(
                preassigned_generator,
                PreassignedTeamGenerator,
            )
        ):
            raise TypeError(
                "preassigned_generator must be a "
                "PreassignedTeamGenerator or None."
            )

        if (
            preassigned_evaluator is not None
            and not isinstance(
                preassigned_evaluator,
                PreassignedTeamEvaluator,
            )
        ):
            raise TypeError(
                "preassigned_evaluator must be a "
                "PreassignedTeamEvaluator or None."
            )

        # ====================================================
        # Optimization mode
        # ====================================================

        resolved_optimization_mode = (
            OptimizationMode.from_value(
                optimization_mode
            )
        )

        resolved_optimization_mode.require_available()

        if (
            stable_optimizer is not None
            and not isinstance(
                stable_optimizer,
                StableOptimizer,
            )
        ):
            raise TypeError(
                "stable_optimizer must be a "
                "StableOptimizer or None."
            )

        if (
            resolved_optimization_mode
            is OptimizationMode.STABLE
            and stable_optimizer is None
        ):
            raise ValueError(
                "stable_optimizer is required when "
                "optimization_mode is STABLE."
            )

        self._importer = importer
        self._generator = generator

        self._optimizer = optimizer

        self._preassigned_generator = (
            preassigned_generator
        )

        self._preassigned_evaluator = (
            preassigned_evaluator
        )

        self._exporter = exporter

        self._optimization_mode = (
            resolved_optimization_mode
        )

        self._stable_optimizer = (
            stable_optimizer
        )

    # ========================================================
    # Entrada desde archivo
    # ========================================================

    def run(
        self,
        source: str | Path,
        number_of_teams: int,
        title: str | None = None,
        metadata: (
            Mapping[str, Any]
            | None
        ) = None,
    ) -> BaseReportResult:
        """
        Importa jugadores y ejecuta automáticamente el flujo correcto.

        La columna Team determina ReportMode.

        OptimizationMode solo se aplica cuando ReportMode es OPTIMIZED.
        """
        players = self._importer.load(
            source
        )

        return self.run_players(
            players=players,
            number_of_teams=number_of_teams,
            title=title,
            metadata=metadata,
        )

    # ========================================================
    # Entrada desde Player[]
    # ========================================================

    def run_players(
        self,
        players: Sequence[Player],
        number_of_teams: int,
        title: str | None = None,
        metadata: (
            Mapping[str, Any]
            | None
        ) = None,
    ) -> BaseReportResult:
        """
        Punto principal de ejecución.

        Detecta automáticamente:

            PREASSIGNED
                → evalúa la distribución CSV.

            OPTIMIZED
                → genera equipos.
                → ejecuta FAST o STABLE.

        GLOBAL se ejecuta fuera de esta fachada usando el resultado
        STABLE como warm start.
        """
        player_list = self._validate_players(
            players
        )

        self._validate_number_of_teams(
            number_of_teams
        )

        report_mode = self.detect_mode(
            player_list
        )

        if (
            report_mode
            is ReportMode.PREASSIGNED
        ):
            return self._run_preassigned(
                players=player_list,
                number_of_teams=number_of_teams,
                title=title,
                metadata=metadata,
            )

        return self._run_optimized(
            players=player_list,
            number_of_teams=number_of_teams,
            title=title,
            metadata=metadata,
        )

    # ========================================================
    # Detección del modo
    # ========================================================

    @staticmethod
    def detect_mode(
        players: Sequence[Player],
    ) -> ReportMode:
        """
        Detecta el flujo basándose en player.team_number.

        Reglas:

            ningún jugador tiene Team
                → OPTIMIZED

            todos tienen Team
                → PREASSIGNED

            solo algunos tienen Team
                → error

        No permitimos una composición parcialmente preasignada porque
        su semántica sería ambigua.
        """
        player_list = (
            LanBalancer._validate_players(
                players
            )
        )

        assignments = [
            getattr(
                player,
                "team_number",
                None,
            )
            for player in player_list
        ]

        assigned_count = sum(
            1
            for value in assignments
            if value is not None
        )

        if assigned_count == 0:
            return ReportMode.OPTIMIZED

        if (
            assigned_count
            == len(
                player_list
            )
        ):
            return ReportMode.PREASSIGNED

        raise ValueError(
            "Partial team assignment is not supported. "
            "Either every player must provide Team or none of them."
        )

    # ========================================================
    # OPTIMIZED
    # ========================================================

    def _run_optimized(
        self,
        players: Sequence[Player],
        number_of_teams: int,
        title: str | None,
        metadata: (
            Mapping[str, Any]
            | None
        ),
    ) -> OptimizationResult:
        """
        Genera la distribución inicial mediante Snake Draft y después
        aplica el modo de optimización configurado.
        """
        initial_teams = (
            self._generator.generate(
                players=players,
                number_of_teams=number_of_teams,
            )
        )

        if (
            self._optimization_mode
            is OptimizationMode.FAST
        ):
            result = (
                self._optimizer.optimize(
                    initial_teams
                )
            )

            return self._decorate_optimization_result(
                result=result,
                title=title,
                metadata=self._build_optimization_metadata(
                    metadata=metadata,
                    stable_run=None,
                ),
            )

        if (
            self._optimization_mode
            is OptimizationMode.STABLE
        ):
            if self._stable_optimizer is None:
                raise RuntimeError(
                    "STABLE mode requires "
                    "stable_optimizer."
                )

            stable_run = (
                self._stable_optimizer
                .optimize_with_details(
                    initial_teams
                )
            )

            return self._decorate_optimization_result(
                result=stable_run.result,
                title=title,
                metadata=self._build_optimization_metadata(
                    metadata=metadata,
                    stable_run=stable_run,
                ),
            )

        raise NotImplementedError(
            f"Optimization mode "
            f"'{self._optimization_mode.value}' "
            "is not implemented."
        )

    # ========================================================
    # PREASSIGNED
    # ========================================================

    def _run_preassigned(
        self,
        players: Sequence[Player],
        number_of_teams: int,
        title: str | None,
        metadata: (
            Mapping[str, Any]
            | None
        ),
    ) -> BaseReportResult:
        """
        Construye y evalúa exclusivamente los equipos definidos por CSV.

        OptimizationMode NO participa en este flujo.
        """
        if (
            self._preassigned_generator
            is None
        ):
            raise RuntimeError(
                "No preassigned_generator has been configured."
            )

        if (
            self._preassigned_evaluator
            is None
        ):
            raise RuntimeError(
                "No preassigned_evaluator has been configured."
            )

        teams = (
            self._preassigned_generator
            .generate(
                players=players,
                number_of_teams=number_of_teams,
            )
        )

        evaluation_metadata = dict(
            metadata
            or {}
        )

        evaluation_metadata[
            "optimization_mode"
        ] = None

        evaluation_metadata[
            "optimization_applied"
        ] = False

        evaluation_metadata[
            "preassigned"
        ] = True

        return (
            self._preassigned_evaluator
            .evaluate(
                teams=teams,
                title=title,
                metadata=evaluation_metadata,
            )
        )

    # ========================================================
    # API FAST explícita
    # ========================================================

    def balance_players(
        self,
        players: Sequence[Player],
        number_of_teams: int,
    ) -> OptimizationResult:
        """
        API histórica de balanceo.

        Respeta actualmente optimization_mode.

        Es equivalente al flujo OPTIMIZED, pero no permite jugadores
        con Team preasignado.
        """
        player_list = self._validate_players(
            players
        )

        self._validate_number_of_teams(
            number_of_teams
        )

        mode = self.detect_mode(
            player_list
        )

        if (
            mode
            is ReportMode.PREASSIGNED
        ):
            raise ValueError(
                "balance_players() cannot be used "
                "with preassigned teams. "
                "Use run_players() instead."
            )

        return self._run_optimized(
            players=player_list,
            number_of_teams=number_of_teams,
            title=None,
            metadata=None,
        )

    def balance(
        self,
        source: str | Path,
        number_of_teams: int,
    ) -> OptimizationResult:
        players = self._importer.load(
            source
        )

        return self.balance_players(
            players=players,
            number_of_teams=number_of_teams,
        )

    # ========================================================
    # Exportación
    # ========================================================

    def export(
        self,
        result: BaseReportResult,
        output: str | Path,
    ) -> Path:
        """
        Exporta cualquier BaseReportResult compatible.
        """
        if self._exporter is None:
            raise RuntimeError(
                "No exporter has been configured."
            )

        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not isinstance(
            result,
            BaseReportResult,
        ):
            raise TypeError(
                "result must be a "
                "BaseReportResult instance."
            )

        if output is None:
            raise ValueError(
                "output cannot be None."
            )

        export_method = getattr(
            self._exporter,
            "export",
            None,
        )

        if not callable(
            export_method
        ):
            raise TypeError(
                "The configured exporter must "
                "provide export()."
            )

        exported_path = (
            export_method(
                result=result,
                output=output,
            )
        )

        return Path(
            exported_path
        )

    def run_and_export(
        self,
        source: str | Path,
        number_of_teams: int,
        output: str | Path,
        title: str | None = None,
        metadata: (
            Mapping[str, Any]
            | None
        ) = None,
    ) -> BaseReportResult:
        result = self.run(
            source=source,
            number_of_teams=number_of_teams,
            title=title,
            metadata=metadata,
        )

        self.export(
            result=result,
            output=output,
        )

        return result

    # ========================================================
    # Metadata
    # ========================================================

    def _build_optimization_metadata(
        self,
        metadata: (
            Mapping[str, Any]
            | None
        ),
        stable_run: (
            StableOptimizationRun
            | None
        ),
    ) -> dict[str, Any]:
        result = dict(
            metadata
            or {}
        )

        result[
            "optimization_applied"
        ] = True

        result[
            "optimization_mode"
        ] = (
            self._optimization_mode.value
        )

        result[
            "optimization_mode_label"
        ] = (
            self._optimization_mode.label
        )

        result[
            "optimization_deterministic"
        ] = (
            self._optimization_mode.deterministic
        )

        if stable_run is not None:
            result[
                "stable_optimization"
            ] = stable_run.as_dict()

        return result

    # ========================================================
    # Decoración del OptimizationResult
    # ========================================================

    @staticmethod
    def _decorate_optimization_result(
        result: OptimizationResult,
        title: str | None,
        metadata: Mapping[str, Any],
    ) -> OptimizationResult:
        """
        LocalOptimizer ya devuelve un OptimizationResult.

        Para no modificar esa capa, reconstruimos únicamente el objeto
        de resultado añadiendo title y metadata.

        Los equipos, ObjectiveResult e historial permanecen intactos.
        """
        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not isinstance(
            result,
            OptimizationResult,
        ):
            raise TypeError(
                "result must be an "
                "OptimizationResult instance."
            )

        existing_metadata = dict(
            getattr(
                result,
                "metadata",
                {},
            )
            or {}
        )

        existing_metadata.update(
            dict(
                metadata
            )
        )

        resolved_title = (
            title
            if title is not None
            else getattr(
                result,
                "title",
                None,
            )
        )

        return OptimizationResult(
            teams=result.teams,
            objective_result=(
                result.objective_result
            ),
            history=result.history,
            title=resolved_title,
            metadata=existing_metadata,
        )

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_players(
        players: Sequence[Player],
    ) -> list[Player]:
        if players is None:
            raise ValueError(
                "players cannot be None."
            )

        try:
            player_list = list(
                players
            )

        except TypeError as error:
            raise TypeError(
                "players must be iterable."
            ) from error

        if not player_list:
            raise ValueError(
                "At least one player is required."
            )

        for index, player in enumerate(
            player_list,
            start=1,
        ):
            if player is None:
                raise ValueError(
                    f"Player {index} cannot be None."
                )

            if not isinstance(
                player,
                Player,
            ):
                raise TypeError(
                    f"Player {index} must be "
                    "a Player instance."
                )

        LanBalancer._validate_unique_players(
            player_list
        )

        return player_list

    @staticmethod
    def _validate_unique_players(
        players: Sequence[Player],
    ) -> None:
        identities: list[
            tuple[str, str]
        ] = []

        for player in players:
            steam_id = getattr(
                player,
                "steam_id",
                None,
            )

            if steam_id:
                identity = (
                    "steam",
                    str(
                        steam_id
                    ).strip(),
                )

            else:
                nickname = getattr(
                    player,
                    "nickname",
                    getattr(
                        player,
                        "nick",
                        None,
                    ),
                )

                if nickname is None:
                    raise ValueError(
                        "Every player must have either "
                        "steam_id or nickname."
                    )

                normalized_nickname = (
                    str(
                        nickname
                    )
                    .strip()
                    .casefold()
                )

                if not normalized_nickname:
                    raise ValueError(
                        "Player nickname cannot be empty."
                    )

                identity = (
                    "nickname",
                    normalized_nickname,
                )

            identities.append(
                identity
            )

        if (
            len(
                identities
            )
            != len(
                set(
                    identities
                )
            )
        ):
            raise ValueError(
                "The player collection contains "
                "duplicated players."
            )

    @staticmethod
    def _validate_number_of_teams(
        number_of_teams: int,
    ) -> None:
        if (
            isinstance(
                number_of_teams,
                bool,
            )
            or not isinstance(
                number_of_teams,
                int,
            )
        ):
            raise TypeError(
                "number_of_teams must be an integer."
            )

        if number_of_teams <= 0:
            raise ValueError(
                "number_of_teams must be "
                "greater than zero."
            )

    # ========================================================
    # Estado STABLE
    # ========================================================

    @property
    def last_stable_run(
        self,
    ) -> StableOptimizationRun | None:
        if self._stable_optimizer is None:
            return None

        return (
            self._stable_optimizer.last_run
        )

    # ========================================================
    # Dependencias
    # ========================================================

    @property
    def importer(
        self,
    ) -> CssStatsImporter:
        return self._importer

    @property
    def generator(
        self,
    ) -> SnakeDraftGenerator:
        return self._generator

    @property
    def optimizer(
        self,
    ) -> LocalOptimizer:
        return self._optimizer

    @property
    def local_optimizer(
        self,
    ) -> LocalOptimizer:
        return self._optimizer

    @property
    def stable_optimizer(
        self,
    ) -> StableOptimizer | None:
        return self._stable_optimizer

    @property
    def optimization_mode(
        self,
    ) -> OptimizationMode:
        return (
            self._optimization_mode
        )

    @property
    def preassigned_generator(
        self,
    ) -> PreassignedTeamGenerator | None:
        return (
            self._preassigned_generator
        )

    @property
    def preassigned_evaluator(
        self,
    ) -> PreassignedTeamEvaluator | None:
        return (
            self._preassigned_evaluator
        )

    @property
    def exporter(
        self,
    ):
        return self._exporter

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        stable_name = (
            self._stable_optimizer
            .__class__.__name__
            if self._stable_optimizer
            is not None
            else "None"
        )

        exporter_name = (
            self._exporter
            .__class__.__name__
            if self._exporter
            is not None
            else "None"
        )

        return (
            f"{self.__class__.__name__}("
            f"optimization_mode="
            f"{self._optimization_mode.value!r}, "
            f"importer="
            f"{self._importer.__class__.__name__}, "
            f"generator="
            f"{self._generator.__class__.__name__}, "
            f"optimizer="
            f"{self._optimizer.__class__.__name__}, "
            f"stable_optimizer="
            f"{stable_name}, "
            f"exporter="
            f"{exporter_name})"
        )
