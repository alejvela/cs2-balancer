from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any

from models.player import Player


@dataclass(
    frozen=True,
    slots=True,
)
class ActivityEvaluation:
    """
    Resultado completo de la evaluación de actividad.

    activity_score:
        Actividad objetiva del jugador entre 0 y 1.

        Este valor NO depende del nivel FACEIT.

    base_activity_factor:
        Factor que correspondería al jugador si todos los niveles
        sufrieran la misma penalización.

    level_penalty_strength:
        Multiplicador utilizado para suavizar o endurecer la pérdida
        de Power según el nivel FACEIT.

    activity_factor:
        Factor final aplicado al Power después del ajuste por nivel.

    adjusted_power:
        Power final utilizado por el balanceador.
    """

    activity_score: float

    base_activity_factor: float

    level_penalty_strength: float

    activity_factor: float

    base_power: float

    adjusted_power: float

    matches_0_7_days: int | None = None

    matches_8_30_days: int | None = None

    matches_31_90_days: int | None = None

    total_matches_90_days: int | None = None

    days_since_last_match: int | None = None

    history_complete: bool | None = None

    faceit_level: int | None = None

    @property
    def power_penalty(
        self,
    ) -> float:
        return max(
            0.0,
            (
                self.base_power
                - self.adjusted_power
            ),
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
        return (
            self.activity_score
            * 100.0
        )

    @property
    def activity_factor_percentage(
        self,
    ) -> float:
        return (
            self.activity_factor
            * 100.0
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "activity_score": (
                self.activity_score
            ),

            "activity_percentage": (
                self.activity_percentage
            ),

            "base_activity_factor": (
                self.base_activity_factor
            ),

            "level_penalty_strength": (
                self.level_penalty_strength
            ),

            "activity_factor": (
                self.activity_factor
            ),

            "activity_factor_percentage": (
                self.activity_factor_percentage
            ),

            "faceit_level": (
                self.faceit_level
            ),

            "base_power": (
                self.base_power
            ),

            "adjusted_power": (
                self.adjusted_power
            ),

            "power_penalty": (
                self.power_penalty
            ),

            "power_penalty_percentage": (
                self.power_penalty_percentage
            ),

            "matches_0_7_days": (
                self.matches_0_7_days
            ),

            "matches_8_30_days": (
                self.matches_8_30_days
            ),

            "matches_31_90_days": (
                self.matches_31_90_days
            ),

            "total_matches_90_days": (
                self.total_matches_90_days
            ),

            "days_since_last_match": (
                self.days_since_last_match
            ),

            "history_complete": (
                self.history_complete
            ),
        }


class ActivityFactorModel:
    """
    Calcula el impacto de la actividad reciente sobre el Power.

    La actividad se divide en tres ventanas:

        0-7 días
            Peso: 50 %
            Objetivo: 10 partidas

        8-30 días
            Peso: 30 %
            Objetivo: 20 partidas

        31-90 días
            Peso: 20 %
            Objetivo: 30 partidas

    Primero se calcula un activity_score entre 0 y 1.

    Después:

        base_activity_factor =
            minimum_factor
            + activity_score
              * (1 - minimum_factor)

    Finalmente se adapta la PENALIZACIÓN al nivel FACEIT:

        base_penalty =
            1 - base_activity_factor

        adjusted_penalty =
            base_penalty
            * level_penalty_strength

        activity_factor =
            1 - adjusted_penalty

    De esta manera el nivel FACEIT NO altera la actividad observada.

    Únicamente modifica cuánto afecta la inactividad al Power.

    Ejemplo con activity_score = 0:

        base_activity_factor = 0.75

        LVL 3:
            strength ≈ 1.15
            factor ≈ 0.71

        LVL 6:
            strength = 1.00
            factor = 0.75

        LVL 8:
            strength ≈ 0.85
            factor ≈ 0.79

        LVL 10:
            strength ≈ 0.80
            factor = 0.80
    """

    DEFAULT_MINIMUM_FACTOR = 0.75

    DEFAULT_WEIGHT_0_7 = 0.50
    DEFAULT_WEIGHT_8_30 = 0.30
    DEFAULT_WEIGHT_31_90 = 0.20

    DEFAULT_TARGET_0_7 = 10
    DEFAULT_TARGET_8_30 = 20
    DEFAULT_TARGET_31_90 = 30

    DEFAULT_UNKNOWN_LEVEL_STRENGTH = 1.00

    LEVEL_PENALTY_STRENGTH = {
        1: 1.18,
        2: 1.16,
        3: 1.14,
        4: 1.10,
        5: 1.05,
        6: 1.00,
        7: 0.94,
        8: 0.88,
        9: 0.84,
        10: 0.80,
    }

    def __init__(
        self,
        minimum_factor: float = DEFAULT_MINIMUM_FACTOR,
        weight_0_7: float = DEFAULT_WEIGHT_0_7,
        weight_8_30: float = DEFAULT_WEIGHT_8_30,
        weight_31_90: float = DEFAULT_WEIGHT_31_90,
        target_0_7: int = DEFAULT_TARGET_0_7,
        target_8_30: int = DEFAULT_TARGET_8_30,
        target_31_90: int = DEFAULT_TARGET_31_90,
    ) -> None:
        self._minimum_factor = (
            self._validate_factor(
                minimum_factor,
                "minimum_factor",
            )
        )

        self._weight_0_7 = (
            self._validate_weight(
                weight_0_7,
                "weight_0_7",
            )
        )

        self._weight_8_30 = (
            self._validate_weight(
                weight_8_30,
                "weight_8_30",
            )
        )

        self._weight_31_90 = (
            self._validate_weight(
                weight_31_90,
                "weight_31_90",
            )
        )

        total_weight = (
            self._weight_0_7
            + self._weight_8_30
            + self._weight_31_90
        )

        if abs(
            total_weight - 1.0
        ) > 1e-9:
            raise ValueError(
                "Activity weights must sum exactly 1.0. "
                f"Received: {total_weight:.6f}."
            )

        self._target_0_7 = (
            self._validate_positive_integer(
                target_0_7,
                "target_0_7",
            )
        )

        self._target_8_30 = (
            self._validate_positive_integer(
                target_8_30,
                "target_8_30",
            )
        )

        self._target_31_90 = (
            self._validate_positive_integer(
                target_31_90,
                "target_31_90",
            )
        )

    # ========================================================
    # API pública
    # ========================================================

    def evaluate(
        self,
        player: Player,
        base_power: float,
    ) -> ActivityEvaluation:
        """
        Calcula el impacto de la actividad sobre el Power.

        Args:
            player:
                Jugador evaluado.

            base_power:
                Power calculado antes de aplicar actividad.

        Returns:
            ActivityEvaluation.
        """
        if player is None:
            raise ValueError(
                "player cannot be None."
            )

        validated_power = (
            self._validate_power(
                base_power
            )
        )

        activity = getattr(
            player,
            "activity",
            None,
        )

        level = self._get_faceit_level(
            player
        )

        if activity is None:
            return self._build_neutral_evaluation(
                base_power=validated_power,
                faceit_level=level,
            )

        matches_0_7 = (
            self._optional_non_negative_integer(
                getattr(
                    activity,
                    "matches_0_7_days",
                    None,
                )
            )
        )

        matches_8_30 = (
            self._optional_non_negative_integer(
                getattr(
                    activity,
                    "matches_8_30_days",
                    None,
                )
            )
        )

        matches_31_90 = (
            self._optional_non_negative_integer(
                getattr(
                    activity,
                    "matches_31_90_days",
                    None,
                )
            )
        )

        total_matches_90 = (
            self._optional_non_negative_integer(
                getattr(
                    activity,
                    "total_matches_90_days",
                    None,
                )
            )
        )

        days_since_last_match = (
            self._optional_non_negative_integer(
                getattr(
                    activity,
                    "days_since_last_match",
                    None,
                )
            )
        )

        history_complete = (
            self._optional_boolean(
                getattr(
                    activity,
                    "history_complete",
                    None,
                )
            )
        )

        has_window_data = any(
            value is not None
            for value in (
                matches_0_7,
                matches_8_30,
                matches_31_90,
            )
        )

        if not has_window_data:
            return self._build_neutral_evaluation(
                base_power=validated_power,
                faceit_level=level,
                total_matches_90_days=(
                    total_matches_90
                ),
                days_since_last_match=(
                    days_since_last_match
                ),
                history_complete=(
                    history_complete
                ),
            )

        activity_score = (
            self._calculate_activity_score(
                matches_0_7=(
                    matches_0_7 or 0
                ),
                matches_8_30=(
                    matches_8_30 or 0
                ),
                matches_31_90=(
                    matches_31_90 or 0
                ),
            )
        )

        base_activity_factor = (
            self._activity_score_to_factor(
                activity_score
            )
        )

        penalty_strength = (
            self._level_penalty_strength(
                level
            )
        )

        final_activity_factor = (
            self._apply_level_adjustment(
                base_activity_factor=(
                    base_activity_factor
                ),
                penalty_strength=(
                    penalty_strength
                ),
            )
        )

        adjusted_power = (
            validated_power
            * final_activity_factor
        )

        return ActivityEvaluation(
            activity_score=(
                activity_score
            ),

            base_activity_factor=(
                base_activity_factor
            ),

            level_penalty_strength=(
                penalty_strength
            ),

            activity_factor=(
                final_activity_factor
            ),

            base_power=(
                validated_power
            ),

            adjusted_power=(
                adjusted_power
            ),

            matches_0_7_days=(
                matches_0_7
            ),

            matches_8_30_days=(
                matches_8_30
            ),

            matches_31_90_days=(
                matches_31_90
            ),

            total_matches_90_days=(
                total_matches_90
            ),

            days_since_last_match=(
                days_since_last_match
            ),

            history_complete=(
                history_complete
            ),

            faceit_level=(
                level
            ),
        )

    def factor(
        self,
        player: Player,
    ) -> float:
        """
        Devuelve exclusivamente el factor de actividad.

        Se utiliza un Power ficticio de 100 porque el factor es
        independiente del Power base.
        """
        return self.evaluate(
            player=player,
            base_power=100.0,
        ).activity_factor

    # ========================================================
    # Activity Score
    # ========================================================

    def _calculate_activity_score(
        self,
        matches_0_7: int,
        matches_8_30: int,
        matches_31_90: int,
    ) -> float:
        score_0_7 = (
            self._window_score(
                matches=matches_0_7,
                target=self._target_0_7,
            )
        )

        score_8_30 = (
            self._window_score(
                matches=matches_8_30,
                target=self._target_8_30,
            )
        )

        score_31_90 = (
            self._window_score(
                matches=matches_31_90,
                target=self._target_31_90,
            )
        )

        score = (
            score_0_7
            * self._weight_0_7

            + score_8_30
            * self._weight_8_30

            + score_31_90
            * self._weight_31_90
        )

        return self._clamp(
            score,
            minimum=0.0,
            maximum=1.0,
        )

    @staticmethod
    def _window_score(
        matches: int,
        target: int,
    ) -> float:
        if matches <= 0:
            return 0.0

        return min(
            1.0,
            (
                float(matches)
                / float(target)
            ),
        )

    # ========================================================
    # Conversión actividad → factor
    # ========================================================

    def _activity_score_to_factor(
        self,
        activity_score: float,
    ) -> float:
        """
        Convierte 0-1 de actividad al factor base.

        Con minimum_factor=0.75:

            activity 0.00 -> factor 0.75
            activity 0.50 -> factor 0.875
            activity 1.00 -> factor 1.00
        """
        return (
            self._minimum_factor
            + (
                activity_score
                * (
                    1.0
                    - self._minimum_factor
                )
            )
        )

    # ========================================================
    # Ajuste por nivel FACEIT
    # ========================================================

    @classmethod
    def _level_penalty_strength(
        cls,
        level: int | None,
    ) -> float:
        """
        Devuelve cuánto afecta la inactividad según el nivel.

        > 1:
            endurece la penalización.

        = 1:
            penalización normal.

        < 1:
            suaviza la penalización.
        """
        if level is None:
            return (
                cls.DEFAULT_UNKNOWN_LEVEL_STRENGTH
            )

        return cls.LEVEL_PENALTY_STRENGTH.get(
            level,
            cls.DEFAULT_UNKNOWN_LEVEL_STRENGTH,
        )

    @staticmethod
    def _apply_level_adjustment(
        base_activity_factor: float,
        penalty_strength: float,
    ) -> float:
        """
        Ajusta únicamente la parte de Power perdida.

        Ejemplo:

            base factor = 0.80

            pérdida base = 20 %

            strength 1.15:
                pérdida = 23 %
                factor = 77 %

            strength 0.80:
                pérdida = 16 %
                factor = 84 %
        """
        base_penalty = max(
            0.0,
            (
                1.0
                - base_activity_factor
            ),
        )

        adjusted_penalty = (
            base_penalty
            * penalty_strength
        )

        final_factor = (
            1.0
            - adjusted_penalty
        )

        return ActivityFactorModel._clamp(
            final_factor,
            minimum=0.0,
            maximum=1.0,
        )

    # ========================================================
    # FACEIT Level
    # ========================================================

    @staticmethod
    def _get_faceit_level(
        player: Player,
    ) -> int | None:
        value = getattr(
            player,
            "level",
            None,
        )

        if value is None:
            value = getattr(
                player,
                "faceit_level",
                None,
            )

        if (
            value is None
            or isinstance(
                value,
                bool,
            )
        ):
            return None

        try:
            level = int(
                float(value)
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if not 1 <= level <= 10:
            return None

        return level

    # ========================================================
    # Neutral fallback
    # ========================================================

    @classmethod
    def _build_neutral_evaluation(
        cls,
        base_power: float,
        faceit_level: int | None,
        total_matches_90_days: int | None = None,
        days_since_last_match: int | None = None,
        history_complete: bool | None = None,
    ) -> ActivityEvaluation:
        """
        Si no existe información suficiente de actividad NO se castiga
        al jugador.

        Falta de datos no significa inactividad.
        """
        return ActivityEvaluation(
            activity_score=1.0,

            base_activity_factor=1.0,

            level_penalty_strength=(
                cls._level_penalty_strength(
                    faceit_level
                )
            ),

            activity_factor=1.0,

            base_power=base_power,

            adjusted_power=base_power,

            total_matches_90_days=(
                total_matches_90_days
            ),

            days_since_last_match=(
                days_since_last_match
            ),

            history_complete=(
                history_complete
            ),

            faceit_level=(
                faceit_level
            ),
        )

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_factor(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                Real,
            )
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        numeric = float(
            value
        )

        if not 0.0 <= numeric <= 1.0:
            raise ValueError(
                f"{field_name} must be between 0 and 1."
            )

        return numeric

    @staticmethod
    def _validate_weight(
        value: Any,
        field_name: str,
    ) -> float:
        return (
            ActivityFactorModel._validate_factor(
                value=value,
                field_name=field_name,
            )
        )

    @staticmethod
    def _validate_positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                int,
            )
        ):
            raise TypeError(
                f"{field_name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return value

    @staticmethod
    def _validate_power(
        value: Any,
    ) -> float:
        if (
            isinstance(value, bool)
            or not isinstance(
                value,
                Real,
            )
        ):
            raise TypeError(
                "base_power must be numeric."
            )

        return max(
            0.0,
            float(value),
        )

    @staticmethod
    def _optional_non_negative_integer(
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

        if numeric < 0:
            return None

        return int(
            round(
                numeric
            )
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
            "true",
            "1",
            "yes",
            "si",
            "sí",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
        }:
            return False

        return None

    @staticmethod
    def _clamp(
        value: float,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(
                maximum,
                float(value),
            ),
        )

    # ========================================================
    # Propiedades
    # ========================================================

    @property
    def minimum_factor(
        self,
    ) -> float:
        return self._minimum_factor

    @property
    def weight_0_7(
        self,
    ) -> float:
        return self._weight_0_7

    @property
    def weight_8_30(
        self,
    ) -> float:
        return self._weight_8_30

    @property
    def weight_31_90(
        self,
    ) -> float:
        return self._weight_31_90

    @property
    def target_0_7(
        self,
    ) -> int:
        return self._target_0_7

    @property
    def target_8_30(
        self,
    ) -> int:
        return self._target_8_30

    @property
    def target_31_90(
        self,
    ) -> int:
        return self._target_31_90

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"minimum_factor={self._minimum_factor:.2f}, "
            f"weights=("
            f"{self._weight_0_7:.2f}, "
            f"{self._weight_8_30:.2f}, "
            f"{self._weight_31_90:.2f}), "
            f"targets=("
            f"{self._target_0_7}, "
            f"{self._target_8_30}, "
            f"{self._target_31_90}))"
        )
