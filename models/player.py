from __future__ import annotations

from collections.abc import Mapping
from numbers import Real
from typing import Any

from scrapers.player_record import ActivityRecord


class Player:
    """
    Representa a un jugador dentro del motor de balanceo.

    Contiene:

        - Identidad del jugador.
        - Estadísticas de FACEIT.
        - Nivel y ELO.
        - Actividad competitiva reciente.
        - Rol y seed.
        - Equipo predeterminado opcional.

    team_number:

        Número del equipo asignado manualmente al jugador.

        Puede ser None cuando el sistema debe generar los equipos
        automáticamente.

        Cuando contiene un valor, será utilizado por
        PreassignedTeamGenerator para agrupar a los jugadores.

        Player solo valida que sea un entero positivo. El rango
        concreto permitido, por ejemplo del 1 al 4, dependerá de la
        configuración del evento y se comprobará en el generador.
    """

    def __init__(
        self,
        nick: str,
        elo: int | None = None,
        level: int | None = None,
        kd: float | None = None,
        rating: float | None = None,
        adr: float | None = None,
        kpr: float | None = None,
        dpr: float | None = None,
        hs: float | None = None,
        kast: float | None = None,
        winrate: float | None = None,
        recent_winrate: float | None = None,
        clutch: float | None = None,
        matches: int | None = None,
        steam_id: str | None = None,
        role: str | None = None,
        seed: int | None = None,
        team_number: int | None = None,
        activity: ActivityRecord | Mapping[str, Any] | None = None,
        source: str | None = None,
        profile_url: str | None = None,
        faceit_url: str | None = None,
        csstats_url: str | None = None,
    ) -> None:
        self.nick = self._validate_required_text(
            value=nick,
            field_name="nick",
        )

        self.elo = self._validate_optional_integer(
            value=elo,
            field_name="elo",
            minimum=0,
        )

        self.level = self._validate_optional_integer(
            value=level,
            field_name="level",
            minimum=1,
            maximum=10,
        )

        self.kd = self._validate_optional_float(
            value=kd,
            field_name="kd",
            minimum=0.0,
        )

        self.rating = self._validate_optional_float(
            value=rating,
            field_name="rating",
            minimum=0.0,
        )

        self.adr = self._validate_optional_float(
            value=adr,
            field_name="adr",
            minimum=0.0,
        )

        self.kpr = self._validate_optional_float(
            value=kpr,
            field_name="kpr",
            minimum=0.0,
        )

        self.dpr = self._validate_optional_float(
            value=dpr,
            field_name="dpr",
            minimum=0.0,
        )

        self.hs = self._validate_optional_percentage(
            value=hs,
            field_name="hs",
        )

        self.kast = self._validate_optional_percentage(
            value=kast,
            field_name="kast",
        )

        self.winrate = self._validate_optional_percentage(
            value=winrate,
            field_name="winrate",
        )

        self.recent_winrate = self._validate_optional_percentage(
            value=recent_winrate,
            field_name="recent_winrate",
        )

        self.clutch = self._validate_optional_percentage(
            value=clutch,
            field_name="clutch",
        )

        self.matches = self._validate_optional_integer(
            value=matches,
            field_name="matches",
            minimum=0,
        )

        self.steam_id = self._validate_optional_text(
            steam_id
        )

        self.role = self._validate_optional_text(
            role
        )

        self.seed = self._validate_optional_integer(
            value=seed,
            field_name="seed",
            minimum=1,
        )

        self.team_number = self._validate_optional_integer(
            value=team_number,
            field_name="team_number",
            minimum=1,
        )

        self.activity = self._validate_activity(
            activity
        )

        self.source = self._validate_optional_text(
            source
        )

        self.profile_url = self._validate_optional_text(
            profile_url
        )

        self.faceit_url = self._validate_optional_text(
            faceit_url
        )

        self.csstats_url = self._validate_optional_text(
            csstats_url
        )

    # ========================================================
    # Identidad y aliases
    # ========================================================

    @property
    def nickname(
        self,
    ) -> str:
        """
        Alias de nick mantenido para compatibilidad.
        """
        return self.nick

    @property
    def faceit_elo(
        self,
    ) -> int | None:
        """
        Alias de elo mantenido para compatibilidad.
        """
        return self.elo

    @property
    def faceit_level(
        self,
    ) -> int | None:
        """
        Alias de level mantenido para compatibilidad.
        """
        return self.level

    @property
    def identity(
        self,
    ) -> str:
        """
        Devuelve una identidad estable para detectar duplicados.

        Prioridad:

            1. Steam ID.
            2. Nick normalizado.
        """
        if self.steam_id:
            return (
                "steam:"
                f"{self.steam_id.casefold()}"
            )

        return (
            "nick:"
            f"{self.nick.casefold()}"
        )

    @property
    def effective_profile_url(
        self,
    ) -> str | None:
        """
        Devuelve la URL de perfil disponible con mayor prioridad.
        """
        return (
            self.faceit_url
            or self.profile_url
            or self.csstats_url
        )

    # ========================================================
    # Equipo predeterminado
    # ========================================================

    @property
    def has_preassigned_team(
        self,
    ) -> bool:
        """
        Indica si el jugador tiene un equipo predeterminado.
        """
        return self.team_number is not None

    @property
    def assigned_team_number(
        self,
    ) -> int | None:
        """
        Alias descriptivo de team_number.

        Permite utilizar un nombre más explícito en futuras capas
        del producto sin romper la compatibilidad actual.
        """
        return self.team_number

    # ========================================================
    # Actividad
    # ========================================================

    @property
    def matches_0_7_days(
        self,
    ) -> int | None:
        if self.activity is None:
            return None

        return self.activity.matches_0_7_days

    @property
    def matches_8_30_days(
        self,
    ) -> int | None:
        if self.activity is None:
            return None

        return self.activity.matches_8_30_days

    @property
    def matches_31_90_days(
        self,
    ) -> int | None:
        if self.activity is None:
            return None

        return self.activity.matches_31_90_days

    @property
    def total_matches_90_days(
        self,
    ) -> int | None:
        if self.activity is None:
            return None

        return self.activity.total_matches_90_days

    @property
    def last_match_at(
        self,
    ) -> int | None:
        if self.activity is None:
            return None

        return self.activity.last_match_at

    @property
    def days_since_last_match(
        self,
    ) -> int | None:
        if self.activity is None:
            return None

        return self.activity.days_since_last_match

    @property
    def activity_history_complete(
        self,
    ) -> bool | None:
        if self.activity is None:
            return None

        return self.activity.history_complete

    @property
    def has_activity_data(
        self,
    ) -> bool:
        return self.activity is not None

    @property
    def has_recent_activity(
        self,
    ) -> bool:
        return (
            self.activity is not None
            and self.activity.total_matches_90_days > 0
        )

    # ========================================================
    # Validación
    # ========================================================

    @staticmethod
    def _validate_activity(
        value: ActivityRecord | Mapping[str, Any] | None,
    ) -> ActivityRecord | None:
        """
        Valida o construye el registro de actividad.
        """
        if value is None:
            return None

        if isinstance(
            value,
            ActivityRecord,
        ):
            return value

        if isinstance(
            value,
            Mapping,
        ):
            return ActivityRecord.from_mapping(
                value
            )

        raise TypeError(
            "activity must be an ActivityRecord, mapping or None."
        )

    @staticmethod
    def _validate_required_text(
        value: Any,
        field_name: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                f"{field_name} must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return normalized

    @staticmethod
    def _validate_optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        normalized = str(
            value
        ).strip()

        return normalized or None

    @staticmethod
    def _validate_optional_integer(
        value: Any,
        field_name: str,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int | None:
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{field_name} cannot be boolean."
            )

        if isinstance(
            value,
            int,
        ):
            integer = value

        elif isinstance(
            value,
            Real,
        ):
            numeric_value = float(
                value
            )

            if not numeric_value.is_integer():
                raise ValueError(
                    f"{field_name} must be an integer."
                )

            integer = int(
                numeric_value
            )

        else:
            text = str(
                value
            ).strip()

            if not text:
                return None

            try:
                numeric_value = float(
                    text.replace(",", ".")
                )

            except ValueError as error:
                raise ValueError(
                    f"{field_name} must be numeric."
                ) from error

            if not numeric_value.is_integer():
                raise ValueError(
                    f"{field_name} must be an integer."
                )

            integer = int(
                numeric_value
            )

        Player._validate_range(
            value=integer,
            field_name=field_name,
            minimum=minimum,
            maximum=maximum,
        )

        return integer

    @staticmethod
    def _validate_optional_float(
        value: Any,
        field_name: str,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(
            value,
            bool,
        ):
            raise TypeError(
                f"{field_name} cannot be boolean."
            )

        if isinstance(
            value,
            Real,
        ):
            numeric_value = float(
                value
            )

        else:
            text = str(
                value
            ).strip()

            if not text:
                return None

            try:
                numeric_value = float(
                    text
                    .replace("%", "")
                    .replace(",", ".")
                )

            except ValueError as error:
                raise ValueError(
                    f"{field_name} must be numeric."
                ) from error

        Player._validate_range(
            value=numeric_value,
            field_name=field_name,
            minimum=minimum,
            maximum=maximum,
        )

        return numeric_value

    @staticmethod
    def _validate_optional_percentage(
        value: Any,
        field_name: str,
    ) -> float | None:
        return Player._validate_optional_float(
            value=value,
            field_name=field_name,
            minimum=0.0,
            maximum=100.0,
        )

    @staticmethod
    def _validate_range(
        value: int | float,
        field_name: str,
        minimum: int | float | None,
        maximum: int | float | None,
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

    # ========================================================
    # Serialización
    # ========================================================

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable del jugador.
        """
        return {
            "nick": self.nick,
            "nickname": self.nickname,

            "steam_id": self.steam_id,

            "elo": self.elo,
            "level": self.level,

            "kd": self.kd,
            "rating": self.rating,
            "adr": self.adr,
            "kpr": self.kpr,
            "dpr": self.dpr,
            "hs": self.hs,
            "kast": self.kast,
            "winrate": self.winrate,
            "recent_winrate": self.recent_winrate,
            "clutch": self.clutch,
            "matches": self.matches,

            "role": self.role,
            "seed": self.seed,

            "team_number": self.team_number,
            "has_preassigned_team": (
                self.has_preassigned_team
            ),

            "activity": (
                self.activity.as_dict()
                if self.activity is not None
                else None
            ),

            "source": self.source,
            "profile_url": self.profile_url,
            "faceit_url": self.faceit_url,
            "csstats_url": self.csstats_url,
            "effective_profile_url": (
                self.effective_profile_url
            ),
        }

    def __repr__(
        self,
    ) -> str:
        matches_90_days = (
            self.activity.total_matches_90_days
            if self.activity is not None
            else None
        )

        return (
            f"{self.__class__.__name__}("
            f"nick={self.nick!r}, "
            f"elo={self.elo!r}, "
            f"level={self.level!r}, "
            f"seed={self.seed!r}, "
            f"team_number={self.team_number!r}, "
            f"matches_90_days={matches_90_days!r})"
        )
