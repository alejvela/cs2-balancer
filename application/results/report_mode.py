from __future__ import annotations

from enum import Enum
from typing import Any


class ReportMode(str, Enum):
    """
    Representa el modo mediante el cual se ha obtenido un resultado.

    Los valores heredan también de `str` para facilitar:

        - Serialización JSON.
        - Exportación HTML.
        - Comparaciones con cadenas.
        - Persistencia futura en base de datos.
        - Uso desde una API REST.

    Modos disponibles:

        OPTIMIZED:
            Los equipos fueron generados y posteriormente optimizados
            por el motor de balanceo.

        PREASSIGNED:
            Los equipos fueron definidos previamente por el usuario
            mediante la columna Team y únicamente fueron evaluados.

    En el futuro podrán añadirse otros modos, por ejemplo:

        SIMULATED
        MANUAL
        DRAFTED
        IMPORTED
    """

    OPTIMIZED = "optimized"
    PREASSIGNED = "preassigned"

    @property
    def label(
        self,
    ) -> str:
        """
        Devuelve una etiqueta legible para interfaces de usuario.
        """
        labels = {
            ReportMode.OPTIMIZED: (
                "Generación y optimización automática"
            ),
            ReportMode.PREASSIGNED: (
                "Evaluación de equipos predeterminados"
            ),
        }

        return labels[
            self
        ]

    @property
    def short_label(
        self,
    ) -> str:
        """
        Devuelve una etiqueta corta adecuada para badges o tablas.
        """
        labels = {
            ReportMode.OPTIMIZED: "Optimización",
            ReportMode.PREASSIGNED: "Evaluación",
        }

        return labels[
            self
        ]

    @property
    def description(
        self,
    ) -> str:
        """
        Devuelve una descripción del origen del resultado.
        """
        descriptions = {
            ReportMode.OPTIMIZED: (
                "Los equipos fueron generados y mejorados "
                "automáticamente por el motor de optimización."
            ),
            ReportMode.PREASSIGNED: (
                "Los equipos proceden de una asignación previa "
                "y no fueron modificados por el optimizador."
            ),
        }

        return descriptions[
            self
        ]

    @property
    def optimized(
        self,
    ) -> bool:
        """
        Indica si el resultado procede del optimizador.
        """
        return self is ReportMode.OPTIMIZED

    @property
    def evaluation_only(
        self,
    ) -> bool:
        """
        Indica si el resultado representa únicamente una evaluación.
        """
        return self is ReportMode.PREASSIGNED

    @property
    def css_class(
        self,
    ) -> str:
        """
        Nombre estable para utilizar como clase CSS.
        """
        return self.value

    @classmethod
    def from_value(
        cls,
        value: Any,
    ) -> ReportMode:
        """
        Convierte un valor externo en ReportMode.

        Admite:

            ReportMode.OPTIMIZED
            "optimized"
            "automatic"
            "optimization"
            "preassigned"
            "preassigned_evaluation"
            "evaluation"

        Esta compatibilidad permite migrar gradualmente los valores
        antiguos utilizados por LanBalancer y TeamEvaluationResult.

        Raises:
            TypeError:
                Si el valor no puede interpretarse como texto.

            ValueError:
                Si el texto no corresponde a ningún modo conocido.
        """
        if isinstance(
            value,
            cls,
        ):
            return value

        if value is None:
            raise ValueError(
                "Report mode cannot be None."
            )

        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "Report mode must be a string or ReportMode."
            )

        normalized = (
            value
            .strip()
            .casefold()
            .replace("-", "_")
            .replace(" ", "_")
        )

        if not normalized:
            raise ValueError(
                "Report mode cannot be empty."
            )

        optimized_aliases = {
            "optimized",
            "optimization",
            "automatic",
            "automatic_mode",
            "generated",
            "generated_and_optimized",
        }

        preassigned_aliases = {
            "preassigned",
            "pre_assigned",
            "preassigned_mode",
            "preassigned_evaluation",
            "evaluation",
            "evaluation_only",
            "manual_assignment",
        }

        if normalized in optimized_aliases:
            return cls.OPTIMIZED

        if normalized in preassigned_aliases:
            return cls.PREASSIGNED

        raise ValueError(
            f"Unknown report mode: {value!r}."
        )

    @classmethod
    def values(
        cls,
    ) -> tuple[str, ...]:
        """
        Devuelve los valores serializables disponibles.
        """
        return tuple(
            mode.value
            for mode in cls
        )

    @classmethod
    def labels(
        cls,
    ) -> dict[str, str]:
        """
        Devuelve un mapa valor-etiqueta útil para formularios o APIs.
        """
        return {
            mode.value: mode.label
            for mode in cls
        }

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve una representación serializable.
        """
        return {
            "value": self.value,
            "label": self.label,
            "short_label": self.short_label,
            "description": self.description,
            "optimized": self.optimized,
            "evaluation_only": self.evaluation_only,
            "css_class": self.css_class,
        }

    def __str__(
        self,
    ) -> str:
        """
        Facilita su uso en HTML, CSV, logs y JSON.
        """
        return self.value
