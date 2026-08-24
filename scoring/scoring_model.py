from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from numbers import Real
from typing import Any

from models.player import Player
from optimizer.activity.activity_factor_model import (
    ActivityEvaluation,
    ActivityFactorModel,
)
from scoring.score_component import ScoreComponent


class ScoringModel:
    """
    Calcula el Power Score individual de cada jugador.

    El cálculo se divide en dos fases:

        1. Power base

            Se obtiene combinando los ScoreComponent disponibles:

                ELO
                KD
                ADR
                KPR
                Winrate
                HS
                ...

            Las métricas ausentes no aportan cero. Su peso se excluye
            temporalmente y los pesos disponibles se redistribuyen.

        2. Ajuste por actividad

            Cuando existe un ActivityFactorModel:

                power final =
                    power base
                    × factor de actividad

            El ActivityFactorModel calcula primero un factor base y
            después puede suavizar o endurecer la penalización según
            el nivel FACEIT.

    Métodos principales:

        base_power(player)
            Devuelve el Power estadístico sin actividad.

        activity_evaluation(player)
            Devuelve el desglose de actividad.

        power(player)
            Devuelve el Power final ajustado.

        evaluate(player)
            Devuelve el desglose completo de estadísticas y actividad.
    """

    SCORE_MINIMUM = 0.0
    SCORE_MAXIMUM = 100.0

    def __init__(
        self,
        components: Iterable[ScoreComponent],
        weights: Mapping[str, float],
        minimum_available_weight: float = 0.0,
        default_power: float = 0.0,
        activity_factor_model: ActivityFactorModel | None = None,
    ) -> None:
        self._components = self._validate_components(
            components
        )

        self._weights = self._validate_weights(
            weights=weights,
            components=self._components,
        )

        if (
            isinstance(minimum_available_weight, bool)
            or not isinstance(
                minimum_available_weight,
                Real,
            )
        ):
            raise TypeError(
                "minimum_available_weight must be numeric."
            )

        minimum_available_weight = float(
            minimum_available_weight
        )

        if not 0.0 <= minimum_available_weight <= 100.0:
            raise ValueError(
                "minimum_available_weight must be between "
                "0 and 100."
            )

        if (
            isinstance(default_power, bool)
            or not isinstance(
                default_power,
                Real,
            )
        ):
            raise TypeError(
                "default_power must be numeric."
            )

        if (
            activity_factor_model is not None
            and not isinstance(
                activity_factor_model,
                ActivityFactorModel,
            )
        ):
            raise TypeError(
                "activity_factor_model must be an "
                "ActivityFactorModel or None."
            )

        self._minimum_available_weight = (
            minimum_available_weight
        )

        self._default_power = self._clamp(
            float(default_power)
        )

        self._activity_factor_model = (
            activity_factor_model
        )

        self._component_by_name = {
            component.name: component
            for component in self._components
        }

        self._component_by_normalized_name = {
            component.name.casefold(): component
            for component in self._components
        }

    def base_power(
        self,
        player: Player,
    ) -> float:
        """
        Calcula el Power estadístico sin aplicar actividad.

        Las métricas sin valor se excluyen del cálculo y sus pesos
        se redistribuyen entre las métricas disponibles.
        """
        evaluation = self.evaluate_base(
            player
        )

        return float(
            evaluation["base_power"]
        )

    def power(
        self,
        player: Player,
    ) -> float:
        """
        Devuelve el Power final del jugador.

        Cuando existe ActivityFactorModel:

            final_power =
                base_power
                × activity_factor

        Cuando no existe:

            final_power =
                base_power
        """
        evaluation = self.evaluate(
            player
        )

        return float(
            evaluation["power"]
        )

    def evaluate_base(
        self,
        player: Player,
    ) -> dict[str, Any]:
        """
        Calcula exclusivamente el Power base y devuelve el desglose
        de componentes.

        Returns:
            Diccionario con:

                base_power:
                    Power estadístico entre 0 y 100.

                configured_weight:
                    Suma de pesos configurados.

                available_weight:
                    Peso disponible para el jugador.

                missing_weight:
                    Peso asociado a métricas ausentes.

                availability_percentage:
                    Porcentaje de información disponible.

                has_sufficient_data:
                    Indica si se alcanza el mínimo configurado.

                components:
                    Desglose de cada ScoreComponent.
        """
        self._validate_player(
            player
        )

        component_results: dict[
            str,
            dict[str, Any],
        ] = {}

        configured_weight = sum(
            self._weights.values()
        )

        available_weight = 0.0
        weighted_score = 0.0

        for component in self._components:
            component_name = component.name

            configured_component_weight = (
                self._weights[
                    component_name
                ]
            )

            is_available = (
                self._component_has_value(
                    component=component,
                    player=player,
                )
            )

            raw_value = self._component_raw_value(
                component=component,
                player=player,
            )

            if not is_available:
                component_results[
                    component_name
                ] = {
                    "available": False,
                    "raw_value": raw_value,
                    "score": None,
                    "configured_weight": (
                        configured_component_weight
                    ),
                    "effective_weight": 0.0,
                    "weighted_score": 0.0,
                }

                continue

            score = self._validate_component_score(
                component=component,
                player=player,
            )

            component_weighted_score = (
                score
                * configured_component_weight
            )

            available_weight += (
                configured_component_weight
            )

            weighted_score += (
                component_weighted_score
            )

            component_results[
                component_name
            ] = {
                "available": True,
                "raw_value": raw_value,
                "score": score,
                "configured_weight": (
                    configured_component_weight
                ),
                "effective_weight": 0.0,
                "weighted_score": (
                    component_weighted_score
                ),
            }

        availability_percentage = (
            available_weight
            / configured_weight
            * 100.0
            if configured_weight > 0.0
            else 0.0
        )

        has_sufficient_data = (
            available_weight > 0.0
            and availability_percentage
            >= self._minimum_available_weight
        )

        if not has_sufficient_data:
            base_power = self._default_power

        else:
            base_power = (
                weighted_score
                / available_weight
            )

        base_power = self._clamp(
            base_power
        )

        self._apply_effective_weights(
            component_results=component_results,
            available_weight=available_weight,
        )

        return {
            "base_power": base_power,
            "configured_weight": configured_weight,
            "available_weight": available_weight,
            "missing_weight": (
                configured_weight
                - available_weight
            ),
            "availability_percentage": (
                availability_percentage
            ),
            "has_sufficient_data": (
                has_sufficient_data
            ),
            "components": component_results,
        }

    def activity_evaluation(
        self,
        player: Player,
        base_power: float | None = None,
    ) -> ActivityEvaluation | None:
        """
        Evalúa el estado de forma del jugador.

        Devuelve None cuando ScoringModel no tiene configurado
        ActivityFactorModel.
        """
        self._validate_player(
            player
        )

        if self._activity_factor_model is None:
            return None

        if base_power is None:
            resolved_base_power = self.base_power(
                player
            )

        else:
            resolved_base_power = (
                self._validate_power_value(
                    value=base_power,
                    field_name="base_power",
                )
            )

        return self._activity_factor_model.evaluate(
            player=player,
            base_power=resolved_base_power,
        )

    def activity_factor(
        self,
        player: Player,
    ) -> float:
        """
        Devuelve únicamente el factor de actividad.

        Cuando no existe ActivityFactorModel, devuelve 1.0.
        """
        evaluation = self.activity_evaluation(
            player
        )

        if evaluation is None:
            return 1.0

        return float(
            evaluation.activity_factor
        )

    def adjusted_power(
        self,
        player: Player,
        base_power: float | None = None,
    ) -> float:
        """
        Devuelve el Power ajustado por actividad.

        Es equivalente a power(), pero permite proporcionar un
        Power base previamente calculado para evitar repetir trabajo.
        """
        self._validate_player(
            player
        )

        if base_power is None:
            resolved_base_power = self.base_power(
                player
            )

        else:
            resolved_base_power = (
                self._validate_power_value(
                    value=base_power,
                    field_name="base_power",
                )
            )

        if self._activity_factor_model is None:
            return resolved_base_power

        evaluation = (
            self._activity_factor_model.evaluate(
                player=player,
                base_power=resolved_base_power,
            )
        )

        return self._clamp(
            evaluation.adjusted_power
        )

    def evaluate(
        self,
        player: Player,
    ) -> dict[str, Any]:
        """
        Calcula el Power base, aplica actividad y devuelve el
        desglose completo.

        El campo `power` representa siempre el Power final utilizado
        por el resto de la aplicación.

        Cuando ActivityFactorModel incorpora un ajuste dependiente del
        nivel FACEIT también se conservan:

            base_activity_factor:
                Factor de actividad antes de ajustar la intensidad de
                la penalización según el nivel.

            level_penalty_strength:
                Multiplicador aplicado únicamente a la parte perdida
                del Power.

            activity_factor:
                Factor final efectivo después del ajuste por nivel.

            faceit_level:
                Nivel FACEIT utilizado para resolver la intensidad de
                la penalización.

        De esta forma el HTML puede explicar exactamente:

            actividad observada
                ↓
            factor base
                ↓
            intensidad por nivel
                ↓
            factor efectivo
                ↓
            Power final
        """
        base_evaluation = self.evaluate_base(
            player
        )

        base_power = float(
            base_evaluation["base_power"]
        )

        activity_evaluation = (
            self.activity_evaluation(
                player=player,
                base_power=base_power,
            )
        )

        if activity_evaluation is None:
            activity_score = 1.0
            base_activity_factor = 1.0
            level_penalty_strength = 1.0
            activity_factor = 1.0
            adjusted_power = base_power

            faceit_level = self._player_faceit_level(
                player
            )

            activity_data: dict[str, Any] = {
                "enabled": False,
                "base_power": base_power,
                "adjusted_power": base_power,
                "activity_score": activity_score,
                "base_activity_factor": (
                    base_activity_factor
                ),
                "level_penalty_strength": (
                    level_penalty_strength
                ),
                "activity_factor": activity_factor,
                "faceit_level": faceit_level,
                "has_activity_data": (
                    getattr(
                        player,
                        "activity",
                        None,
                    )
                    is not None
                ),
                "history_complete": getattr(
                    player,
                    "activity_history_complete",
                    None,
                ),
                "matches_0_7_days": getattr(
                    player,
                    "matches_0_7_days",
                    None,
                ),
                "matches_8_30_days": getattr(
                    player,
                    "matches_8_30_days",
                    None,
                ),
                "matches_31_90_days": getattr(
                    player,
                    "matches_31_90_days",
                    None,
                ),
                "total_matches_90_days": getattr(
                    player,
                    "total_matches_90_days",
                    None,
                ),
                "days_since_last_match": getattr(
                    player,
                    "days_since_last_match",
                    None,
                ),
                "reason": (
                    "Activity adjustment is disabled."
                ),
            }

        else:
            activity_score = float(
                activity_evaluation.activity_score
            )

            base_activity_factor = float(
                activity_evaluation.base_activity_factor
            )

            level_penalty_strength = float(
                activity_evaluation.level_penalty_strength
            )

            activity_factor = float(
                activity_evaluation.activity_factor
            )

            faceit_level = (
                activity_evaluation.faceit_level
            )

            adjusted_power = self._clamp(
                activity_evaluation.adjusted_power
            )

            activity_data = {
                "enabled": True,
                **activity_evaluation.as_dict(),
                "has_activity_data": (
                    getattr(
                        player,
                        "activity",
                        None,
                    )
                    is not None
                ),
            }

        return {
            "power": adjusted_power,
            "base_power": base_power,
            "adjusted_power": adjusted_power,

            "activity_score": activity_score,
            "base_activity_factor": (
                base_activity_factor
            ),
            "level_penalty_strength": (
                level_penalty_strength
            ),
            "activity_factor": activity_factor,
            "activity_enabled": (
                self._activity_factor_model
                is not None
            ),
            "faceit_level": faceit_level,

            "activity": activity_data,

            "configured_weight": base_evaluation[
                "configured_weight"
            ],
            "available_weight": base_evaluation[
                "available_weight"
            ],
            "missing_weight": base_evaluation[
                "missing_weight"
            ],
            "availability_percentage": (
                base_evaluation[
                    "availability_percentage"
                ]
            ),
            "has_sufficient_data": (
                base_evaluation[
                    "has_sufficient_data"
                ]
            ),
            "components": base_evaluation[
                "components"
            ],
        }

    def rank(
        self,
        players: Sequence[Player],
        descending: bool = True,
    ) -> list[Player]:
        """
        Ordena jugadores según el Power final ajustado.

        En caso de empate se utiliza:

            1. Power base.
            2. ELO.
            3. Nick.

        Esto mantiene un resultado determinista.
        """
        player_list = self._validate_players(
            players
        )

        return sorted(
            player_list,
            key=self._ranking_key,
            reverse=descending,
        )

    def rank_with_scores(
        self,
        players: Sequence[Player],
        descending: bool = True,
    ) -> list[tuple[Player, float]]:
        """
        Devuelve jugadores junto a su Power final ajustado.
        """
        ranked_players = self.rank(
            players=players,
            descending=descending,
        )

        return [
            (
                player,
                self.power(player),
            )
            for player in ranked_players
        ]

    def rank_with_evaluations(
        self,
        players: Sequence[Player],
        descending: bool = True,
    ) -> list[tuple[Player, dict[str, Any]]]:
        """
        Devuelve los jugadores y el desglose completo del Power.

        Resulta útil para depuración y para generar el HTML.
        """
        player_list = self._validate_players(
            players
        )

        evaluations = {
            id(player): self.evaluate(player)
            for player in player_list
        }

        ranked_players = sorted(
            player_list,
            key=lambda player: self._ranking_key_from_evaluation(
                player=player,
                evaluation=evaluations[
                    id(player)
                ],
            ),
            reverse=descending,
        )

        return [
            (
                player,
                evaluations[id(player)],
            )
            for player in ranked_players
        ]

    def component_score(
        self,
        player: Player,
        component_name: str,
    ) -> float | None:
        """
        Devuelve la puntuación de un componente concreto.

        Si el jugador no dispone del dato, devuelve None.
        """
        self._validate_player(
            player
        )

        component = self.get_component(
            component_name
        )

        if not self._component_has_value(
            component=component,
            player=player,
        ):
            return None

        return self._validate_component_score(
            component=component,
            player=player,
        )

    def get_component(
        self,
        component_name: str,
    ) -> ScoreComponent:
        """
        Obtiene un componente por nombre ignorando mayúsculas.
        """
        normalized_name = self._validate_text(
            component_name,
            "component_name",
        ).casefold()

        component = (
            self._component_by_normalized_name.get(
                normalized_name
            )
        )

        if component is None:
            raise KeyError(
                f"Component '{component_name}' "
                "was not found."
            )

        return component

    def get_weight(
        self,
        component_name: str,
    ) -> float:
        """
        Devuelve el peso configurado para un componente.
        """
        component = self.get_component(
            component_name
        )

        return self._weights[
            component.name
        ]

    def has_component(
        self,
        component_name: str,
    ) -> bool:
        """
        Indica si existe un componente con el nombre recibido.
        """
        if not isinstance(
            component_name,
            str,
        ):
            return False

        normalized_name = (
            component_name
            .strip()
            .casefold()
        )

        if not normalized_name:
            return False

        return (
            normalized_name
            in self._component_by_normalized_name
        )

    def as_dict(
        self,
    ) -> dict[str, Any]:
        """
        Devuelve la configuración serializable del modelo.
        """
        activity_configuration: dict[str, Any] | None

        if self._activity_factor_model is None:
            activity_configuration = None

        else:
            activity_configuration = {
                "type": (
                    self._activity_factor_model
                    .__class__.__name__
                ),
                "target_0_7": (
                    self._activity_factor_model
                    .target_0_7
                ),
                "target_8_30": (
                    self._activity_factor_model
                    .target_8_30
                ),
                "target_31_90": (
                    self._activity_factor_model
                    .target_31_90
                ),
                "weight_0_7": (
                    self._activity_factor_model
                    .weight_0_7
                ),
                "weight_8_30": (
                    self._activity_factor_model
                    .weight_8_30
                ),
                "weight_31_90": (
                    self._activity_factor_model
                    .weight_31_90
                ),
                "minimum_factor": (
                    self._activity_factor_model
                    .minimum_factor
                ),
                "level_penalty_strength": dict(
                    self._activity_factor_model
                    .LEVEL_PENALTY_STRENGTH
                ),
            }

        return {
            "component_count": len(
                self._components
            ),
            "configured_weight": sum(
                self._weights.values()
            ),
            "minimum_available_weight": (
                self._minimum_available_weight
            ),
            "default_power": (
                self._default_power
            ),
            "activity_enabled": (
                self._activity_factor_model
                is not None
            ),
            "activity_model": (
                activity_configuration
            ),
            "components": [
                {
                    "name": component.name,
                    "type": (
                        component
                        .__class__
                        .__name__
                    ),
                    "weight": self._weights[
                        component.name
                    ],
                    "attribute": getattr(
                        component,
                        "attribute",
                        None,
                    ),
                }
                for component in self._components
            ],
        }

    def _ranking_key(
        self,
        player: Player,
    ) -> tuple[float, float, float, str]:
        """
        Construye una clave determinista para ordenar jugadores.
        """
        evaluation = self.evaluate(
            player
        )

        return self._ranking_key_from_evaluation(
            player=player,
            evaluation=evaluation,
        )

    @staticmethod
    def _ranking_key_from_evaluation(
        player: Player,
        evaluation: Mapping[str, Any],
    ) -> tuple[float, float, float, str]:
        adjusted_power = ScoringModel._safe_float(
            evaluation.get("power"),
            default=0.0,
        )

        base_power = ScoringModel._safe_float(
            evaluation.get("base_power"),
            default=0.0,
        )

        elo = getattr(
            player,
            "elo",
            getattr(
                player,
                "faceit_elo",
                0.0,
            ),
        )

        elo_value = ScoringModel._safe_float(
            elo,
            default=0.0,
        )

        nickname = getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                "",
            ),
        )

        return (
            adjusted_power,
            base_power,
            elo_value,
            str(nickname).casefold(),
        )

    @staticmethod
    def _component_has_value(
        component: ScoreComponent,
        player: Player,
    ) -> bool:
        """
        Comprueba si el componente dispone de un valor real.

        AttributeScoreComponent proporciona has_value(). Para otros
        componentes se considera que existe valor y se deja que
        score() realice su validación.
        """
        has_value_method = getattr(
            component,
            "has_value",
            None,
        )

        if callable(
            has_value_method
        ):
            return bool(
                has_value_method(
                    player
                )
            )

        return True

    @staticmethod
    def _component_raw_value(
        component: ScoreComponent,
        player: Player,
    ) -> float | None:
        """
        Obtiene el valor original cuando el componente lo expone.
        """
        raw_value_method = getattr(
            component,
            "raw_value",
            None,
        )

        if not callable(
            raw_value_method
        ):
            return None

        try:
            return raw_value_method(
                player
            )

        except (
            TypeError,
            ValueError,
            AttributeError,
        ):
            return None

    @classmethod
    def _validate_component_score(
        cls,
        component: ScoreComponent,
        player: Player,
    ) -> float:
        score = component.score(
            player
        )

        if (
            isinstance(score, bool)
            or not isinstance(
                score,
                Real,
            )
        ):
            raise TypeError(
                f"Component '{component.name}' "
                "must return a numeric score."
            )

        return cls._clamp(
            float(score)
        )

    @staticmethod
    def _apply_effective_weights(
        component_results: dict[
            str,
            dict[str, Any],
        ],
        available_weight: float,
    ) -> None:
        """
        Calcula el porcentaje efectivo de cada componente después de
        redistribuir los pesos disponibles.
        """
        if available_weight <= 0.0:
            return

        for component_result in (
            component_results.values()
        ):
            if not component_result[
                "available"
            ]:
                continue

            configured_weight = float(
                component_result[
                    "configured_weight"
                ]
            )

            effective_weight = (
                configured_weight
                / available_weight
                * 100.0
            )

            component_result[
                "effective_weight"
            ] = effective_weight

    @staticmethod
    def _validate_components(
        components: Iterable[ScoreComponent],
    ) -> tuple[ScoreComponent, ...]:
        if components is None:
            raise ValueError(
                "components cannot be None."
            )

        try:
            component_list = tuple(
                components
            )

        except TypeError as error:
            raise TypeError(
                "components must be iterable."
            ) from error

        if not component_list:
            raise ValueError(
                "At least one ScoreComponent is required."
            )

        names: set[str] = set()

        for index, component in enumerate(
            component_list,
            start=1,
        ):
            if component is None:
                raise ValueError(
                    f"Component {index} cannot be None."
                )

            if not isinstance(
                component,
                ScoreComponent,
            ):
                raise TypeError(
                    f"Component {index} must be a "
                    "ScoreComponent instance."
                )

            if not isinstance(
                component.name,
                str,
            ):
                raise TypeError(
                    f"Component {index} must expose "
                    "a string name."
                )

            normalized_name = (
                component.name
                .strip()
                .casefold()
            )

            if not normalized_name:
                raise ValueError(
                    f"Component {index} has an empty name."
                )

            if normalized_name in names:
                raise ValueError(
                    f"Duplicated component name "
                    f"'{component.name}'."
                )

            names.add(
                normalized_name
            )

        return component_list

    @staticmethod
    def _validate_weights(
        weights: Mapping[str, float],
        components: tuple[ScoreComponent, ...],
    ) -> dict[str, float]:
        if weights is None:
            raise ValueError(
                "weights cannot be None."
            )

        if not isinstance(
            weights,
            Mapping,
        ):
            raise TypeError(
                "weights must be a mapping."
            )

        normalized_weights: dict[
            str,
            float,
        ] = {}

        for name, weight in weights.items():
            if not isinstance(
                name,
                str,
            ):
                raise TypeError(
                    "Every weight key must be a string."
                )

            normalized_name = name.strip()

            if not normalized_name:
                raise ValueError(
                    "Weight names cannot be empty."
                )

            if (
                isinstance(weight, bool)
                or not isinstance(
                    weight,
                    Real,
                )
            ):
                raise TypeError(
                    f"Weight '{name}' must be numeric."
                )

            numeric_weight = float(
                weight
            )

            if numeric_weight <= 0.0:
                raise ValueError(
                    f"Weight '{name}' must be greater "
                    "than zero."
                )

            normalized_weights[
                normalized_name.casefold()
            ] = numeric_weight

        result: dict[str, float] = {}

        component_names = {
            component.name.casefold()
            for component in components
        }

        for component in components:
            normalized_component_name = (
                component.name.casefold()
            )

            if (
                normalized_component_name
                not in normalized_weights
            ):
                raise ValueError(
                    f"Missing weight for component "
                    f"'{component.name}'."
                )

            result[
                component.name
            ] = normalized_weights[
                normalized_component_name
            ]

        unknown_weights = (
            set(normalized_weights)
            - component_names
        )

        if unknown_weights:
            raise ValueError(
                "Weights were defined for unknown "
                f"components: {sorted(unknown_weights)}."
            )

        return result

    @staticmethod
    def _validate_players(
        players: Sequence[Player],
    ) -> list[Player]:
        if players is None:
            raise ValueError(
                "players cannot be None."
            )

        player_list = list(
            players
        )

        if not player_list:
            raise ValueError(
                "At least one player is required."
            )

        for index, player in enumerate(
            player_list,
            start=1,
        ):
            if player is None:
                raise ValueError(
                    f"Player {index} cannot be None."
                )

        return player_list

    @staticmethod
    def _validate_player(
        player: Player,
    ) -> None:
        if player is None:
            raise ValueError(
                "player cannot be None."
            )

    @staticmethod
    def _validate_power_value(
        value: float,
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

        numeric_value = float(
            value
        )

        if numeric_value < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return ScoringModel._clamp(
            numeric_value
        )

    @staticmethod
    def _validate_text(
        value: str,
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
    def _player_faceit_level(
        player: Player,
    ) -> int | None:
        """
        Obtiene un nivel FACEIT válido entre 1 y 10.
        """
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

    @staticmethod
    def _safe_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        if value is None:
            return float(
                default
            )

        if isinstance(
            value,
            bool,
        ):
            return float(
                default
            )

        try:
            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return float(
                default
            )

    @classmethod
    def _clamp(
        cls,
        value: float,
    ) -> float:
        return max(
            cls.SCORE_MINIMUM,
            min(
                cls.SCORE_MAXIMUM,
                float(value),
            ),
        )

    @property
    def components(
        self,
    ) -> tuple[ScoreComponent, ...]:
        return self._components

    @property
    def weights(
        self,
    ) -> dict[str, float]:
        return dict(
            self._weights
        )

    @property
    def minimum_available_weight(
        self,
    ) -> float:
        return self._minimum_available_weight

    @property
    def default_power(
        self,
    ) -> float:
        return self._default_power

    @property
    def activity_factor_model(
        self,
    ) -> ActivityFactorModel | None:
        return self._activity_factor_model

    @property
    def activity_enabled(
        self,
    ) -> bool:
        return (
            self._activity_factor_model
            is not None
        )

    def __len__(
        self,
    ) -> int:
        return len(
            self._components
        )

    def __repr__(
        self,
    ) -> str:
        component_names = ", ".join(
            component.name
            for component in self._components
        )

        activity_model_name = (
            self._activity_factor_model
            .__class__
            .__name__
            if self._activity_factor_model
            is not None
            else "disabled"
        )

        return (
            f"{self.__class__.__name__}("
            f"components=[{component_names}], "
            f"configured_weight="
            f"{sum(self._weights.values()):.2f}, "
            f"activity_model="
            f"{activity_model_name})"
        )
