from __future__ import annotations

import copy
import random
from collections.abc import Sequence
from typing import Any

from models.player import Player
from models.team import Team
from optimizer.stable.solution_signature import (
    SolutionSignature,
)


class DeterministicRestartGenerator:
    """
    Generador determinista de soluciones iniciales para StableOptimizer.

    Objetivo:

        misma solución inicial
        + mismo restart_index
        + misma seed
                ↓
        exactamente la misma composición

    pero:

        distinto restart_index
                ↓
        distinta zona del espacio de búsqueda

    Esto permite que LocalOptimizer explore múltiples óptimos locales
    sin introducir aleatoriedad no reproducible.

    Estrategias utilizadas:

        Restart 0
            Conserva exactamente la distribución original.

        Familia 1
            Swaps deterministas entre equipos.

        Familia 2
            Redistribución parcial de jugadores no-seed.

        Familia 3
            Reconstrucción completa determinista.

        Familia 4
            Reconstrucción completa + perturbación adicional.

    Después se repite el ciclo utilizando nuevas seeds.

    Restricciones estructurales preservadas:

        - mismos jugadores;
        - mismo número de equipos;
        - mismos tamaños de equipo;
        - sin duplicados;
        - sin jugadores ausentes;
        - separación de seeds cuando es matemáticamente posible.

    IMPORTANTE:

    Esta clase NO evalúa si una composición es buena.

    Su única responsabilidad es producir puntos de partida diferentes
    y reproducibles.

    La calidad se decide posteriormente mediante:

        LocalOptimizer
            ↓
        SolutionSelector
            ↓
        ConvergenceTracker
    """

    STRATEGY_COUNT = 4

    def __init__(
        self,
        separated_seed_level: int | None = 1,
        maximum_seeded_players_per_team: int = 1,
        minimum_swaps: int = 1,
        maximum_swaps: int = 6,
        partial_redistribution_ratio: float = 0.50,
    ) -> None:
        self._separated_seed_level = (
            self._validate_optional_integer(
                separated_seed_level,
                field_name="separated_seed_level",
            )
        )

        self._maximum_seeded_players_per_team = (
            self._validate_positive_integer(
                maximum_seeded_players_per_team,
                field_name=(
                    "maximum_seeded_players_per_team"
                ),
            )
        )

        self._minimum_swaps = (
            self._validate_positive_integer(
                minimum_swaps,
                field_name="minimum_swaps",
            )
        )

        self._maximum_swaps = (
            self._validate_positive_integer(
                maximum_swaps,
                field_name="maximum_swaps",
            )
        )

        if (
            self._minimum_swaps
            > self._maximum_swaps
        ):
            raise ValueError(
                "minimum_swaps cannot be greater "
                "than maximum_swaps."
            )

        self._partial_redistribution_ratio = (
            self._validate_ratio(
                partial_redistribution_ratio,
                field_name=(
                    "partial_redistribution_ratio"
                ),
            )
        )

    # ========================================================
    # API pública
    # ========================================================

    def __call__(
        self,
        initial_teams: Sequence[Team],
        restart_index: int,
        seed: int,
    ) -> list[Team]:
        """
        Permite utilizar la instancia directamente como RestartFactory.

        Ejemplo:

            StableOptimizer(
                local_optimizer=optimizer,
                restart_factory=(
                    DeterministicRestartGenerator()
                ),
            )
        """
        return self.generate(
            initial_teams=initial_teams,
            restart_index=restart_index,
            seed=seed,
        )

    def generate(
        self,
        initial_teams: Sequence[Team],
        restart_index: int,
        seed: int,
    ) -> list[Team]:
        """
        Genera una composición inicial determinista.
        """
        teams = self._validate_teams(
            initial_teams
        )

        restart_index = (
            self._validate_non_negative_integer(
                restart_index,
                field_name="restart_index",
            )
        )

        seed = self._validate_integer(
            seed,
            field_name="seed",
        )

        original_signature = (
            SolutionSignature.from_teams(
                teams
            )
        )

        # ----------------------------------------------------
        # Restart 0
        #
        # Siempre conservamos una ejecución desde la solución
        # inicial real.
        # ----------------------------------------------------

        if restart_index == 0:
            result = self._clone_teams(
                teams
            )

            self._validate_generated_solution(
                original=original_signature,
                generated=result,
            )

            return result

        rng = random.Random(
            seed
        )

        strategy_index = (
            (restart_index - 1)
            % self.STRATEGY_COUNT
        )

        if strategy_index == 0:
            result = (
                self._controlled_swaps(
                    teams=teams,
                    restart_index=restart_index,
                    rng=rng,
                )
            )

        elif strategy_index == 1:
            result = (
                self._partial_redistribution(
                    teams=teams,
                    rng=rng,
                )
            )

        elif strategy_index == 2:
            result = (
                self._full_redistribution(
                    teams=teams,
                    rng=rng,
                )
            )

        else:
            result = (
                self._full_redistribution_with_perturbation(
                    teams=teams,
                    restart_index=restart_index,
                    rng=rng,
                )
            )

        self._validate_generated_solution(
            original=original_signature,
            generated=result,
        )

        return result

    # ========================================================
    # Familia 1
    # Swaps deterministas
    # ========================================================

    def _controlled_swaps(
        self,
        teams: Sequence[Team],
        restart_index: int,
        rng: random.Random,
    ) -> list[Team]:
        """
        Parte de la solución original y realiza varios swaps entre
        jugadores no protegidos.

        Sirve para explorar óptimos locales próximos.
        """
        result = self._clone_teams(
            teams
        )

        number_of_swaps = (
            self._minimum_swaps
            + (
                restart_index
                % (
                    self._maximum_swaps
                    - self._minimum_swaps
                    + 1
                )
            )
        )

        for _ in range(
            number_of_swaps
        ):
            self._perform_random_safe_swap(
                teams=result,
                rng=rng,
            )

        return result

    def _perform_random_safe_swap(
        self,
        teams: list[Team],
        rng: random.Random,
    ) -> None:
        """
        Realiza un swap conservando seeds protegidos.

        Elegimos jugadores no-seed para que la restricción de separación
        permanezca válida.
        """
        eligible_teams = [
            (
                team_index,
                [
                    index
                    for index, player
                    in enumerate(
                        team.players
                    )
                    if not self._is_protected_seed(
                        player
                    )
                ],
            )
            for team_index, team
            in enumerate(
                teams
            )
        ]

        eligible_teams = [
            item
            for item in eligible_teams
            if item[1]
        ]

        if len(
            eligible_teams
        ) < 2:
            return

        first_team_data, second_team_data = (
            rng.sample(
                eligible_teams,
                2,
            )
        )

        first_team_index, first_positions = (
            first_team_data
        )

        second_team_index, second_positions = (
            second_team_data
        )

        first_player_index = rng.choice(
            first_positions
        )

        second_player_index = rng.choice(
            second_positions
        )

        first_players = list(
            teams[
                first_team_index
            ].players
        )

        second_players = list(
            teams[
                second_team_index
            ].players
        )

        (
            first_players[
                first_player_index
            ],
            second_players[
                second_player_index
            ],
        ) = (
            second_players[
                second_player_index
            ],
            first_players[
                first_player_index
            ],
        )

        self._replace_team_players(
            teams[first_team_index],
            first_players,
        )

        self._replace_team_players(
            teams[second_team_index],
            second_players,
        )

    # ========================================================
    # Familia 2
    # Redistribución parcial
    # ========================================================

    def _partial_redistribution(
        self,
        teams: Sequence[Team],
        rng: random.Random,
    ) -> list[Team]:
        """
        Conserva parte de la composición original y redistribuye una
        fracción de los jugadores no protegidos.

        Es una perturbación más fuerte que los swaps, pero conserva
        parte de la estructura del Snake Draft inicial.
        """
        result = self._clone_teams(
            teams
        )

        movable_positions: list[
            tuple[int, int]
        ] = []

        for team_index, team in enumerate(
            result
        ):
            for player_index, player in enumerate(
                team.players
            ):
                if self._is_protected_seed(
                    player
                ):
                    continue

                movable_positions.append(
                    (
                        team_index,
                        player_index,
                    )
                )

        if len(
            movable_positions
        ) < 2:
            return result

        redistribution_count = max(
            2,
            int(
                round(
                    len(
                        movable_positions
                    )
                    * self._partial_redistribution_ratio
                )
            ),
        )

        redistribution_count = min(
            redistribution_count,
            len(
                movable_positions
            ),
        )

        selected_positions = (
            rng.sample(
                movable_positions,
                redistribution_count,
            )
        )

        selected_players = [
            result[
                team_index
            ].players[
                player_index
            ]
            for team_index, player_index
            in selected_positions
        ]

        rng.shuffle(
            selected_players
        )

        # Evitamos, en lo posible, dejar a todos exactamente en su
        # posición original.
        if (
            len(
                selected_players
            ) > 1
        ):
            shift = (
                1
                + rng.randrange(
                    len(
                        selected_players
                    )
                    - 1
                )
            )

            selected_players = (
                selected_players[shift:]
                + selected_players[:shift]
            )

        replacements_by_team: dict[
            int,
            dict[int, Player],
        ] = {}

        for (
            team_index,
            player_index,
        ), player in zip(
            selected_positions,
            selected_players,
            strict=True,
        ):
            replacements_by_team.setdefault(
                team_index,
                {},
            )[
                player_index
            ] = player

        for team_index, replacements in (
            replacements_by_team.items()
        ):
            players = list(
                result[
                    team_index
                ].players
            )

            for (
                player_index,
                player,
            ) in replacements.items():
                players[
                    player_index
                ] = player

            self._replace_team_players(
                result[team_index],
                players,
            )

        return result

    # ========================================================
    # Familia 3
    # Reconstrucción completa
    # ========================================================

    def _full_redistribution(
        self,
        teams: Sequence[Team],
        rng: random.Random,
    ) -> list[Team]:
        """
        Reconstruye completamente los equipos.

        Los seeds protegidos se distribuyen primero.

        Después se distribuyen todos los demás jugadores manteniendo
        exactamente las capacidades originales.
        """
        template_teams = self._clone_teams(
            teams
        )

        capacities = [
            len(
                team.players
            )
            for team in teams
        ]

        all_players = [
            player
            for team in teams
            for player in team.players
        ]

        seeded_players = [
            player
            for player in all_players
            if self._is_protected_seed(
                player
            )
        ]

        regular_players = [
            player
            for player in all_players
            if not self._is_protected_seed(
                player
            )
        ]

        rng.shuffle(
            seeded_players
        )

        rng.shuffle(
            regular_players
        )

        buckets: list[
            list[Player]
        ] = [
            []
            for _ in template_teams
        ]

        # ----------------------------------------------------
        # Seeds
        # ----------------------------------------------------

        self._distribute_seeded_players(
            seeded_players=seeded_players,
            buckets=buckets,
            capacities=capacities,
            rng=rng,
        )

        # ----------------------------------------------------
        # Resto
        # ----------------------------------------------------

        self._distribute_regular_players(
            players=regular_players,
            buckets=buckets,
            capacities=capacities,
            rng=rng,
        )

        for (
            team,
            players,
        ) in zip(
            template_teams,
            buckets,
            strict=True,
        ):
            self._replace_team_players(
                team,
                players,
            )

        return template_teams

    # ========================================================
    # Familia 4
    # Reconstrucción + perturbación
    # ========================================================

    def _full_redistribution_with_perturbation(
        self,
        teams: Sequence[Team],
        restart_index: int,
        rng: random.Random,
    ) -> list[Team]:
        """
        Reconstrucción completa seguida de swaps seguros.

        Sirve para crear variantes adicionales de una distribución
        totalmente mezclada.
        """
        result = (
            self._full_redistribution(
                teams=teams,
                rng=rng,
            )
        )

        extra_swaps = (
            1
            + (
                restart_index
                % self._maximum_swaps
            )
        )

        for _ in range(
            extra_swaps
        ):
            self._perform_random_safe_swap(
                teams=result,
                rng=rng,
            )

        return result

    # ========================================================
    # Distribución de seeds
    # ========================================================

    def _distribute_seeded_players(
        self,
        seeded_players: list[Player],
        buckets: list[list[Player]],
        capacities: list[int],
        rng: random.Random,
    ) -> None:
        if not seeded_players:
            return

        maximum_seed_capacity = (
            len(
                buckets
            )
            * self._maximum_seeded_players_per_team
        )

        if (
            len(
                seeded_players
            )
            > maximum_seed_capacity
        ):
            raise ValueError(
                "Cannot preserve seed separation: "
                f"{len(seeded_players)} protected seeds "
                f"for {len(buckets)} teams with maximum "
                f"{self._maximum_seeded_players_per_team} "
                "per team."
            )

        available_team_indices = list(
            range(
                len(
                    buckets
                )
            )
        )

        rng.shuffle(
            available_team_indices
        )

        seed_counts = [
            0
            for _ in buckets
        ]

        for player in seeded_players:
            candidates = [
                team_index
                for team_index
                in available_team_indices
                if (
                    len(
                        buckets[
                            team_index
                        ]
                    )
                    < capacities[
                        team_index
                    ]
                    and seed_counts[
                        team_index
                    ]
                    < (
                        self
                        ._maximum_seeded_players_per_team
                    )
                )
            ]

            if not candidates:
                raise RuntimeError(
                    "No valid team is available "
                    "for protected seed."
                )

            minimum_seed_count = min(
                seed_counts[
                    team_index
                ]
                for team_index
                in candidates
            )

            balanced_candidates = [
                team_index
                for team_index
                in candidates
                if (
                    seed_counts[
                        team_index
                    ]
                    == minimum_seed_count
                )
            ]

            selected_team_index = (
                rng.choice(
                    balanced_candidates
                )
            )

            buckets[
                selected_team_index
            ].append(
                player
            )

            seed_counts[
                selected_team_index
            ] += 1

    # ========================================================
    # Distribución de jugadores normales
    # ========================================================

    @staticmethod
    def _distribute_regular_players(
        players: list[Player],
        buckets: list[list[Player]],
        capacities: list[int],
        rng: random.Random,
    ) -> None:
        """
        Distribuye jugadores intentando llenar los equipos de forma
        equilibrada en cada paso.

        La seed controla los desempates.
        """
        for player in players:
            available = [
                team_index
                for team_index, bucket
                in enumerate(
                    buckets
                )
                if (
                    len(bucket)
                    < capacities[
                        team_index
                    ]
                )
            ]

            if not available:
                raise RuntimeError(
                    "No capacity remains while "
                    "redistributing players."
                )

            minimum_size = min(
                len(
                    buckets[
                        team_index
                    ]
                )
                for team_index
                in available
            )

            smallest_teams = [
                team_index
                for team_index
                in available
                if (
                    len(
                        buckets[
                            team_index
                        ]
                    )
                    == minimum_size
                )
            ]

            selected_team_index = (
                rng.choice(
                    smallest_teams
                )
            )

            buckets[
                selected_team_index
            ].append(
                player
            )

    # ========================================================
    # Seeds
    # ========================================================

    def _is_protected_seed(
        self,
        player: Player,
    ) -> bool:
        if (
            self._separated_seed_level
            is None
        ):
            return False

        seed = getattr(
            player,
            "seed",
            None,
        )

        if (
            seed is None
            or isinstance(
                seed,
                bool,
            )
        ):
            return False

        try:
            numeric_seed = int(
                float(
                    seed
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            return False

        return (
            numeric_seed
            == self._separated_seed_level
        )

    # ========================================================
    # Clonado de Team
    # ========================================================

    @classmethod
    def _clone_teams(
        cls,
        teams: Sequence[Team],
    ) -> list[Team]:
        """
        Crea nuevas instancias de Team conservando EXACTAMENTE las
        mismas instancias de Player.

        No usamos deepcopy porque eso duplicaría Player y podría romper
        referencias compartidas o caches.

        Se realiza:

            copy.copy(team)
                ↓
            nueva colección players
                ↓
            mismas instancias Player
        """
        result: list[
            Team
        ] = []

        for team in teams:
            cloned_team = copy.copy(
                team
            )

            cls._replace_team_players(
                cloned_team,
                list(
                    team.players
                ),
            )

            result.append(
                cloned_team
            )

        return result

    @staticmethod
    def _replace_team_players(
        team: Team,
        players: Sequence[Player],
    ) -> None:
        """
        Sustituye la colección interna de jugadores de Team.

        Soporta las dos implementaciones más habituales:

            team.players = [...]

        o:

            team._players = [...]

        El fallback a `_players` permite trabajar con una propiedad
        pública de solo lectura.

        Si Team cambia de contrato en el futuro, esta es la única
        función que tendremos que adaptar.
        """
        player_list = list(
            players
        )

        # ----------------------------------------------------
        # Intento mediante propiedad pública.
        # ----------------------------------------------------

        try:
            team.players = player_list

            return

        except (
            AttributeError,
            TypeError,
        ):
            pass

        # ----------------------------------------------------
        # Implementación con atributo interno.
        # ----------------------------------------------------

        if hasattr(
            team,
            "_players",
        ):
            try:
                team._players = player_list

                return

            except (
                AttributeError,
                TypeError,
            ):
                pass

        # ----------------------------------------------------
        # Último intento:
        # modificar la lista existente in-place.
        # ----------------------------------------------------

        existing_players = getattr(
            team,
            "players",
            None,
        )

        if isinstance(
            existing_players,
            list,
        ):
            existing_players[:] = (
                player_list
            )

            return

        raise TypeError(
            "Team players collection cannot be replaced. "
            "Adapt DeterministicRestartGenerator."
            "_replace_team_players() to the current Team model."
        )

    # ========================================================
    # Validación final
    # ========================================================

    def _validate_generated_solution(
        self,
        original: SolutionSignature,
        generated: Sequence[Team],
    ) -> None:
        generated_signature = (
            SolutionSignature.from_teams(
                generated
            )
        )

        if not original.same_player_pool(
            generated_signature
        ):
            raise RuntimeError(
                "Restart generation changed "
                "the player pool."
            )

        if (
            original.team_count
            != generated_signature.team_count
        ):
            raise RuntimeError(
                "Restart generation changed "
                "the number of teams."
            )

        if (
            sorted(
                original.team_sizes
            )
            != sorted(
                generated_signature.team_sizes
            )
        ):
            raise RuntimeError(
                "Restart generation changed "
                "team sizes."
            )

        self._validate_seed_distribution(
            generated
        )

    def _validate_seed_distribution(
        self,
        teams: Sequence[Team],
    ) -> None:
        if (
            self._separated_seed_level
            is None
        ):
            return

        for team_index, team in enumerate(
            teams,
            start=1,
        ):
            seeded_count = sum(
                1
                for player in team.players
                if self._is_protected_seed(
                    player
                )
            )

            if (
                seeded_count
                > (
                    self
                    ._maximum_seeded_players_per_team
                )
            ):
                raise RuntimeError(
                    f"Restart generated Team "
                    f"{team_index} with "
                    f"{seeded_count} protected seeds. "
                    f"Maximum allowed: "
                    f"{self._maximum_seeded_players_per_team}."
                )

    # ========================================================
    # Validaciones
    # ========================================================

    @staticmethod
    def _validate_teams(
        teams: Sequence[Team],
    ) -> list[Team]:
        if teams is None:
            raise ValueError(
                "teams cannot be None."
            )

        try:
            team_list = list(
                teams
            )

        except TypeError as error:
            raise TypeError(
                "teams must be iterable."
            ) from error

        if not team_list:
            raise ValueError(
                "At least one team is required."
            )

        for index, team in enumerate(
            team_list,
            start=1,
        ):
            if not isinstance(
                team,
                Team,
            ):
                raise TypeError(
                    f"Team {index} must be a "
                    "Team instance."
                )

            players = getattr(
                team,
                "players",
                None,
            )

            if players is None:
                raise ValueError(
                    f"Team {index} does not "
                    "provide players."
                )

        return team_list

    @staticmethod
    def _validate_integer(
        value: Any,
        field_name: str,
    ) -> int:
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

        return value

    @classmethod
    def _validate_non_negative_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int:
        validated = (
            cls._validate_integer(
                value=value,
                field_name=field_name,
            )
        )

        if validated < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return validated

    @classmethod
    def _validate_positive_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int:
        validated = (
            cls._validate_integer(
                value=value,
                field_name=field_name,
            )
        )

        if validated <= 0:
            raise ValueError(
                f"{field_name} must be "
                "greater than zero."
            )

        return validated

    @classmethod
    def _validate_optional_integer(
        cls,
        value: Any,
        field_name: str,
    ) -> int | None:
        if value is None:
            return None

        return cls._validate_integer(
            value=value,
            field_name=field_name,
        )

    @staticmethod
    def _validate_ratio(
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
                (
                    int,
                    float,
                ),
            )
        ):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        numeric = float(
            value
        )

        if not 0.0 < numeric <= 1.0:
            raise ValueError(
                f"{field_name} must be "
                "greater than 0 and at most 1."
            )

        return numeric

    # ========================================================
    # Propiedades
    # ========================================================

    @property
    def separated_seed_level(
        self,
    ) -> int | None:
        return (
            self._separated_seed_level
        )

    @property
    def maximum_seeded_players_per_team(
        self,
    ) -> int:
        return (
            self
            ._maximum_seeded_players_per_team
        )

    @property
    def minimum_swaps(
        self,
    ) -> int:
        return self._minimum_swaps

    @property
    def maximum_swaps(
        self,
    ) -> int:
        return self._maximum_swaps

    @property
    def partial_redistribution_ratio(
        self,
    ) -> float:
        return (
            self._partial_redistribution_ratio
        )

    # ========================================================
    # Representación
    # ========================================================

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"seed_level="
            f"{self._separated_seed_level!r}, "
            f"max_seeded_per_team="
            f"{self._maximum_seeded_players_per_team}, "
            f"swaps="
            f"{self._minimum_swaps}-"
            f"{self._maximum_swaps}, "
            f"partial_ratio="
            f"{self._partial_redistribution_ratio:.2f})"
        )
