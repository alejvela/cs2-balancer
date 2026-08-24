from __future__ import annotations

import math
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from numbers import Real
from typing import Any


@dataclass(frozen=True, slots=True)
class ActivityStatistics:
    """
    Resume la actividad competitiva reciente de un jugador.

    Las ventanas son independientes para evitar contar varias veces
    una misma partida:

        matches_0_7_days:
            Partidas terminadas durante los últimos 7 días.

        matches_8_30_days:
            Partidas terminadas hace más de 7 días y hasta 30 días.

        matches_31_90_days:
            Partidas terminadas hace más de 30 días y hasta 90 días.

    También conserva:

        total_matches_90_days:
            Total de partidas únicas durante la ventana completa.

        last_match_at:
            Timestamp Unix en segundos de la última partida terminada.

        days_since_last_match:
            Días completos transcurridos desde la última partida.

    Esta clase no calcula todavía la penalización del Power Score.
    Solo representa y extrae los datos de actividad.
    """

    matches_0_7_days: int = 0
    matches_8_30_days: int = 0
    matches_31_90_days: int = 0

    total_matches_90_days: int = 0

    last_match_at: int | None = None
    days_since_last_match: int | None = None

    history_complete: bool = True

    WINDOW_7_DAYS_SECONDS = 7 * 24 * 60 * 60
    WINDOW_30_DAYS_SECONDS = 30 * 24 * 60 * 60
    WINDOW_90_DAYS_SECONDS = 90 * 24 * 60 * 60

    def __post_init__(self) -> None:
        integer_fields = {
            "matches_0_7_days": self.matches_0_7_days,
            "matches_8_30_days": self.matches_8_30_days,
            "matches_31_90_days": self.matches_31_90_days,
            "total_matches_90_days": self.total_matches_90_days,
        }

        for field_name, value in integer_fields.items():
            self._validate_non_negative_integer(
                value=value,
                field_name=field_name,
            )

        if self.last_match_at is not None:
            self._validate_non_negative_integer(
                value=self.last_match_at,
                field_name="last_match_at",
            )

        if self.days_since_last_match is not None:
            self._validate_non_negative_integer(
                value=self.days_since_last_match,
                field_name="days_since_last_match",
            )

        if not isinstance(self.history_complete, bool):
            raise TypeError(
                "history_complete must be a boolean."
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
    def from_history(
        cls,
        history_items: Iterable[Mapping[str, Any]],
        reference_timestamp: int | None = None,
        history_complete: bool = True,
    ) -> ActivityStatistics:
        """
        Construye las estadísticas a partir del historial de FACEIT.

        Las partidas se deduplican mediante match_id. Cuando no existe
        match_id, se utiliza una identidad derivada de la fecha y la
        posición del elemento.

        Solo se cuentan partidas con finished_at válido. Si no existe,
        se utiliza started_at como fallback.
        """
        if history_items is None:
            raise ValueError(
                "history_items cannot be None."
            )

        now_timestamp = cls._resolve_reference_timestamp(
            reference_timestamp
        )

        minimum_timestamp = (
            now_timestamp
            - cls.WINDOW_90_DAYS_SECONDS
        )

        unique_matches: dict[str, int] = {}

        for index, item in enumerate(
            history_items,
            start=1,
        ):
            if not isinstance(item, Mapping):
                continue

            match_timestamp = cls._extract_match_timestamp(
                item
            )

            if match_timestamp is None:
                continue

            # Ignoramos fechas futuras claramente inconsistentes.
            if match_timestamp > now_timestamp:
                continue

            # El historial puede contener elementos anteriores si la
            # API o la paginación devolvieran una ventana más amplia.
            if match_timestamp < minimum_timestamp:
                continue

            match_id = cls._optional_text(
                item.get("match_id")
            )

            identity = (
                f"id:{match_id}"
                if match_id is not None
                else (
                    f"timestamp:{match_timestamp}:"
                    f"position:{index}"
                )
            )

            existing_timestamp = unique_matches.get(
                identity
            )

            if (
                existing_timestamp is None
                or match_timestamp > existing_timestamp
            ):
                unique_matches[
                    identity
                ] = match_timestamp

        timestamps = sorted(
            unique_matches.values(),
            reverse=True,
        )

        matches_0_7_days = 0
        matches_8_30_days = 0
        matches_31_90_days = 0

        for match_timestamp in timestamps:
            age_seconds = (
                now_timestamp
                - match_timestamp
            )

            if age_seconds <= cls.WINDOW_7_DAYS_SECONDS:
                matches_0_7_days += 1

            elif age_seconds <= cls.WINDOW_30_DAYS_SECONDS:
                matches_8_30_days += 1

            elif age_seconds <= cls.WINDOW_90_DAYS_SECONDS:
                matches_31_90_days += 1

        last_match_at = (
            timestamps[0]
            if timestamps
            else None
        )

        days_since_last_match = (
            max(
                0,
                (
                    now_timestamp
                    - last_match_at
                )
                // (24 * 60 * 60),
            )
            if last_match_at is not None
            else None
        )

        return cls(
            matches_0_7_days=matches_0_7_days,
            matches_8_30_days=matches_8_30_days,
            matches_31_90_days=matches_31_90_days,
            total_matches_90_days=len(timestamps),
            last_match_at=last_match_at,
            days_since_last_match=(
                int(days_since_last_match)
                if days_since_last_match is not None
                else None
            ),
            history_complete=history_complete,
        )

    @classmethod
    def empty(
        cls,
        history_complete: bool = True,
    ) -> ActivityStatistics:
        """
        Crea unas estadísticas sin actividad encontrada.
        """
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
    def last_match_datetime(
        self,
    ) -> datetime | None:
        """
        Devuelve la fecha de la última partida en UTC.
        """
        if self.last_match_at is None:
            return None

        return datetime.fromtimestamp(
            self.last_match_at,
            tz=UTC,
        )

    @property
    def last_match_iso(
        self,
    ) -> str | None:
        """
        Devuelve la fecha en formato ISO 8601.
        """
        last_match_datetime = (
            self.last_match_datetime
        )

        if last_match_datetime is None:
            return None

        return last_match_datetime.isoformat()

    @property
    def has_recent_activity(
        self,
    ) -> bool:
        return self.total_matches_90_days > 0

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable.
        """
        return {
            "matches_0_7_days": self.matches_0_7_days,
            "matches_8_30_days": self.matches_8_30_days,
            "matches_31_90_days": self.matches_31_90_days,
            "total_matches_90_days": self.total_matches_90_days,
            "last_match_at": self.last_match_at,
            "last_match_iso": self.last_match_iso,
            "days_since_last_match": (
                self.days_since_last_match
            ),
            "history_complete": self.history_complete,
        }

    @staticmethod
    def _extract_match_timestamp(
        item: Mapping[str, Any],
    ) -> int | None:
        """
        Obtiene finished_at y utiliza started_at como fallback.
        """
        for field_name in (
            "finished_at",
            "started_at",
        ):
            timestamp = ActivityStatistics._optional_timestamp(
                item.get(field_name)
            )

            if timestamp is not None:
                return timestamp

        return None

    @staticmethod
    def _optional_timestamp(
        value: Any,
    ) -> int | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, Real):
            numeric_value = float(value)

        else:
            text = str(value).strip()

            if not text:
                return None

            try:
                numeric_value = float(text)

            except ValueError:
                return None

        if not math.isfinite(numeric_value):
            return None

        if numeric_value <= 0:
            return None

        timestamp = int(
            numeric_value
        )

        # Protección por si alguna respuesta utilizara milisegundos.
        if timestamp > 10_000_000_000:
            timestamp //= 1000

        return timestamp

    @staticmethod
    def _resolve_reference_timestamp(
        value: int | None,
    ) -> int:
        if value is None:
            return int(
                time.time()
            )

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                "reference_timestamp must be an integer or None."
            )

        if value <= 0:
            raise ValueError(
                "reference_timestamp must be greater than zero."
            )

        return value

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(value).strip()

        return text or None

    @staticmethod
    def _validate_non_negative_integer(
        value: int,
        field_name: str,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
        ):
            raise TypeError(
                f"{field_name} must be an integer."
            )

        if value < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )
