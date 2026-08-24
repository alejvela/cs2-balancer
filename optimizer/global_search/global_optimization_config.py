from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any


@dataclass(
    frozen=True,
    slots=True,
)
class GlobalOptimizationConfig:
    """
    Configuración del optimizador GLOBAL.

    El modo GLOBAL explora directamente composiciones de equipos
    mediante búsqueda combinatoria / branch & bound.

    A diferencia del optimizador local:

        - no depende de swaps;
        - no depende de restarts;
        - no modifica equipos mediante apply()/undo();
        - trabaja con estados parciales inmutables.

    ============================================================
    Límites de búsqueda
    ============================================================

    maximum_nodes:
        Número máximo de nodos visitados.

        None:
            sin límite explícito.

    maximum_evaluations:
        Número máximo de soluciones completas evaluadas mediante
        ObjectiveEngine.

        None:
            sin límite explícito.

    maximum_elapsed_seconds:
        Tiempo máximo total permitido.

        None:
            sin límite de tiempo.

    ============================================================
    Comparación de scores
    ============================================================

    score_tolerance:
        Tolerancia utilizada al comparar puntuaciones.

    minimum_improvement:
        Mejora mínima requerida para sustituir el incumbent.

    ============================================================
    Optimización
    ============================================================

    use_incumbent:
        Utiliza una solución previa como mejor solución inicial.

        Normalmente será la solución procedente de STABLE.

    use_symmetry_breaking:
        Activa eliminación de configuraciones equivalentes.

    use_seed_pruning:
        Activa podas relacionadas con restricciones de seed.

    use_capacity_pruning:
        Activa podas por capacidad imposible de los equipos.

    use_power_bound:
        Activa la futura cota superior de Power.

    use_elo_bound:
        Activa la futura cota superior de ELO.

    deterministic:
        La misma entrada y configuración deben recorrer
        las ramas en el mismo orden.

    ============================================================
    Optimalidad
    ============================================================

    require_proof:

        False:
            GLOBAL puede detenerse por límites y devolver simplemente
            la mejor solución encontrada.

        True:
            El resultado solo debe considerarse óptimo si se ha agotado
            completamente el espacio relevante mediante exploración
            o podas matemáticamente seguras.

    En esta etapa utilizaremos normalmente:

        require_proof=False
    """

    maximum_nodes: int | None = 2_000_000

    maximum_evaluations: int | None = 250_000

    maximum_elapsed_seconds: float | None = 120.0

    score_tolerance: float = 1e-6

    minimum_improvement: float = 1e-6

    use_incumbent: bool = True

    use_symmetry_breaking: bool = True

    use_seed_pruning: bool = True

    use_capacity_pruning: bool = True

    use_power_bound: bool = True

    use_elo_bound: bool = True

    deterministic: bool = True

    require_proof: bool = False

    base_seed: int = 2026

    def __post_init__(
        self,
    ) -> None:
        # ====================================================
        # Límites
        # ====================================================

        self._validate_optional_positive_integer(
            value=self.maximum_nodes,
            field_name="maximum_nodes",
        )

        self._validate_optional_positive_integer(
            value=self.maximum_evaluations,
            field_name="maximum_evaluations",
        )

        self._validate_optional_positive_number(
            value=self.maximum_elapsed_seconds,
            field_name="maximum_elapsed_seconds",
        )

        # ====================================================
        # Scores
        # ====================================================

        self._validate_non_negative_number(
            value=self.score_tolerance,
            field_name="score_tolerance",
        )

        self._validate_non_negative_number(
            value=self.minimum_improvement,
            field_name="minimum_improvement",
        )

        # ====================================================
        # Booleanos
        # ====================================================

        boolean_fields = {
            "use_incumbent": (
                self.use_incumbent
            ),

            "use_symmetry_breaking": (
                self.use_symmetry_breaking
            ),

            "use_seed_pruning": (
                self.use_seed_pruning
            ),

            "use_capacity_pruning": (
                self.use_capacity_pruning
            ),

            "use_power_bound": (
                self.use_power_bound
            ),

            "use_elo_bound": (
                self.use_elo_bound
            ),

            "deterministic": (
                self.deterministic
            ),

            "require_proof": (
                self.require_proof
            ),
        }

        for (
            field_name,
            value,
        ) in boolean_fields.items():
            if not isinstance(
                value,
                bool,
            ):
                raise TypeError(
                    f"{field_name} must be a boolean."
                )

        # ====================================================
        # Seed
        # ====================================================

        if (
            isinstance(
                self.base_seed,
                bool,
            )
            or not isinstance(
                self.base_seed,
                int,
            )
        ):
            raise TypeError(
                "base_seed must be an integer."
            )

        # ====================================================
        # Configuración de proof
        # ====================================================

        if self.require_proof:
            if (
                self.maximum_nodes
                is not None
                or self.maximum_evaluations
                is not None
                or self.maximum_elapsed_seconds
                is not None
            ):
                raise ValueError(
                    "require_proof=True requires "
                    "maximum_nodes, maximum_evaluations "
                    "and maximum_elapsed_seconds to be None."
                )

    # ========================================================
    # Comparación de puntuaciones
    # ========================================================

    def score_improves(
        self,
        candidate: float,
        current_best: float,
    ) -> bool:
        """
        Indica si candidate mejora realmente current_best.

        Se exige al menos:

            max(
                score_tolerance,
                minimum_improvement
            )

        de mejora.
        """

        candidate_value = (
            self._validate_numeric(
                value=candidate,
                field_name="candidate",
            )
        )

        current_value = (
            self._validate_numeric(
                value=current_best,
                field_name="current_best",
            )
        )

        required_improvement = max(
            self.score_tolerance,
            self.minimum_improvement,
        )

        return (
            candidate_value
            > (
                current_value
                + required_improvement
            )
        )

    def scores_equivalent(
        self,
        first: float,
        second: float,
    ) -> bool:
        """
        Considera equivalentes dos scores dentro de score_tolerance.
        """

        first_value = (
            self._validate_numeric(
                value=first,
                field_name="first",
            )
        )

        second_value = (
            self._validate_numeric(
                value=second,
                field_name="second",
            )
        )

        return (
            abs(
                first_value
                - second_value
            )
            <= self.score_tolerance
        )

    # ========================================================
    # Límites activos
    # ========================================================

    @property
    def has_node_limit(
        self,
    ) -> bool:
        return (
            self.maximum_nodes
            is not None
        )

    @property
    def has_evaluation_limit(
        self,
    ) -> bool:
        return (
            self.maximum_evaluations
            is not None
        )

    @property
    def has_time_limit(
        self,
    ) -> bool:
        return (
            self.maximum_elapsed_seconds
            is not None
        )

    @property
    def unlimited(
        self,
    ) -> bool:
        """
        True cuando no existe ningún límite artificial.
        """

        return (
            self.maximum_nodes
            is None
            and self.maximum_evaluations
            is None
            and self.maximum_elapsed_seconds
            is None
        )

    # ========================================================
    # Presets
    # ========================================================

    @classmethod
    def smoke_test(
        cls,
    ) -> GlobalOptimizationConfig:
        """
        Configuración pequeña para validar la integración GLOBAL.

        Es la que encaja con la prueba que estamos ejecutando ahora.
        """

        return cls(
            maximum_nodes=50_000,

            maximum_evaluations=5_000,

            maximum_elapsed_seconds=30.0,

            score_tolerance=1e-6,

            minimum_improvement=1e-6,

            use_incumbent=True,

            use_symmetry_breaking=True,

            use_seed_pruning=True,

            use_capacity_pruning=True,

            use_power_bound=True,

            use_elo_bound=True,

            deterministic=True,

            require_proof=False,

            base_seed=2026,
        )

    @classmethod
    def balanced(
        cls,
    ) -> GlobalOptimizationConfig:
        """
        Configuración general para ejecuciones normales.
        """

        return cls(
            maximum_nodes=2_000_000,

            maximum_evaluations=250_000,

            maximum_elapsed_seconds=120.0,

            score_tolerance=1e-6,

            minimum_improvement=1e-6,

            use_incumbent=True,

            use_symmetry_breaking=True,

            use_seed_pruning=True,

            use_capacity_pruning=True,

            use_power_bound=True,

            use_elo_bound=True,

            deterministic=True,

            require_proof=False,

            base_seed=2026,
        )

    @classmethod
    def deep(
        cls,
    ) -> GlobalOptimizationConfig:
        """
        Configuración más profunda para búsquedas offline.
        """

        return cls(
            maximum_nodes=10_000_000,

            maximum_evaluations=1_000_000,

            maximum_elapsed_seconds=600.0,

            score_tolerance=1e-6,

            minimum_improvement=1e-6,

            use_incumbent=True,

            use_symmetry_breaking=True,

            use_seed_pruning=True,

            use_capacity_pruning=True,

            use_power_bound=True,

            use_elo_bound=True,

            deterministic=True,

            require_proof=False,

            base_seed=2026,
        )

    @classmethod
    def proof(
        cls,
    ) -> GlobalOptimizationConfig:
        """
        Configuración sin límites artificiales.

        Permite intentar demostrar optimalidad real.

        Debe utilizarse únicamente cuando las podas implementadas
        sean matemáticamente seguras.
        """

        return cls(
            maximum_nodes=None,

            maximum_evaluations=None,

            maximum_elapsed_seconds=None,

            score_tolerance=1e-9,

            minimum_improvement=1e-9,

            use_incumbent=True,

            use_symmetry_breaking=True,

            use_seed_pruning=True,

            use_capacity_pruning=True,

            use_power_bound=True,

            use_elo_bound=True,

            deterministic=True,

            require_proof=True,

            base_seed=2026,
        )

    # ========================================================
    # Serialización
    # ========================================================

    def as_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "maximum_nodes": (
                self.maximum_nodes
            ),

            "maximum_evaluations": (
                self.maximum_evaluations
            ),

            "maximum_elapsed_seconds": (
                self.maximum_elapsed_seconds
            ),

            "score_tolerance": (
                self.score_tolerance
            ),

            "minimum_improvement": (
                self.minimum_improvement
            ),

            "use_incumbent": (
                self.use_incumbent
            ),

            "use_symmetry_breaking": (
                self.use_symmetry_breaking
            ),

            "use_seed_pruning": (
                self.use_seed_pruning
            ),

            "use_capacity_pruning": (
                self.use_capacity_pruning
            ),

            "use_power_bound": (
                self.use_power_bound
            ),

            "use_elo_bound": (
                self.use_elo_bound
            ),

            "deterministic": (
                self.deterministic
            ),

            "require_proof": (
                self.require_proof
            ),

            "base_seed": (
                self.base_seed
            ),

            "has_node_limit": (
                self.has_node_limit
            ),

            "has_evaluation_limit": (
                self.has_evaluation_limit
            ),

            "has_time_limit": (
                self.has_time_limit
            ),

            "unlimited": (
                self.unlimited
            ),
        }

    # ========================================================
    # Validación numérica
    # ========================================================

    @staticmethod
    def _validate_numeric(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                Real,
            )
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        return float(
            value
        )

    @classmethod
    def _validate_non_negative_number(
        cls,
        value: Any,
        field_name: str,
    ) -> None:
        numeric = (
            cls._validate_numeric(
                value=value,
                field_name=field_name,
            )
        )

        if numeric < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

    @classmethod
    def _validate_optional_positive_number(
        cls,
        value: Any,
        field_name: str,
    ) -> None:
        if value is None:
            return

        numeric = (
            cls._validate_numeric(
                value=value,
                field_name=field_name,
            )
        )

        if numeric <= 0.0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

    @staticmethod
    def _validate_optional_positive_integer(
        value: Any,
        field_name: str,
    ) -> None:
        if value is None:
            return

        if (
            isinstance(
                value,
                bool,
            )
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

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"maximum_nodes={self.maximum_nodes!r}, "
            f"maximum_evaluations="
            f"{self.maximum_evaluations!r}, "
            f"maximum_elapsed_seconds="
            f"{self.maximum_elapsed_seconds!r}, "
            f"require_proof="
            f"{self.require_proof})"
        )
