from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ActivityRecord:
    """
    Información sobre la actividad competitiva reciente del jugador.

    Las ventanas son independientes:

        matches_0_7_days:
            Partidas jugadas durante los últimos 7 días.

        matches_8_30_days:
            Partidas jugadas entre los días 8 y 30.

        matches_31_90_days:
            Partidas jugadas entre los días 31 y 90.

    total_matches_90_days debe coincidir con la suma de las tres
    ventanas anteriores.
    """

    matches_0_7_days: int = 0
    matches_8_30_days: int = 0
    matches_31_90_days: int = 0

    total_matches_90_days: int = 0

    last_match_at: int | None = None
    days_since_last_match: int | None = None

    history_complete: bool = True

    def __post_init__(self) -> None:
        self.matches_0_7_days = (
            self._validate_non_negative_integer(
                value=self.matches_0_7_days,
                field_name="matches_0_7_days",
            )
        )

        self.matches_8_30_days = (
            self._validate_non_negative_integer(
                value=self.matches_8_30_days,
                field_name="matches_8_30_days",
            )
        )

        self.matches_31_90_days = (
            self._validate_non_negative_integer(
                value=self.matches_31_90_days,
                field_name="matches_31_90_days",
            )
        )

        self.total_matches_90_days = (
            self._validate_non_negative_integer(
                value=self.total_matches_90_days,
                field_name="total_matches_90_days",
            )
        )

        self.last_match_at = (
            self._validate_optional_non_negative_integer(
                value=self.last_match_at,
                field_name="last_match_at",
            )
        )

        self.days_since_last_match = (
            self._validate_optional_non_negative_integer(
                value=self.days_since_last_match,
                field_name="days_since_last_match",
            )
        )

        self.history_complete = self._validate_boolean(
            value=self.history_complete,
            field_name="history_complete",
        )

        calculated_total = (
            self.matches_0_7_days
            + self.matches_8_30_days
            + self.matches_31_90_days
        )

        if calculated_total != self.total_matches_90_days:
            raise ValueError(
                "total_matches_90_days must equal the sum of "
                "matches_0_7_days, matches_8_30_days and "
                "matches_31_90_days."
            )

    @classmethod
    def from_mapping(
        cls,
        data: Mapping[str, Any] | None,
    ) -> ActivityRecord | None:
        """
        Construye ActivityRecord desde un diccionario.

        Devuelve None cuando no existe información de actividad.
        """
        if data is None:
            return None

        if not isinstance(data, Mapping):
            raise TypeError(
                "activity data must be a mapping or None."
            )

        activity_keys = {
            "matches_0_7_days",
            "matches_8_30_days",
            "matches_31_90_days",
            "total_matches_90_days",
            "last_match_at",
            "days_since_last_match",
            "history_complete",
            "activity_history_complete",
        }

        has_activity_information = any(
            key in data
            and data.get(key) not in {None, ""}
            for key in activity_keys
        )

        if not has_activity_information:
            return None

        matches_0_7_days = cls._coerce_optional_integer(
            data.get("matches_0_7_days")
        )

        matches_8_30_days = cls._coerce_optional_integer(
            data.get("matches_8_30_days")
        )

        matches_31_90_days = cls._coerce_optional_integer(
            data.get("matches_31_90_days")
        )

        calculated_total = (
            (matches_0_7_days or 0)
            + (matches_8_30_days or 0)
            + (matches_31_90_days or 0)
        )

        provided_total = cls._coerce_optional_integer(
            data.get("total_matches_90_days")
        )

        total_matches_90_days = (
            calculated_total
            if provided_total is None
            else provided_total
        )

        history_complete_value = data.get(
            "history_complete",
            data.get(
                "activity_history_complete",
                True,
            ),
        )

        return cls(
            matches_0_7_days=matches_0_7_days or 0,
            matches_8_30_days=matches_8_30_days or 0,
            matches_31_90_days=matches_31_90_days or 0,
            total_matches_90_days=total_matches_90_days,
            last_match_at=cls._coerce_optional_integer(
                data.get("last_match_at")
            ),
            days_since_last_match=cls._coerce_optional_integer(
                data.get("days_since_last_match")
            ),
            history_complete=cls._coerce_boolean(
                history_complete_value
            ),
        )

    @classmethod
    def empty(
        cls,
        history_complete: bool = True,
    ) -> ActivityRecord:
        return cls(
            matches_0_7_days=0,
            matches_8_30_days=0,
            matches_31_90_days=0,
            total_matches_90_days=0,
            last_match_at=None,
            days_since_last_match=None,
            history_complete=history_complete,
        )

    @property
    def has_activity(self) -> bool:
        return self.total_matches_90_days > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "matches_0_7_days": self.matches_0_7_days,
            "matches_8_30_days": self.matches_8_30_days,
            "matches_31_90_days": self.matches_31_90_days,
            "total_matches_90_days": self.total_matches_90_days,
            "last_match_at": self.last_match_at,
            "days_since_last_match": self.days_since_last_match,
            "history_complete": self.history_complete,
        }

    @staticmethod
    def _validate_non_negative_integer(
        value: Any,
        field_name: str,
    ) -> int:
        integer = ActivityRecord._coerce_optional_integer(
            value
        )

        if integer is None:
            raise ValueError(
                f"{field_name} cannot be None."
            )

        if integer < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return integer

    @staticmethod
    def _validate_optional_non_negative_integer(
        value: Any,
        field_name: str,
    ) -> int | None:
        integer = ActivityRecord._coerce_optional_integer(
            value
        )

        if integer is None:
            return None

        if integer < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return integer

    @staticmethod
    def _validate_boolean(
        value: Any,
        field_name: str,
    ) -> bool:
        try:
            return ActivityRecord._coerce_boolean(
                value
            )

        except ValueError as error:
            raise ValueError(
                f"{field_name} must be boolean."
            ) from error

    @staticmethod
    def _coerce_optional_integer(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                "Boolean values cannot be converted to integers."
            )

        text = str(value).strip()

        if not text:
            return None

        try:
            number = float(
                text.replace(",", ".")
            )

        except ValueError as error:
            raise ValueError(
                f"Expected an integer, received {value!r}."
            ) from error

        if not number.is_integer():
            raise ValueError(
                f"Expected an integer, received {value!r}."
            )

        return int(number)

    @staticmethod
    def _coerce_boolean(
        value: Any,
    ) -> bool:
        if isinstance(value, bool):
            return value

        if value is None:
            return True

        if isinstance(value, (int, float)):
            if value == 1:
                return True

            if value == 0:
                return False

        text = str(value).strip().casefold()

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
            f"Expected a boolean value, received {value!r}."
        )


@dataclass(slots=True)
class PlayerRecord:
    """
    Registro intermedio generado por el scraper.

    Representa los datos extraídos y normalizados antes de convertirlos
    en un objeto Player mediante el importador CSV.

    team_number:
        Número de equipo asignado manualmente al jugador.

        Es opcional porque el producto admite dos modos:

            - Equipos generados automáticamente.
            - Equipos predeterminados que solo deben evaluarse.

        Esta clase solo comprueba que sea un entero positivo. El rango
        permitido según el evento se validará posteriormente.
    """

    nickname: str

    profile_url: str | None = None
    steam_id: str | None = None
    faceit_url: str | None = None
    csstats_url: str | None = None

    elo: int | None = None
    faceit_level: int | None = None

    kd: float | None = None
    rating: float | None = None
    adr: float | None = None
    kpr: float | None = None
    dpr: float | None = None

    hs: float | None = None
    kast: float | None = None
    winrate: float | None = None
    recent_winrate: float | None = None
    clutch: float | None = None

    matches: int | None = None

    activity: ActivityRecord | Mapping[str, Any] | None = None

    banned_matches_percentage: float | None = None

    role: str | None = None
    seed: int | None = None

    team_number: int | None = None

    source: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        self.nickname = self._required_string(
            self.nickname,
            "nickname",
        )

        self.profile_url = self._optional_string(
            self.profile_url
        )

        self.steam_id = self._optional_string(
            self.steam_id
        )

        self.faceit_url = self._optional_string(
            self.faceit_url
        )

        self.csstats_url = self._optional_string(
            self.csstats_url
        )

        self.role = self._optional_string(
            self.role
        )

        self.source = self._optional_string(
            self.source
        )

        self.error = self._optional_string(
            self.error
        )

        self.elo = self._optional_integer(
            self.elo,
            "elo",
            minimum=0,
        )

        self.faceit_level = self._optional_integer(
            self.faceit_level,
            "faceit_level",
            minimum=0,
            maximum=10,
        )

        self.matches = self._optional_integer(
            self.matches,
            "matches",
            minimum=0,
        )

        self.seed = self._optional_integer(
            self.seed,
            "seed",
            minimum=1,
        )

        self.team_number = self._optional_integer(
            self.team_number,
            "team_number",
            minimum=1,
        )

        self.kd = self._optional_float(
            self.kd,
            "kd",
            minimum=0.0,
        )

        self.rating = self._optional_float(
            self.rating,
            "rating",
            minimum=0.0,
        )

        self.adr = self._optional_float(
            self.adr,
            "adr",
            minimum=0.0,
        )

        self.kpr = self._optional_float(
            self.kpr,
            "kpr",
            minimum=0.0,
        )

        self.dpr = self._optional_float(
            self.dpr,
            "dpr",
            minimum=0.0,
        )

        self.hs = self._optional_percentage(
            self.hs,
            "hs",
        )

        self.kast = self._optional_percentage(
            self.kast,
            "kast",
        )

        self.winrate = self._optional_percentage(
            self.winrate,
            "winrate",
        )

        self.recent_winrate = self._optional_percentage(
            self.recent_winrate,
            "recent_winrate",
        )

        self.clutch = self._optional_percentage(
            self.clutch,
            "clutch",
        )

        self.banned_matches_percentage = (
            self._optional_percentage(
                self.banned_matches_percentage,
                "banned_matches_percentage",
            )
        )

        if isinstance(
            self.activity,
            Mapping,
        ):
            self.activity = ActivityRecord.from_mapping(
                self.activity
            )

        elif (
            self.activity is not None
            and not isinstance(
                self.activity,
                ActivityRecord,
            )
        ):
            raise TypeError(
                "activity must be an ActivityRecord, "
                "mapping or None."
            )

    @property
    def is_valid(self) -> bool:
        """
        Un registro es válido cuando no contiene error de scraping.
        """
        return self.error is None

    @property
    def identity(self) -> str:
        """
        Devuelve una identidad estable para detectar duplicados.
        """
        if self.steam_id:
            return (
                "steam:"
                f"{self.steam_id.strip().casefold()}"
            )

        return (
            "nickname:"
            f"{self.nickname.casefold()}"
        )

    @property
    def effective_profile_url(self) -> str | None:
        return (
            self.csstats_url
            or self.profile_url
            or self.faceit_url
        )

    @property
    def has_preassigned_team(self) -> bool:
        """
        Indica si el jugador tiene equipo predeterminado.
        """
        return self.team_number is not None

    @property
    def matches_0_7_days(self) -> int | None:
        if self.activity is None:
            return None

        return self.activity.matches_0_7_days

    @property
    def matches_8_30_days(self) -> int | None:
        if self.activity is None:
            return None

        return self.activity.matches_8_30_days

    @property
    def matches_31_90_days(self) -> int | None:
        if self.activity is None:
            return None

        return self.activity.matches_31_90_days

    @property
    def total_matches_90_days(self) -> int | None:
        if self.activity is None:
            return None

        return self.activity.total_matches_90_days

    @property
    def last_match_at(self) -> int | None:
        if self.activity is None:
            return None

        return self.activity.last_match_at

    @property
    def days_since_last_match(self) -> int | None:
        if self.activity is None:
            return None

        return self.activity.days_since_last_match

    @property
    def activity_history_complete(self) -> bool | None:
        if self.activity is None:
            return None

        return self.activity.history_complete

    def as_dict(
        self,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable.

        ActivityRecord se conserva anidado dentro de `activity`.
        """
        data = asdict(
            self
        )

        if not exclude_none:
            return data

        return self._remove_none_recursively(
            data
        )

    def to_csv_row(self) -> dict[str, Any]:
        """
        Devuelve una fila plana compatible con el importador CSV.

        La columna Team conserva la asignación predeterminada.
        """
        return {
            "Nick": self.nickname,
            "SteamID": self.steam_id,
            "ProfileURL": self.profile_url,
            "FaceitURL": self.faceit_url,
            "CssStatsURL": self.csstats_url,

            "ELO": self.elo,
            "FaceitLevel": self.faceit_level,

            "KD": self.kd,
            "Rating": self.rating,
            "ADR": self.adr,
            "KPR": self.kpr,
            "DPR": self.dpr,
            "HS": self.hs,
            "KAST": self.kast,
            "Winrate": self.winrate,
            "RecentWinrate": self.recent_winrate,
            "Clutch": self.clutch,

            "Matches": self.matches,

            "Matches0_7Days": self.matches_0_7_days,
            "Matches8_30Days": self.matches_8_30_days,
            "Matches31_90Days": self.matches_31_90_days,
            "TotalMatches90Days": self.total_matches_90_days,
            "LastMatchAt": self.last_match_at,
            "DaysSinceLastMatch": self.days_since_last_match,
            "ActivityHistoryComplete": (
                self.activity_history_complete
            ),

            "BannedMatchesPercentage": (
                self.banned_matches_percentage
            ),

            "Role": self.role,
            "Seed": self.seed,
            "Team": self.team_number,

            "Source": self.source,
            "Error": self.error,
        }

    @classmethod
    def failed(
        cls,
        nickname: str,
        error: str,
        profile_url: str | None = None,
        source: str | None = None,
        seed: int | None = None,
        team_number: int | None = None,
    ) -> PlayerRecord:
        """
        Construye un registro que representa un error de scraping.

        Conserva Seed y Team para que el fichero de errores permita
        localizar correctamente al jugador dentro del evento.
        """
        return cls(
            nickname=nickname,
            profile_url=profile_url,
            source=source,
            error=error,
            seed=seed,
            team_number=team_number,
        )

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> PlayerRecord:
        """
        Construye un PlayerRecord desde un diccionario.

        Admite tanto nombres internos como nombres habituales del CSV.
        """
        if data is None:
            raise ValueError(
                "data cannot be None."
            )

        if not isinstance(data, Mapping):
            raise TypeError(
                "data must be a mapping."
            )

        activity_data = data.get(
            "activity"
        )

        if activity_data is None:
            activity_data = {
                "matches_0_7_days": cls._first_value(
                    data,
                    "matches_0_7_days",
                    "Matches0_7Days",
                ),
                "matches_8_30_days": cls._first_value(
                    data,
                    "matches_8_30_days",
                    "Matches8_30Days",
                ),
                "matches_31_90_days": cls._first_value(
                    data,
                    "matches_31_90_days",
                    "Matches31_90Days",
                ),
                "total_matches_90_days": cls._first_value(
                    data,
                    "total_matches_90_days",
                    "TotalMatches90Days",
                ),
                "last_match_at": cls._first_value(
                    data,
                    "last_match_at",
                    "LastMatchAt",
                ),
                "days_since_last_match": cls._first_value(
                    data,
                    "days_since_last_match",
                    "DaysSinceLastMatch",
                ),
                "history_complete": cls._first_value(
                    data,
                    "activity_history_complete",
                    "history_complete",
                    "ActivityHistoryComplete",
                ),
            }

        faceit_level = cls._first_value(
            data,
            "faceit_level",
            "level",
            "FaceitLevel",
        )

        team_number = cls._first_value(
            data,
            "team_number",
            "team",
            "team_id",
            "team_number",
            "Team",
            "TeamNumber",
            "TeamId",
            "AssignedTeam",
            "Equipo",
        )

        return cls(
            nickname=(
                cls._first_value(
                    data,
                    "nickname",
                    "nick",
                    "Nick",
                )
            ),
            profile_url=cls._first_value(
                data,
                "profile_url",
                "ProfileURL",
            ),
            steam_id=cls._first_value(
                data,
                "steam_id",
                "SteamID",
            ),
            faceit_url=cls._first_value(
                data,
                "faceit_url",
                "FaceitURL",
            ),
            csstats_url=cls._first_value(
                data,
                "csstats_url",
                "CssStatsURL",
            ),
            elo=cls._first_value(
                data,
                "elo",
                "ELO",
            ),
            faceit_level=faceit_level,
            kd=cls._first_value(
                data,
                "kd",
                "KD",
            ),
            rating=cls._first_value(
                data,
                "rating",
                "Rating",
            ),
            adr=cls._first_value(
                data,
                "adr",
                "ADR",
            ),
            kpr=cls._first_value(
                data,
                "kpr",
                "KPR",
            ),
            dpr=cls._first_value(
                data,
                "dpr",
                "DPR",
            ),
            hs=cls._first_value(
                data,
                "hs",
                "HS",
            ),
            kast=cls._first_value(
                data,
                "kast",
                "KAST",
            ),
            winrate=cls._first_value(
                data,
                "winrate",
                "Winrate",
            ),
            recent_winrate=cls._first_value(
                data,
                "recent_winrate",
                "RecentWinrate",
            ),
            clutch=cls._first_value(
                data,
                "clutch",
                "Clutch",
            ),
            matches=cls._first_value(
                data,
                "matches",
                "Matches",
            ),
            activity=ActivityRecord.from_mapping(
                activity_data
            ),
            banned_matches_percentage=cls._first_value(
                data,
                "banned_matches_percentage",
                "BannedMatchesPercentage",
            ),
            role=cls._first_value(
                data,
                "role",
                "Role",
            ),
            seed=cls._first_value(
                data,
                "seed",
                "Seed",
            ),
            team_number=team_number,
            source=cls._first_value(
                data,
                "source",
                "Source",
            ),
            error=cls._first_value(
                data,
                "error",
                "Error",
            ),
        )

    @staticmethod
    def _first_value(
        data: Mapping[str, Any],
        *keys: str,
    ) -> Any:
        """
        Devuelve el primer valor disponible entre varias claves.

        Un valor vacío no bloquea la búsqueda de los siguientes alias.
        """
        for key in keys:
            if key not in data:
                continue

            value = data.get(
                key
            )

            if value is None:
                continue

            if isinstance(value, str) and not value.strip():
                continue

            return value

        return None

    @staticmethod
    def _required_string(
        value: Any,
        field_name: str,
    ) -> str:
        if value is None:
            raise ValueError(
                f"{field_name} is required."
            )

        normalized = str(
            value
        ).strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _optional_string(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None

    @staticmethod
    def _optional_integer(
        value: Any,
        field_name: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int | None:
        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} cannot be boolean."
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
                f"{field_name} must be numeric."
            ) from error

        if not number.is_integer():
            raise ValueError(
                f"{field_name} must be an integer."
            )

        integer = int(
            number
        )

        PlayerRecord._validate_range(
            value=integer,
            field_name=field_name,
            minimum=minimum,
            maximum=maximum,
        )

        return integer

    @staticmethod
    def _optional_float(
        value: Any,
        field_name: str,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} cannot be boolean."
            )

        text = str(
            value
        ).strip()

        if not text:
            return None

        text = (
            text
            .replace("%", "")
            .replace(",", ".")
        )

        try:
            number = float(
                text
            )

        except ValueError as error:
            raise ValueError(
                f"{field_name} must be numeric."
            ) from error

        PlayerRecord._validate_range(
            value=number,
            field_name=field_name,
            minimum=minimum,
            maximum=maximum,
        )

        return number

    @staticmethod
    def _optional_percentage(
        value: Any,
        field_name: str,
    ) -> float | None:
        return PlayerRecord._optional_float(
            value=value,
            field_name=field_name,
            minimum=0.0,
            maximum=100.0,
        )

    @staticmethod
    def _validate_range(
        value: float | int,
        field_name: str,
        minimum: float | int | None,
        maximum: float | int | None,
    ) -> None:
        if (
            minimum is not None
            and value < minimum
        ):
            raise ValueError(
                f"{field_name} cannot be lower than {minimum}."
            )

        if (
            maximum is not None
            and value > maximum
        ):
            raise ValueError(
                f"{field_name} cannot be greater than {maximum}."
            )

    @classmethod
    def _remove_none_recursively(
        cls,
        value: Any,
    ) -> Any:
        if isinstance(value, dict):
            return {
                key: cls._remove_none_recursively(
                    item
                )
                for key, item in value.items()
                if item is not None
            }

        if isinstance(value, list):
            return [
                cls._remove_none_recursively(
                    item
                )
                for item in value
                if item is not None
            ]

        return value

    def __repr__(self) -> str:
        status = (
            "valid"
            if self.is_valid
            else f"error={self.error!r}"
        )

        activity_matches = (
            self.activity.total_matches_90_days
            if self.activity is not None
            else None
        )

        return (
            f"{self.__class__.__name__}("
            f"nickname={self.nickname!r}, "
            f"steam_id={self.steam_id!r}, "
            f"seed={self.seed!r}, "
            f"team_number={self.team_number!r}, "
            f"matches_90_days={activity_matches!r}, "
            f"status={status})"
        )
