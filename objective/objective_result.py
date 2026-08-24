from __future__ import annotations

from dataclasses import dataclass, field
from numbers import Real
from typing import Any

from objective.restriction_result import (
    RestrictionResult,
)


@dataclass(slots=True)
class ObjectiveResult:
    """
    Resultado completo de la evaluación de una solución.

    La puntuación final se calcula así:

        weighted_average =
            sum(restriction.weighted_score)
            / sum(restriction.weight)

        final_score =
            weighted_average
            - structural_penalties

    Finalmente, la puntuación se limita al intervalo 0-100.

    Las restricciones blandas, como Power Balance, ELO Balance o
    KD Balance, deben usar penalty=0.0.

    Las penalizaciones se reservan para restricciones estructurales,
    como tamaños incorrectos, jugadores duplicados o jugadores ausentes.
    """

    restrictions: dict[str, RestrictionResult] = field(
        default_factory=dict
    )

    score: float = 0.0

    SCORE_MINIMUM = 0.0
    SCORE_MAXIMUM = 100.0

    def add_result(
        self,
        result: RestrictionResult,
    ) -> None:
        """
        Añade un resultado de restricción.

        No permite sobrescribir silenciosamente una restricción con el
        mismo nombre.
        """
        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        if not isinstance(
            result,
            RestrictionResult,
        ):
            raise TypeError(
                "result must be a RestrictionResult instance."
            )

        name = self._validate_name(
            result.name
        )

        normalized_name = name.casefold()

        existing_names = {
            existing_name.casefold()
            for existing_name in self.restrictions
        }

        if normalized_name in existing_names:
            raise ValueError(
                f"Duplicated restriction result '{name}'."
            )

        self.restrictions[name] = result

    def compute(
        self,
    ) -> float:
        """
        Calcula y almacena la puntuación final.

        Returns:
            Puntuación final entre 0 y 100.
        """
        if not self.restrictions:
            self.score = 0.0
            return self.score

        total_weight = self.total_weight

        if total_weight <= 0.0:
            self.score = 0.0
            return self.score

        raw_score = (
            self.weighted_score
            / total_weight
        )

        final_score = (
            raw_score
            - self.penalty
        )

        self.score = self._clamp_score(
            final_score
        )

        return self.score

    @property
    def weighted_score(
        self,
    ) -> float:
        """
        Suma de las puntuaciones ponderadas de todas las restricciones.
        """
        total = 0.0

        for result in self.restrictions.values():
            weighted_score = result.weighted_score

            if (
                isinstance(weighted_score, bool)
                or not isinstance(weighted_score, Real)
            ):
                raise TypeError(
                    f"Restriction '{result.name}' returned a "
                    "non-numeric weighted_score."
                )

            total += float(
                weighted_score
            )

        return total

    @property
    def total_weight(
        self,
    ) -> float:
        """
        Suma de todos los pesos configurados.
        """
        total = 0.0

        for result in self.restrictions.values():
            weight = result.weight

            if (
                isinstance(weight, bool)
                or not isinstance(weight, Real)
            ):
                raise TypeError(
                    f"Restriction '{result.name}' has a "
                    "non-numeric weight."
                )

            numeric_weight = float(
                weight
            )

            if numeric_weight < 0.0:
                raise ValueError(
                    f"Restriction '{result.name}' has a "
                    "negative weight."
                )

            total += numeric_weight

        return total

    @property
    def weighted_average(
        self,
    ) -> float:
        """
        Puntuación media ponderada antes de aplicar penalizaciones.
        """
        total_weight = self.total_weight

        if total_weight <= 0.0:
            return 0.0

        return (
            self.weighted_score
            / total_weight
        )

    @property
    def penalty(
        self,
    ) -> float:
        """
        Suma de penalizaciones estructurales.

        Las restricciones blandas deben aportar 0.0.
        """
        total = 0.0

        for result in self.restrictions.values():
            penalty = result.penalty

            if (
                isinstance(penalty, bool)
                or not isinstance(penalty, Real)
            ):
                raise TypeError(
                    f"Restriction '{result.name}' has a "
                    "non-numeric penalty."
                )

            numeric_penalty = float(
                penalty
            )

            if numeric_penalty < 0.0:
                raise ValueError(
                    f"Restriction '{result.name}' has a "
                    "negative penalty."
                )

            total += numeric_penalty

        return total

    @property
    def is_valid(
        self,
    ) -> bool:
        """
        Una solución se considera estructuralmente válida cuando no
        contiene penalizaciones.
        """
        return self.penalty <= 0.0

    def get(
        self,
        name: str,
    ) -> RestrictionResult | None:
        """
        Obtiene un resultado ignorando mayúsculas y minúsculas.
        """
        normalized_name = self._validate_name(
            name
        ).casefold()

        for restriction_name, result in self.restrictions.items():
            if restriction_name.casefold() == normalized_name:
                return result

        return None

    def summary(
        self,
    ) -> dict[str, float]:
        """
        Devuelve únicamente las puntuaciones de cada restricción.
        """
        return {
            name: float(result.score)
            for name, result
            in self.restrictions.items()
        }

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable.
        """
        return {
            "score": self.score,
            "weighted_average": self.weighted_average,
            "weighted_score": self.weighted_score,
            "total_weight": self.total_weight,
            "penalty": self.penalty,
            "is_valid": self.is_valid,
            "restrictions": {
                name: result.as_dict()
                for name, result
                in self.restrictions.items()
            },
        }

    @staticmethod
    def _validate_name(
        name: str,
    ) -> str:
        if not isinstance(name, str):
            raise TypeError(
                "Restriction name must be a string."
            )

        normalized = name.strip()

        if not normalized:
            raise ValueError(
                "Restriction name cannot be empty."
            )

        return normalized

    @classmethod
    def _clamp_score(
        cls,
        value: float,
    ) -> float:
        """
        Limita la puntuación final al intervalo 0-100.
        """
        return max(
            cls.SCORE_MINIMUM,
            min(
                cls.SCORE_MAXIMUM,
                float(value),
            ),
        )

    def __getitem__(
        self,
        name: str,
    ) -> RestrictionResult:
        result = self.get(
            name
        )

        if result is None:
            raise KeyError(
                f"Restriction result '{name}' was not found."
            )

        return result

    def __contains__(
        self,
        name: object,
    ) -> bool:
        if not isinstance(name, str):
            return False

        return self.get(name) is not None

    def __len__(
        self,
    ) -> int:
        return len(
            self.restrictions
        )

    def __iter__(
        self,
    ):
        return iter(
            self.restrictions.values()
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"score={self.score:.2f}, "
            f"weighted_average={self.weighted_average:.2f}, "
            f"penalty={self.penalty:.2f}, "
            f"restrictions={len(self.restrictions)})"
        )
