from __future__ import annotations

import csv
import inspect
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from models.player import Player
from scrapers.player_record import ActivityRecord


class CssStatsImporter:
    """
    Importa jugadores desde el CSV intermedio generado a partir
    de la FACEIT Data API.

    Aunque conserva el nombre histórico CssStatsImporter, actualmente
    importa estadísticas de FACEIT, actividad competitiva y
    configuración del evento.

    Columnas reconocidas:

        Identidad:
            Nick
            SteamID
            ProfileURL
            FaceitURL
            CssStatsURL

        Rendimiento:
            ELO
            FaceitLevel
            KD
            Rating
            ADR
            KPR
            DPR
            HS
            KAST
            Winrate
            RecentWinrate
            Clutch
            Matches

        Actividad:
            Matches0_7Days
            Matches8_30Days
            Matches31_90Days
            TotalMatches90Days
            LastMatchAt
            DaysSinceLastMatch
            ActivityHistoryComplete

        Configuración del evento:
            Role
            Seed
            Team

        Trazabilidad:
            Source

    Solo Nick es obligatorio.

    Team es opcional para mantener los dos modos del producto:

        - Generación automática de equipos.
        - Evaluación de equipos predeterminados.

    Cuando Team existe, debe ser un entero positivo. El rango concreto,
    por ejemplo 1–4, se validará posteriormente en
    PreassignedTeamGenerator.
    """

    FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        # -----------------------------------------------------
        # Identidad
        # -----------------------------------------------------

        "nick": (
            "nick",
            "nickname",
            "player",
            "player_name",
            "display_name",
        ),
        "steam_id": (
            "steam_id",
            "steamid",
            "steam_id_64",
            "steamid64",
            "game_player_id",
        ),
        "profile_url": (
            "profile_url",
            "profileurl",
        ),
        "faceit_url": (
            "faceit_url",
            "faceiturl",
        ),
        "csstats_url": (
            "csstats_url",
            "css_stats_url",
            "cssstatsurl",
        ),

        # -----------------------------------------------------
        # FACEIT
        # -----------------------------------------------------

        "elo": (
            "elo",
            "faceit_elo",
            "faceitelo",
        ),
        "level": (
            "level",
            "lvl",
            "faceit_level",
            "faceitlevel",
            "skill_level",
        ),

        # -----------------------------------------------------
        # Rendimiento
        # -----------------------------------------------------

        "kd": (
            "kd",
            "k_d",
            "kd_ratio",
            "k_d_ratio",
            "average_k_d_ratio",
            "average_kd_ratio",
        ),
        "rating": (
            "rating",
            "average_rating",
            "avg_rating",
        ),
        "adr": (
            "adr",
            "average_adr",
            "avg_adr",
            "average_damage_per_round",
        ),
        "kpr": (
            "kpr",
            "kills_per_round",
            "average_kills_per_round",
        ),
        "dpr": (
            "dpr",
            "deaths_per_round",
            "average_deaths_per_round",
        ),
        "hs": (
            "hs",
            "hs_percentage",
            "headshots",
            "headshots_percentage",
            "average_headshots",
        ),
        "kast": (
            "kast",
            "kast_percentage",
            "average_kast",
        ),
        "winrate": (
            "winrate",
            "win_rate",
            "win_rate_percentage",
        ),
        "recent_winrate": (
            "recent_winrate",
            "recent_win_rate",
            "recent_win_rate_percentage",
        ),
        "clutch": (
            "clutch",
            "clutch_percentage",
            "clutch_winrate",
            "clutch_win_rate",
        ),
        "matches": (
            "matches",
            "match_count",
            "games",
            "games_played",
        ),

        # -----------------------------------------------------
        # Actividad competitiva
        # -----------------------------------------------------

        "matches_0_7_days": (
            "matches_0_7_days",
            "matches0_7_days",
            "matches_0_to_7_days",
            "matches_last_7_days",
        ),
        "matches_8_30_days": (
            "matches_8_30_days",
            "matches8_30_days",
            "matches_8_to_30_days",
        ),
        "matches_31_90_days": (
            "matches_31_90_days",
            "matches31_90_days",
            "matches_31_to_90_days",
        ),
        "total_matches_90_days": (
            "total_matches_90_days",
            "totalmatches90days",
            "matches_last_90_days",
            "matches_90_days",
        ),
        "last_match_at": (
            "last_match_at",
            "lastmatchat",
            "last_match_timestamp",
        ),
        "days_since_last_match": (
            "days_since_last_match",
            "dayssincelastmatch",
            "inactive_days",
        ),
        "activity_history_complete": (
            "activity_history_complete",
            "activityhistorycomplete",
            "history_complete",
        ),

        # -----------------------------------------------------
        # Configuración del evento
        # -----------------------------------------------------

        "role": (
            "role",
            "player_role",
        ),
        "seed": (
            "seed",
            "seed_number",
            "seednumber",
            "seed_level",
        ),
        "team_number": (
            "team",
            "team_number",
            "teamnumber",
            "team_id",
            "teamid",
            "assigned_team",
            "assignedteam",
            "equipo",
            "numero_equipo",
        ),

        # -----------------------------------------------------
        # Trazabilidad
        # -----------------------------------------------------

        "source": (
            "source",
            "data_source",
        ),
    }

    REQUIRED_FIELDS = (
        "nick",
    )

    def __init__(
        self,
        strict: bool = True,
        encoding: str = "utf-8-sig",
    ) -> None:
        if not isinstance(
            strict,
            bool,
        ):
            raise TypeError(
                "strict must be a boolean."
            )

        if not isinstance(
            encoding,
            str,
        ):
            raise TypeError(
                "encoding must be a string."
            )

        normalized_encoding = encoding.strip()

        if not normalized_encoding:
            raise ValueError(
                "encoding cannot be empty."
            )

        self._strict = strict
        self._encoding = normalized_encoding
        self._errors: list[dict[str, Any]] = []

    # ========================================================
    # API pública
    # ========================================================

    def load(
        self,
        source: str | Path,
    ) -> list[Player]:
        """
        Lee el CSV y construye los objetos Player.

        En modo estricto:
            El primer error detiene la importación.

        En modo no estricto:
            Las filas incorrectas se registran en `errors` y se
            continúa con las siguientes.
        """
        path = self._validate_source(
            source
        )

        self._errors.clear()

        rows = self._read_csv(
            path
        )

        if not rows:
            raise ValueError(
                "The player CSV does not contain data rows."
            )

        self._validate_team_assignment_consistency(
            rows
        )

        players: list[Player] = []

        seen_nicks: set[str] = set()
        seen_steam_ids: set[str] = set()

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            try:
                player = self._build_player(
                    row=row,
                    row_number=row_number,
                )

                nickname = self._get_player_nickname(
                    player
                )

                normalized_nick = (
                    nickname
                    .strip()
                    .casefold()
                )

                if normalized_nick in seen_nicks:
                    raise ValueError(
                        f"Duplicated Nick '{nickname}'."
                    )

                steam_id = getattr(
                    player,
                    "steam_id",
                    None,
                )

                normalized_steam_id: str | None = None

                if steam_id:
                    normalized_steam_id = (
                        str(steam_id)
                        .strip()
                        .casefold()
                    )

                    if normalized_steam_id in seen_steam_ids:
                        raise ValueError(
                            f"Duplicated Steam ID "
                            f"'{steam_id}'."
                        )

                seen_nicks.add(
                    normalized_nick
                )

                if normalized_steam_id:
                    seen_steam_ids.add(
                        normalized_steam_id
                    )

                players.append(
                    player
                )

            except (
                TypeError,
                ValueError,
                RuntimeError,
            ) as error:
                error_information = {
                    "row": row_number,
                    "nick": self._find_value(
                        row,
                        self.FIELD_ALIASES["nick"],
                    ),
                    "team_number": self._find_value(
                        row,
                        self.FIELD_ALIASES[
                            "team_number"
                        ],
                    ),
                    "error": str(error),
                }

                self._errors.append(
                    error_information
                )

                if self._strict:
                    raise RuntimeError(
                        f"Could not import row "
                        f"{row_number}: {error}"
                    ) from error

        if not players:
            raise RuntimeError(
                "No valid Player instances were imported."
            )

        return players

    def import_players(
        self,
        source: str | Path,
    ) -> list[Player]:
        """
        Alias de load() mantenido por compatibilidad.
        """
        return self.load(
            source
        )

    # ========================================================
    # Construcción del jugador
    # ========================================================

    def _build_player(
        self,
        row: Mapping[str, Any],
        row_number: int,
    ) -> Player:
        """
        Convierte una fila normalizada en Player.
        """
        activity_values = self._extract_activity_values(
            row=row,
            row_number=row_number,
        )

        activity = self._build_activity_record(
            values=activity_values,
            row_number=row_number,
        )

        team_number = self._optional_positive_integer(
            value=self._find_value(
                row,
                self.FIELD_ALIASES["team_number"],
            ),
            field_name="Team",
            row_number=row_number,
        )

        values: dict[str, Any] = {
            # -------------------------------------------------
            # Identidad
            # -------------------------------------------------

            "nick": self._required_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["nick"],
                ),
                field_name="Nick",
                row_number=row_number,
            ),

            "steam_id": self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["steam_id"],
                )
            ),

            "profile_url": self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["profile_url"],
                )
            ),

            "faceit_url": self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["faceit_url"],
                )
            ),

            "csstats_url": self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["csstats_url"],
                )
            ),

            # -------------------------------------------------
            # FACEIT
            # -------------------------------------------------

            "elo": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["elo"],
                ),
                field_name="ELO",
                row_number=row_number,
            ),

            "level": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["level"],
                ),
                field_name="FaceitLevel",
                row_number=row_number,
            ),

            # -------------------------------------------------
            # Rendimiento
            # -------------------------------------------------

            "kd": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["kd"],
                ),
                field_name="KD",
                row_number=row_number,
            ),

            "rating": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["rating"],
                ),
                field_name="Rating",
                row_number=row_number,
            ),

            "adr": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["adr"],
                ),
                field_name="ADR",
                row_number=row_number,
            ),

            "kpr": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["kpr"],
                ),
                field_name="KPR",
                row_number=row_number,
            ),

            "dpr": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["dpr"],
                ),
                field_name="DPR",
                row_number=row_number,
            ),

            "hs": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["hs"],
                ),
                field_name="HS",
                row_number=row_number,
            ),

            "kast": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["kast"],
                ),
                field_name="KAST",
                row_number=row_number,
            ),

            "winrate": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["winrate"],
                ),
                field_name="Winrate",
                row_number=row_number,
            ),

            "recent_winrate": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "recent_winrate"
                    ],
                ),
                field_name="RecentWinrate",
                row_number=row_number,
            ),

            "clutch": self._optional_float(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["clutch"],
                ),
                field_name="Clutch",
                row_number=row_number,
            ),

            "matches": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["matches"],
                ),
                field_name="Matches",
                row_number=row_number,
            ),

            # -------------------------------------------------
            # Actividad
            # -------------------------------------------------

            "activity": activity,

            # Compatibilidad temporal con constructores Player que
            # utilicen la actividad aplanada.
            **activity_values,

            # -------------------------------------------------
            # Configuración del evento
            # -------------------------------------------------

            "role": self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["role"],
                )
            ),

            "seed": self._optional_positive_integer(
                value=self._find_value(
                    row,
                    self.FIELD_ALIASES["seed"],
                ),
                field_name="Seed",
                row_number=row_number,
            ),

            "team_number": team_number,

            # -------------------------------------------------
            # Trazabilidad
            # -------------------------------------------------

            "source": self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["source"],
                )
            ),
        }

        self._validate_player_values(
            values=values,
            row_number=row_number,
        )

        return self._construct_player(
            values=values,
            row_number=row_number,
        )

    # ========================================================
    # Actividad
    # ========================================================

    def _extract_activity_values(
        self,
        row: Mapping[str, Any],
        row_number: int,
    ) -> dict[str, Any]:
        """
        Extrae las columnas de actividad del CSV.

        Si el CSV no contiene información de actividad, todos los
        valores serán None y no se construirá ActivityRecord.
        """
        return {
            "matches_0_7_days": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "matches_0_7_days"
                    ],
                ),
                field_name="Matches0_7Days",
                row_number=row_number,
            ),

            "matches_8_30_days": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "matches_8_30_days"
                    ],
                ),
                field_name="Matches8_30Days",
                row_number=row_number,
            ),

            "matches_31_90_days": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "matches_31_90_days"
                    ],
                ),
                field_name="Matches31_90Days",
                row_number=row_number,
            ),

            "total_matches_90_days": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "total_matches_90_days"
                    ],
                ),
                field_name="TotalMatches90Days",
                row_number=row_number,
            ),

            "last_match_at": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "last_match_at"
                    ],
                ),
                field_name="LastMatchAt",
                row_number=row_number,
            ),

            "days_since_last_match": self._optional_int(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "days_since_last_match"
                    ],
                ),
                field_name="DaysSinceLastMatch",
                row_number=row_number,
            ),

            "activity_history_complete": self._optional_bool(
                self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "activity_history_complete"
                    ],
                ),
                field_name=(
                    "ActivityHistoryComplete"
                ),
                row_number=row_number,
            ),
        }

    @staticmethod
    def _build_activity_record(
        values: Mapping[str, Any],
        row_number: int,
    ) -> ActivityRecord | None:
        """
        Construye ActivityRecord cuando existe información de actividad.

        Los contadores ausentes se interpretan como cero únicamente
        cuando existe al menos un dato relacionado con actividad.
        """
        activity_fields = (
            "matches_0_7_days",
            "matches_8_30_days",
            "matches_31_90_days",
            "total_matches_90_days",
            "last_match_at",
            "days_since_last_match",
            "activity_history_complete",
        )

        has_activity_information = any(
            values.get(field_name) is not None
            for field_name in activity_fields
        )

        if not has_activity_information:
            return None

        matches_0_7_days = (
            values.get("matches_0_7_days")
            or 0
        )

        matches_8_30_days = (
            values.get("matches_8_30_days")
            or 0
        )

        matches_31_90_days = (
            values.get("matches_31_90_days")
            or 0
        )

        calculated_total = (
            matches_0_7_days
            + matches_8_30_days
            + matches_31_90_days
        )

        provided_total = values.get(
            "total_matches_90_days"
        )

        total_matches_90_days = (
            calculated_total
            if provided_total is None
            else provided_total
        )

        history_complete = values.get(
            "activity_history_complete"
        )

        if history_complete is None:
            history_complete = True

        try:
            return ActivityRecord(
                matches_0_7_days=matches_0_7_days,
                matches_8_30_days=matches_8_30_days,
                matches_31_90_days=matches_31_90_days,
                total_matches_90_days=(
                    total_matches_90_days
                ),
                last_match_at=values.get(
                    "last_match_at"
                ),
                days_since_last_match=values.get(
                    "days_since_last_match"
                ),
                history_complete=history_complete,
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise ValueError(
                f"Invalid activity data at row "
                f"{row_number}: {error}"
            ) from error

    # ========================================================
    # Construcción adaptable de Player
    # ========================================================

    def _construct_player(
        self,
        values: dict[str, Any],
        row_number: int,
    ) -> Player:
        """
        Adapta los valores al constructor real de Player.

        Permite compatibilidad con firmas como:

            Player(nick=...)
            Player(nickname=...)

            Player(level=...)
            Player(faceit_level=...)

            Player(team_number=...)
            Player(assigned_team_number=...)

            Player(activity=ActivityRecord(...))
        """
        signature = inspect.signature(
            Player.__init__
        )

        parameters = {
            name: parameter
            for name, parameter
            in signature.parameters.items()
            if name != "self"
        }

        aliases_by_parameter: dict[
            str,
            tuple[str, ...],
        ] = {
            "nick": (
                "nick",
            ),
            "nickname": (
                "nick",
            ),
            "elo": (
                "elo",
            ),
            "faceit_elo": (
                "elo",
            ),
            "level": (
                "level",
            ),
            "faceit_level": (
                "level",
            ),
            "kd": (
                "kd",
            ),
            "rating": (
                "rating",
            ),
            "adr": (
                "adr",
            ),
            "kpr": (
                "kpr",
            ),
            "dpr": (
                "dpr",
            ),
            "hs": (
                "hs",
            ),
            "kast": (
                "kast",
            ),
            "winrate": (
                "winrate",
            ),
            "recent_winrate": (
                "recent_winrate",
            ),
            "clutch": (
                "clutch",
            ),
            "matches": (
                "matches",
            ),
            "steam_id": (
                "steam_id",
            ),
            "role": (
                "role",
            ),
            "seed": (
                "seed",
            ),

            # Equipo predeterminado
            "team_number": (
                "team_number",
            ),
            "assigned_team_number": (
                "team_number",
            ),
            "team": (
                "team_number",
            ),

            "source": (
                "source",
            ),
            "profile_url": (
                "profile_url",
            ),
            "faceit_url": (
                "faceit_url",
            ),
            "csstats_url": (
                "csstats_url",
            ),

            # Actividad agregada
            "activity": (
                "activity",
            ),

            # Compatibilidad con actividad aplanada
            "matches_0_7_days": (
                "matches_0_7_days",
            ),
            "matches_8_30_days": (
                "matches_8_30_days",
            ),
            "matches_31_90_days": (
                "matches_31_90_days",
            ),
            "total_matches_90_days": (
                "total_matches_90_days",
            ),
            "last_match_at": (
                "last_match_at",
            ),
            "days_since_last_match": (
                "days_since_last_match",
            ),
            "activity_history_complete": (
                "activity_history_complete",
            ),
            "history_complete": (
                "activity_history_complete",
            ),
        }

        constructor_arguments: dict[str, Any] = {}
        missing_required: list[str] = []

        for parameter_name, parameter in parameters.items():
            if parameter.kind in {
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            }:
                continue

            aliases = aliases_by_parameter.get(
                parameter_name,
                (parameter_name,),
            )

            value_found = False

            for alias in aliases:
                if alias not in values:
                    continue

                constructor_arguments[
                    parameter_name
                ] = values[alias]

                value_found = True
                break

            if value_found:
                continue

            if (
                parameter.default
                is inspect.Parameter.empty
            ):
                missing_required.append(
                    parameter_name
                )

        if missing_required:
            raise TypeError(
                "Player constructor contains unsupported required "
                f"arguments: {missing_required}."
            )

        try:
            return Player(
                **constructor_arguments
            )

        except Exception as error:
            nickname = values.get(
                "nick",
                "Unknown",
            )

            raise RuntimeError(
                f"Player constructor failed for "
                f"'{nickname}' at row {row_number}. "
                f"Arguments: "
                f"{sorted(constructor_arguments.keys())}. "
                f"Original error: {error}"
            ) from error

    # ========================================================
    # Validaciones de datos
    # ========================================================

    @staticmethod
    def _validate_player_values(
        values: Mapping[str, Any],
        row_number: int,
    ) -> None:
        seed = values.get(
            "seed"
        )

        if seed is not None and seed <= 0:
            raise ValueError(
                f"Seed must be greater than zero "
                f"at row {row_number}."
            )

        team_number = values.get(
            "team_number"
        )

        if (
            team_number is not None
            and team_number <= 0
        ):
            raise ValueError(
                f"Team must be greater than zero "
                f"at row {row_number}."
            )

        level = values.get(
            "level"
        )

        if (
            level is not None
            and not 1 <= level <= 10
        ):
            raise ValueError(
                f"FaceitLevel must be between 1 and 10 "
                f"at row {row_number}."
            )

        elo = values.get(
            "elo"
        )

        if elo is not None and elo < 0:
            raise ValueError(
                f"ELO cannot be negative "
                f"at row {row_number}."
            )

        non_negative_integer_fields = (
            "matches",
            "matches_0_7_days",
            "matches_8_30_days",
            "matches_31_90_days",
            "total_matches_90_days",
            "last_match_at",
            "days_since_last_match",
        )

        for field_name in non_negative_integer_fields:
            value = values.get(
                field_name
            )

            if value is None:
                continue

            if value < 0:
                raise ValueError(
                    f"{field_name} cannot be negative "
                    f"at row {row_number}."
                )

        percentage_fields = (
            "hs",
            "kast",
            "winrate",
            "recent_winrate",
            "clutch",
        )

        for field_name in percentage_fields:
            value = values.get(
                field_name
            )

            if value is None:
                continue

            if not 0.0 <= value <= 100.0:
                raise ValueError(
                    f"{field_name} must be between "
                    f"0 and 100 at row {row_number}."
                )

        activity = values.get(
            "activity"
        )

        if (
            activity is not None
            and not isinstance(
                activity,
                ActivityRecord,
            )
        ):
            raise TypeError(
                f"activity must be an ActivityRecord "
                f"at row {row_number}."
            )

    def _validate_team_assignment_consistency(
        self,
        rows: list[dict[str, Any]],
    ) -> None:
        """
        Detecta una configuración parcial de equipos.

        Estados válidos:

            - Ningún jugador tiene Team.
            - Todos los jugadores tienen Team.

        Si solo algunas filas contienen Team, la importación se detiene
        para evitar una evaluación incompleta.
        """
        assigned_rows: list[int] = []
        unassigned_rows: list[int] = []

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            team_number = self._optional_positive_integer(
                value=self._find_value(
                    row,
                    self.FIELD_ALIASES[
                        "team_number"
                    ],
                ),
                field_name="Team",
                row_number=row_number,
            )

            if team_number is None:
                unassigned_rows.append(
                    row_number
                )

            else:
                assigned_rows.append(
                    row_number
                )

        if not assigned_rows:
            return

        if not unassigned_rows:
            return

        raise ValueError(
            "Team assignment is incomplete. "
            "When predefined teams are used, every player must "
            "contain a Team value. "
            f"Assigned rows: {assigned_rows}. "
            f"Rows without Team: {unassigned_rows}."
        )

    # ========================================================
    # Lectura del CSV
    # ========================================================

    def _read_csv(
        self,
        path: Path,
    ) -> list[dict[str, Any]]:
        """
        Lee el CSV detectando coma, punto y coma o tabulador.
        """
        with path.open(
            "r",
            encoding=self._encoding,
            newline="",
        ) as file:
            sample = file.read(
                4096
            )

            file.seek(0)

            try:
                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t",
                )

            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(
                file,
                dialect=dialect,
            )

            if not reader.fieldnames:
                raise ValueError(
                    "The CSV does not contain headers."
                )

            normalized_headers = {
                self._normalize_key(header)
                for header in reader.fieldnames
                if header is not None
            }

            self._validate_headers(
                normalized_headers
            )

            return [
                self._normalize_row(
                    row
                )
                for row in reader
                if self._row_contains_data(
                    row
                )
            ]

    def _validate_headers(
        self,
        headers: set[str],
    ) -> None:
        """
        Comprueba la existencia de las columnas obligatorias.

        Team continúa siendo opcional.
        """
        for required_field in self.REQUIRED_FIELDS:
            aliases = self.FIELD_ALIASES[
                required_field
            ]

            normalized_aliases = {
                self._normalize_key(alias)
                for alias in aliases
            }

            if headers.isdisjoint(
                normalized_aliases
            ):
                raise ValueError(
                    "The CSV must contain a "
                    f"'{required_field}' column."
                )

    @classmethod
    def _normalize_row(
        cls,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            cls._normalize_key(key): value
            for key, value in row.items()
            if key is not None
        }

    @staticmethod
    def _row_contains_data(
        row: Mapping[str, Any],
    ) -> bool:
        return any(
            value is not None
            and str(value).strip()
            for value in row.values()
        )

    @classmethod
    def _find_value(
        cls,
        row: Mapping[str, Any],
        aliases: tuple[str, ...],
    ) -> Any:
        for alias in aliases:
            normalized_alias = cls._normalize_key(
                alias
            )

            if normalized_alias in row:
                return row[
                    normalized_alias
                ]

        return None

    @staticmethod
    def _normalize_key(
        key: Any,
    ) -> str:
        """
        Convierte cabeceras como:

            FaceitLevel
                -> faceit_level

            Matches0_7Days
                -> matches0_7_days

            ActivityHistoryComplete
                -> activity_history_complete

            TeamNumber
                -> team_number

            AssignedTeam
                -> assigned_team
        """
        text = str(
            key
        ).strip()

        text = re.sub(
            r"(?<=[a-z0-9])(?=[A-Z])",
            "_",
            text,
        )

        text = re.sub(
            r"(?<=[A-Z])(?=[A-Z][a-z])",
            "_",
            text,
        )

        text = text.casefold()

        text = re.sub(
            r"[^a-z0-9]+",
            "_",
            text,
        )

        return text.strip(
            "_"
        )

    # ========================================================
    # Conversión de valores
    # ========================================================

    @staticmethod
    def _required_text(
        value: Any,
        field_name: str,
        row_number: int,
    ) -> str:
        text = CssStatsImporter._optional_text(
            value
        )

        if text is None:
            raise ValueError(
                f"{field_name} is required "
                f"at row {row_number}."
            )

        return text

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(
            value
        ).strip()

        return text or None

    @classmethod
    def _optional_int(
        cls,
        value: Any,
        field_name: str,
        row_number: int,
    ) -> int | None:
        number = cls._optional_float(
            value=value,
            field_name=field_name,
            row_number=row_number,
        )

        if number is None:
            return None

        if not float(number).is_integer():
            raise ValueError(
                f"{field_name} must be an integer "
                f"at row {row_number}, "
                f"received {value!r}."
            )

        return int(
            number
        )

    @staticmethod
    def _optional_positive_integer(
        value: Any,
        field_name: str,
        row_number: int,
    ) -> int | None:
        """
        Convierte una celda opcional en entero positivo.

        Se utiliza para Seed y Team.
        """
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{field_name} must be an integer "
                f"at row {row_number}."
            )

        text = str(
            value
        ).strip()

        if not text:
            return None

        try:
            number = float(
                text.replace(",", ".")
            )

        except ValueError as error:
            raise ValueError(
                f"{field_name} must be an integer "
                f"at row {row_number}, "
                f"received {value!r}."
            ) from error

        if not number.is_integer():
            raise ValueError(
                f"{field_name} must be an integer "
                f"at row {row_number}, "
                f"received {value!r}."
            )

        integer = int(
            number
        )

        if integer <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero "
                f"at row {row_number}."
            )

        return integer

    @staticmethod
    def _optional_float(
        value: Any,
        field_name: str,
        row_number: int,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{field_name} must be numeric "
                f"at row {row_number}."
            )

        if isinstance(
            value,
            (int, float),
        ):
            return float(
                value
            )

        text = (
            str(value)
            .strip()
            .replace("\u00a0", "")
            .replace(" ", "")
            .replace("%", "")
        )

        if not text:
            return None

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = (
                    text
                    .replace(".", "")
                    .replace(",", ".")
                )

            else:
                text = text.replace(
                    ",",
                    "",
                )

        else:
            text = text.replace(
                ",",
                ".",
            )

        try:
            return float(
                text
            )

        except ValueError as error:
            raise ValueError(
                f"{field_name} must be numeric "
                f"at row {row_number}, "
                f"received {value!r}."
            ) from error

    @staticmethod
    def _optional_bool(
        value: Any,
        field_name: str,
        row_number: int,
    ) -> bool | None:
        """
        Convierte representaciones habituales de booleanos.

        Una celda vacía devuelve None.
        """
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            return value

        if isinstance(
            value,
            (int, float),
        ):
            if value == 1:
                return True

            if value == 0:
                return False

        text = str(
            value
        ).strip().casefold()

        if not text:
            return None

        if text in {
            "true",
            "1",
            "yes",
            "y",
            "si",
            "sí",
        }:
            return True

        if text in {
            "false",
            "0",
            "no",
            "n",
        }:
            return False

        raise ValueError(
            f"{field_name} must be boolean "
            f"at row {row_number}, "
            f"received {value!r}."
        )

    # ========================================================
    # Utilidades
    # ========================================================

    @staticmethod
    def _get_player_nickname(
        player: Player,
    ) -> str:
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
                "The Player instance does not expose "
                "nick or nickname."
            )

        return str(
            nickname
        )

    @staticmethod
    def _validate_source(
        source: str | Path,
    ) -> Path:
        if source is None:
            raise ValueError(
                "source cannot be None."
            )

        if not isinstance(
            source,
            (str, Path),
        ):
            raise TypeError(
                "source must be a string or Path."
            )

        path = Path(
            source
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Player file not found: "
                f"{path.resolve()}"
            )

        if not path.is_file():
            raise ValueError(
                f"Player source is not a file: "
                f"{path.resolve()}"
            )

        if path.suffix.casefold() != ".csv":
            raise ValueError(
                "CssStatsImporter only supports CSV files."
            )

        return path

    # ========================================================
    # Propiedades
    # ========================================================

    @property
    def strict(
        self,
    ) -> bool:
        return self._strict

    @property
    def encoding(
        self,
    ) -> str:
        return self._encoding

    @property
    def errors(
        self,
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            self._errors
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"strict={self._strict}, "
            f"encoding={self._encoding!r})"
        )
