from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Real
from typing import Any


@dataclass(slots=True)
class RestrictionResult:
    """
    Resultado de evaluar una restricción.

    Atributos:

        name:
            Nombre único de la restricción.

        score:
            Puntuación normalizada entre 0 y 100.

        penalty:
            Penalización estructural no negativa.

            Las restricciones blandas, como Power Balance, ELO Balance
            o KD Balance, deben utilizar penalty=0.0.

        weight:
            Peso no negativo utilizado para calcular la media ponderada.

        details:
            Información adicional para depuración e informes.
    """

    name: str
    score: float
    penalty: float = 0.0
    weight: float = 1.0
    details: dict[str, Any] = field(
        default_factory=dict
    )

    SCORE_MINIMUM = 0.0
    SCORE_MAXIMUM = 100.0

    def __post_init__(
        self,
    ) -> None:
        self.name = self._validate_name(
            self.name
        )

        self.score = self._validate_score(
            self.score
        )

        self.penalty = self._validate_penalty(
            self.penalty
        )

        self.weight = self._validate_weight(
            self.weight
        )

        if not isinstance(
            self.details,
            dict,
        ):
            raise TypeError(
                "details must be a dictionary."
            )

        self.details = dict(
            self.details
        )

    @property
    def weighted_score(
        self,
    ) -> float:
        """
        Puntuación ponderada de la restricción.

        Ejemplo:

            score = 90
            weight = 30

            weighted_score = 2700
        """
        return (
            self.score
            * self.weight
        )

    @property
    def passed(
        self,
    ) -> bool:
        """
        Indica si la restricción no ha generado penalización estructural.
        """
        return self.penalty <= 0.0

    def add_detail(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Añade o actualiza un detalle del resultado.
        """
        normalized_key = self._validate_detail_key(
            key
        )

        self.details[
            normalized_key
        ] = value

    def get_detail(
        self,
        key: str,
        default: Any = None,
    ) -> Any:
        """
        Obtiene un detalle por clave.
        """
        normalized_key = self._validate_detail_key(
            key
        )

        return self.details.get(
            normalized_key,
            default,
        )

    def has_detail(
        self,
        key: str,
    ) -> bool:
        """
        Indica si existe una clave dentro de details.
        """
        normalized_key = self._validate_detail_key(
            key
        )

        return (
            normalized_key
            in self.details
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable.
        """
        return {
            "name": self.name,
            "score": self.score,
            "weighted_score": self.weighted_score,
            "penalty": self.penalty,
            "weight": self.weight,
            "passed": self.passed,
            "details": dict(
                self.details
            ),
        }

    @classmethod
    def _validate_score(
        cls,
        value: float,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                "score must be numeric."
            )

        numeric_value = float(
            value
        )

        return max(
            cls.SCORE_MINIMUM,
            min(
                cls.SCORE_MAXIMUM,
                numeric_value,
            ),
        )

    @staticmethod
    def _validate_penalty(
        value: float,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                "penalty must be numeric."
            )

        numeric_value = float(
            value
        )

        if numeric_value < 0.0:
            raise ValueError(
                "penalty cannot be negative."
            )

        return numeric_value

    @staticmethod
    def _validate_weight(
        value: float,
    ) -> float:
        if isinstance(value, bool) or not isinstance(
            value,
            Real,
        ):
            raise TypeError(
                "weight must be numeric."
            )

        numeric_value = float(
            value
        )

        if numeric_value < 0.0:
            raise ValueError(
                "weight cannot be negative."
            )

        return numeric_value

    @staticmethod
    def _validate_name(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "name must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "name cannot be empty."
            )

        return normalized

    @staticmethod
    def _validate_detail_key(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(
                "detail key must be a string."
            )

        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "detail key cannot be empty."
            )

        return normalized

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"score={self.score:.2f}, "
            f"weight={self.weight:.2f}, "
            f"penalty={self.penalty:.2f}, "
            f"passed={self.passed})"
        )
