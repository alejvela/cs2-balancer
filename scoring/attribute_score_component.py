from __future__ import annotations

from numbers import Real
from typing import Any

from models.player import Player
from optimizer.normalization.normalizer import Normalizer
from scoring.score_component import ScoreComponent


class AttributeScoreComponent(ScoreComponent):
    """
    Componente de puntuación basado en un atributo numérico de Player.

    Obtiene el valor del atributo configurado, lo transforma mediante
    un Normalizer y devuelve una puntuación entre 0 y 100.

    Ejemplos de atributos:

        - elo
        - kd
        - adr
        - kpr
        - hs
        - winrate

    El componente no contiene ningún peso. La ponderación pertenece
    exclusivamente al ScoringModel.
    """

    def __init__(
        self,
        name: str,
        attribute: str,
        normalizer: Normalizer,
        default_score: float = 0.0,
    ) -> None:
        self._name = self._validate_text(
            value=name,
            field_name="name",
        )

        self._attribute = self._validate_text(
            value=attribute,
            field_name="attribute",
        )

        if normalizer is None:
            raise ValueError(
                "normalizer cannot be None."
            )

        normalize_method = getattr(
            normalizer,
            "normalize",
            None,
        )

        if not callable(normalize_method):
            raise TypeError(
                "normalizer must provide a normalize() method."
            )

        if (
            isinstance(default_score, bool)
            or not isinstance(default_score, Real)
        ):
            raise TypeError(
                "default_score must be numeric."
            )

        self._normalizer = normalizer

        self._default_score = self._clamp_score(
            float(default_score)
        )

    @property
    def name(self) -> str:
        """
        Nombre con el que el componente aparecerá en PlayerEvaluation
        y en el diccionario de pesos de ScoringModel.
        """
        return self._name

    @property
    def attribute(self) -> str:
        """
        Nombre del atributo leído desde Player.
        """
        return self._attribute

    @property
    def normalizer(self) -> Normalizer:
        """
        Normalizador utilizado para convertir el valor a 0-100.
        """
        return self._normalizer

    @property
    def default_score(self) -> float:
        """
        Puntuación utilizada cuando el atributo no tiene valor.
        """
        return self._default_score

    def score(
        self,
        player: Player,
    ) -> float:
        """
        Devuelve la puntuación normalizada del atributo.

        Si el atributo no existe o su valor es None, devuelve
        `default_score`.
        """
        if player is None:
            raise ValueError(
                "player cannot be None."
            )

        value = self._get_value(player)

        if value is None:
            return self._default_score

        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                f"Player attribute '{self._attribute}' must be numeric, "
                f"but received {type(value).__name__}."
            )

        normalized_score = self._normalizer.normalize(
            float(value)
        )

        if (
            isinstance(normalized_score, bool)
            or not isinstance(normalized_score, Real)
        ):
            raise TypeError(
                f"Normalizer for component '{self._name}' "
                "must return a numeric value."
            )

        return self._clamp_score(
            float(normalized_score)
        )

    def has_value(
        self,
        player: Player,
    ) -> bool:
        """
        Indica si el jugador contiene un valor válido para el atributo.
        """
        if player is None:
            return False

        value = self._get_value(player)

        return (
            value is not None
            and not isinstance(value, bool)
            and isinstance(value, Real)
        )

    def raw_value(
        self,
        player: Player,
    ) -> float | None:
        """
        Devuelve el valor original del jugador sin normalizar.

        Es útil para informes y depuración.
        """
        if player is None:
            raise ValueError(
                "player cannot be None."
            )

        value = self._get_value(player)

        if value is None:
            return None

        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                f"Player attribute '{self._attribute}' must be numeric."
            )

        return float(value)

    def _get_value(
        self,
        player: Player,
    ) -> Any:
        """
        Obtiene el atributo configurado.

        Incluye compatibilidad temporal entre nombres equivalentes
        utilizados en distintas versiones del modelo Player.
        """
        value = getattr(
            player,
            self._attribute,
            None,
        )

        if value is not None:
            return value

        alternatives = {
            "elo": (
                "faceit_elo",
            ),
            "faceit_elo": (
                "elo",
            ),
            "faceit_level": (
                "level",
            ),
            "level": (
                "faceit_level",
            ),
            "nickname": (
                "nick",
            ),
            "nick": (
                "nickname",
            ),
        }

        for alternative in alternatives.get(
            self._attribute,
            (),
        ):
            value = getattr(
                player,
                alternative,
                None,
            )

            if value is not None:
                return value

        return None

    @staticmethod
    def _validate_text(
        value: str,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
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
    def _clamp_score(
        value: float,
    ) -> float:
        """
        Garantiza que la puntuación esté entre 0 y 100.
        """
        return max(
            0.0,
            min(100.0, value),
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name='{self._name}', "
            f"attribute='{self._attribute}', "
            f"default_score={self._default_score})"
        )
