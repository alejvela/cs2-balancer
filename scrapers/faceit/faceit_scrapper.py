from __future__ import annotations

import csv
import re
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scrapers.faceit.faceit_api_client import (
    FaceitApiClient,
)
from scrapers.faceit.faceit_player_record_map import (
    FaceitPlayerRecordMapper,
)
from scrapers.player_record import PlayerRecord


class FaceitScraper:
    """
    Importa jugadores definidos en un CSV y obtiene sus estadísticas
    desde FACEIT.

    Flujo:

        players.csv
            ↓
        lectura y validación de filas
            ↓
        FaceitApiClient
            ↓
        FaceitPlayerRecordMapper
            ↓
        PlayerRecord[]

    El CSV de entrada puede contener:

        Nick:
            Nombre utilizado dentro del evento.

        FaceitNickname:
            Nombre del perfil de FACEIT.

        Role:
            Rol opcional del jugador.

        Seed:
            Nivel de cabeza de serie opcional.

        Team:
            Número de equipo predeterminado opcional.

    La columna Team no se utiliza para formar equipos dentro de esta
    clase. Únicamente se conserva para que posteriormente pueda ser
    utilizada por PreassignedTeamGenerator.

    En modo estricto:

        El primer error detiene el proceso.

    En modo no estricto:

        Se devuelve un PlayerRecord fallido y se continúa con el resto
        de jugadores.
    """

    FIELD_ALIASES: dict[str, tuple[str, ...]] = {
        "nick": (
            "nick",
            "nickname",
            "player",
            "player_name",
            "display_name",
        ),
        "faceit_nickname": (
            "faceit_nickname",
            "faceitnickname",
            "faceit_name",
            "faceitname",
            "faceit",
        ),
        "game_player_id": (
            "game_player_id",
            "gameplayerid",
            "steam_id",
            "steamid",
            "steam_id_64",
            "steamid64",
        ),
        "role": (
            "role",
            "player_role",
            "playerrole",
        ),
        "seed": (
            "seed",
            "seed_number",
            "seednumber",
            "seed_level",
            "seedlevel",
        ),
        "team_number": (
            "team",
            "team_number",
            "teamnumber",
            "team_id",
            "teamid",
            "assigned_team",
            "assignedteam",
            "equipo",
            "numero_equipo",
        ),
    }

    REQUIRED_FIELDS = (
        "nick",
    )

    def __init__(
        self,
        client: FaceitApiClient,
        mapper: FaceitPlayerRecordMapper,
        recent_matches: int = 30,
        strict: bool = False,
        delay: float = 0.0,
        maximum_seed_one_players: int | None = None,
    ) -> None:
        if client is None:
            raise ValueError(
                "client cannot be None."
            )

        if not isinstance(
            client,
            FaceitApiClient,
        ):
            raise TypeError(
                "client must be a FaceitApiClient instance."
            )

        if mapper is None:
            raise ValueError(
                "mapper cannot be None."
            )

        if not isinstance(
            mapper,
            FaceitPlayerRecordMapper,
        ):
            raise TypeError(
                "mapper must be a FaceitPlayerRecordMapper instance."
            )

        self._recent_matches = self._validate_non_negative_integer(
            value=recent_matches,
            field_name="recent_matches",
        )

        if not isinstance(
            strict,
            bool,
        ):
            raise TypeError(
                "strict must be a boolean."
            )

        self._delay = self._validate_non_negative_number(
            value=delay,
            field_name="delay",
        )

        if maximum_seed_one_players is not None:
            maximum_seed_one_players = (
                self._validate_positive_integer(
                    value=maximum_seed_one_players,
                    field_name="maximum_seed_one_players",
                )
            )

        self._client = client
        self._mapper = mapper
        self._strict = strict
        self._maximum_seed_one_players = (
            maximum_seed_one_players
        )

        self._errors: list[dict[str, Any]] = []

    def scrape(
        self,
        source: str | Path,
    ) -> list[PlayerRecord]:
        """
        Lee el CSV de entrada y genera un PlayerRecord por jugador.

        Args:
            source:
                Ruta al CSV que contiene los jugadores.

        Returns:
            Lista de PlayerRecord válidos y, cuando strict=False,
            registros fallidos.

        Raises:
            RuntimeError:
                Si strict=True y se produce un error en alguna fila.
        """
        source_path = self._validate_source(
            source
        )

        self._errors.clear()

        rows = self._read_csv(
            source_path
        )

        if not rows:
            raise ValueError(
                "The player CSV does not contain data rows."
            )

        self._validate_seed_configuration(
            rows
        )

        self._validate_team_assignment_consistency(
            rows
        )

        records: list[PlayerRecord] = []

        seen_event_nicks: set[str] = set()
        seen_faceit_nicknames: set[str] = set()
        seen_game_player_ids: set[str] = set()

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            requested_nickname = self._required_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["nick"],
                ),
                field_name="Nick",
                row_number=row_number,
            )

            faceit_nickname = self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["faceit_nickname"],
                )
            )

            game_player_id = self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["game_player_id"],
                )
            )

            role = self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["role"],
                )
            )

            seed = self._optional_positive_integer(
                value=self._find_value(
                    row,
                    self.FIELD_ALIASES["seed"],
                ),
                field_name="Seed",
                row_number=row_number,
            )

            team_number = self._optional_positive_integer(
                value=self._find_value(
                    row,
                    self.FIELD_ALIASES["team_number"],
                ),
                field_name="Team",
                row_number=row_number,
            )

            try:
                self._validate_unique_input_identity(
                    requested_nickname=requested_nickname,
                    faceit_nickname=faceit_nickname,
                    game_player_id=game_player_id,
                    seen_event_nicks=seen_event_nicks,
                    seen_faceit_nicknames=seen_faceit_nicknames,
                    seen_game_player_ids=seen_game_player_ids,
                )

                record = self._scrape_player(
                    requested_nickname=requested_nickname,
                    faceit_nickname=faceit_nickname,
                    game_player_id=game_player_id,
                    role=role,
                    seed=seed,
                    team_number=team_number,
                )

                records.append(
                    record
                )

                self._register_input_identity(
                    requested_nickname=requested_nickname,
                    faceit_nickname=faceit_nickname,
                    game_player_id=game_player_id,
                    seen_event_nicks=seen_event_nicks,
                    seen_faceit_nicknames=seen_faceit_nicknames,
                    seen_game_player_ids=seen_game_player_ids,
                )

            except (
                TypeError,
                ValueError,
                RuntimeError,
            ) as error:
                error_information = {
                    "row": row_number,
                    "nick": requested_nickname,
                    "faceit_nickname": faceit_nickname,
                    "game_player_id": game_player_id,
                    "role": role,
                    "seed": seed,
                    "team_number": team_number,
                    "error": str(error),
                }

                self._errors.append(
                    error_information
                )

                if self._strict:
                    raise RuntimeError(
                        f"Could not scrape row {row_number} "
                        f"for player '{requested_nickname}': "
                        f"{error}"
                    ) from error

                records.append(
                    PlayerRecord.failed(
                        nickname=requested_nickname,
                        error=str(error),
                        source="FACEIT",
                        seed=seed,
                        team_number=team_number,
                    )
                )

            self._wait_between_requests(
                current_row=row_number,
                total_rows=len(rows),
            )

        if not records:
            raise RuntimeError(
                "No PlayerRecord instances were generated."
            )

        return records

    def _scrape_player(
        self,
        requested_nickname: str,
        faceit_nickname: str | None,
        game_player_id: str | None,
        role: str | None,
        seed: int | None,
        team_number: int | None,
    ) -> PlayerRecord:
        """
        Obtiene el bundle de un jugador y lo convierte en PlayerRecord.

        Prioridad de búsqueda:

            1. FaceitNickname.
            2. game_player_id / Steam ID.
            3. Nick del evento.
        """
        lookup_nickname = (
            faceit_nickname
            or requested_nickname
        )

        if faceit_nickname is not None:
            bundle = self._client.get_player_bundle_by_nickname(
                nickname=faceit_nickname,
                recent_matches=self._recent_matches,
            )

        elif game_player_id is not None:
            bundle = self._client.get_player_bundle_by_game_player_id(
                game_player_id=game_player_id,
                recent_matches=self._recent_matches,
            )

        else:
            bundle = self._client.get_player_bundle_by_nickname(
                nickname=lookup_nickname,
                recent_matches=self._recent_matches,
            )

        if not isinstance(
            bundle,
            Mapping,
        ):
            raise TypeError(
                "FaceitApiClient must return a mapping bundle."
            )

        return self._mapper.map_bundle(
            bundle=bundle,
            requested_nickname=requested_nickname,
            role=role,
            seed=seed,
            team_number=team_number,
        )

    def _validate_seed_configuration(
        self,
        rows: list[dict[str, Any]],
    ) -> None:
        """
        Comprueba opcionalmente cuántos jugadores tienen Seed=1.

        Esta validación se aplica sobre el CSV de entrada, antes de
        consultar FACEIT.
        """
        if self._maximum_seed_one_players is None:
            return

        seed_one_players: list[str] = []

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            seed = self._optional_positive_integer(
                value=self._find_value(
                    row,
                    self.FIELD_ALIASES["seed"],
                ),
                field_name="Seed",
                row_number=row_number,
            )

            if seed != 1:
                continue

            nickname = self._optional_text(
                self._find_value(
                    row,
                    self.FIELD_ALIASES["nick"],
                )
            )

            seed_one_players.append(
                nickname or f"Row {row_number}"
            )

        if (
            len(seed_one_players)
            > self._maximum_seed_one_players
        ):
            raise ValueError(
                "The number of Seed=1 players exceeds the "
                "configured maximum. "
                f"Maximum: {self._maximum_seed_one_players}. "
                f"Found: {len(seed_one_players)}. "
                f"Players: {seed_one_players}."
            )

    def _validate_team_assignment_consistency(
        self,
        rows: list[dict[str, Any]],
    ) -> None:
        """
        Detecta una asignación parcial de equipos.

        Se permiten dos estados:

            - Ningún jugador tiene Team.
            - Todos los jugadores tienen Team.

        Una mezcla de filas con y sin Team normalmente representa un
        error en el CSV y produciría una evaluación incompleta.

        El rango concreto de equipos no se valida aquí, porque depende
        del número de equipos configurado para el evento.
        """
        assigned_rows: list[int] = []
        unassigned_rows: list[int] = []

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            team_number = self._optional_positive_integer(
                value=self._find_value(
                    row,
                    self.FIELD_ALIASES["team_number"],
                ),
                field_name="Team",
                row_number=row_number,
            )

            if team_number is None:
                unassigned_rows.append(
                    row_number
                )

            else:
                assigned_rows.append(
                    row_number
                )

        if not assigned_rows:
            return

        if not unassigned_rows:
            return

        raise ValueError(
            "Team assignment is incomplete. When using predefined "
            "teams, every player must contain a Team value. "
            f"Assigned rows: {assigned_rows}. "
            f"Rows without Team: {unassigned_rows}."
        )

    @staticmethod
    def _validate_unique_input_identity(
        requested_nickname: str,
        faceit_nickname: str | None,
        game_player_id: str | None,
        seen_event_nicks: set[str],
        seen_faceit_nicknames: set[str],
        seen_game_player_ids: set[str],
    ) -> None:
        normalized_event_nick = (
            requested_nickname
            .strip()
            .casefold()
        )

        if normalized_event_nick in seen_event_nicks:
            raise ValueError(
                f"Duplicated event Nick "
                f"'{requested_nickname}'."
            )

        if faceit_nickname:
            normalized_faceit_nickname = (
                faceit_nickname
                .strip()
                .casefold()
            )

            if (
                normalized_faceit_nickname
                in seen_faceit_nicknames
            ):
                raise ValueError(
                    f"Duplicated FaceitNickname "
                    f"'{faceit_nickname}'."
                )

        if game_player_id:
            normalized_game_player_id = (
                game_player_id
                .strip()
                .casefold()
            )

            if (
                normalized_game_player_id
                in seen_game_player_ids
            ):
                raise ValueError(
                    f"Duplicated game player ID "
                    f"'{game_player_id}'."
                )

    @staticmethod
    def _register_input_identity(
        requested_nickname: str,
        faceit_nickname: str | None,
        game_player_id: str | None,
        seen_event_nicks: set[str],
        seen_faceit_nicknames: set[str],
        seen_game_player_ids: set[str],
    ) -> None:
        seen_event_nicks.add(
            requested_nickname
            .strip()
            .casefold()
        )

        if faceit_nickname:
            seen_faceit_nicknames.add(
                faceit_nickname
                .strip()
                .casefold()
            )

        if game_player_id:
            seen_game_player_ids.add(
                game_player_id
                .strip()
                .casefold()
            )

    def _read_csv(
        self,
        source: Path,
    ) -> list[dict[str, Any]]:
        """
        Lee el CSV detectando coma, punto y coma o tabulador.
        """
        with source.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            sample = file.read(
                4096
            )

            file.seek(0)

            try:
                dialect = csv.Sniffer().sniff(
                    sample,
                    delimiters=",;\t",
                )

            except csv.Error:
                dialect = csv.excel

            reader = csv.DictReader(
                file,
                dialect=dialect,
            )

            if not reader.fieldnames:
                raise ValueError(
                    "The CSV does not contain headers."
                )

            normalized_headers = {
                self._normalize_key(header)
                for header in reader.fieldnames
                if header is not None
            }

            self._validate_headers(
                normalized_headers
            )

            return [
                self._normalize_row(
                    row
                )
                for row in reader
                if self._row_contains_data(
                    row
                )
            ]

    def _validate_headers(
        self,
        headers: set[str],
    ) -> None:
        """
        Valida únicamente las cabeceras obligatorias.

        Team sigue siendo opcional para mantener el modo automático.
        """
        for required_field in self.REQUIRED_FIELDS:
            aliases = self.FIELD_ALIASES[
                required_field
            ]

            normalized_aliases = {
                self._normalize_key(alias)
                for alias in aliases
            }

            if headers.isdisjoint(
                normalized_aliases
            ):
                raise ValueError(
                    "The CSV must contain a valid "
                    f"'{required_field}' column."
                )

    @classmethod
    def _normalize_row(
        cls,
        row: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            cls._normalize_key(key): value
            for key, value in row.items()
            if key is not None
        }

    @staticmethod
    def _row_contains_data(
        row: Mapping[str, Any],
    ) -> bool:
        return any(
            value is not None
            and str(value).strip()
            for value in row.values()
        )

    @classmethod
    def _find_value(
        cls,
        row: Mapping[str, Any],
        aliases: tuple[str, ...],
    ) -> Any:
        for alias in aliases:
            normalized_alias = cls._normalize_key(
                alias
            )

            if normalized_alias in row:
                return row[
                    normalized_alias
                ]

        return None

    @staticmethod
    def _normalize_key(
        value: Any,
    ) -> str:
        """
        Convierte cabeceras como:

            FaceitNickname
                -> faceit_nickname

            TeamNumber
                -> team_number

            AssignedTeam
                -> assigned_team
        """
        text = str(
            value
        ).strip()

        text = re.sub(
            r"(?<=[a-z0-9])(?=[A-Z])",
            "_",
            text,
        )

        text = re.sub(
            r"(?<=[A-Z])(?=[A-Z][a-z])",
            "_",
            text,
        )

        text = text.casefold()

        text = re.sub(
            r"[^a-z0-9]+",
            "_",
            text,
        )

        return text.strip(
            "_"
        )

    @staticmethod
    def _required_text(
        value: Any,
        field_name: str,
        row_number: int,
    ) -> str:
        text = FaceitScraper._optional_text(
            value
        )

        if text is None:
            raise ValueError(
                f"{field_name} is required "
                f"at row {row_number}."
            )

        return text

    @staticmethod
    def _optional_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = str(
            value
        ).strip()

        return text or None

    @staticmethod
    def _optional_positive_integer(
        value: Any,
        field_name: str,
        row_number: int,
    ) -> int | None:
        """
        Convierte una celda opcional en entero positivo.

        Se utiliza para Seed y Team.
        """
        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be an integer "
                f"at row {row_number}."
            )

        text = str(
            value
        ).strip()

        if not text:
            return None

        try:
            number = float(
                text.replace(",", ".")
            )

        except ValueError as error:
            raise ValueError(
                f"{field_name} must be an integer "
                f"at row {row_number}, "
                f"received {value!r}."
            ) from error

        if not number.is_integer():
            raise ValueError(
                f"{field_name} must be an integer "
                f"at row {row_number}, "
                f"received {value!r}."
            )

        integer = int(
            number
        )

        if integer <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero "
                f"at row {row_number}."
            )

        return integer

    @staticmethod
    def _validate_non_negative_integer(
        value: Any,
        field_name: str,
    ) -> int:
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

        return value

    @staticmethod
    def _validate_positive_integer(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
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
    def _validate_non_negative_number(
        value: Any,
        field_name: str,
    ) -> float:
        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be numeric."
            )

        try:
            numeric_value = float(
                value
            )

        except (
            TypeError,
            ValueError,
        ) as error:
            raise TypeError(
                f"{field_name} must be numeric."
            ) from error

        if numeric_value < 0.0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return numeric_value

    @staticmethod
    def _validate_source(
        source: str | Path,
    ) -> Path:
        if source is None:
            raise ValueError(
                "source cannot be None."
            )

        if not isinstance(
            source,
            (str, Path),
        ):
            raise TypeError(
                "source must be a string or Path."
            )

        source_path = Path(
            source
        )

        if not source_path.exists():
            raise FileNotFoundError(
                f"Player file not found: "
                f"{source_path.resolve()}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"Player source is not a file: "
                f"{source_path.resolve()}"
            )

        if source_path.suffix.casefold() != ".csv":
            raise ValueError(
                "FaceitScraper only supports CSV files."
            )

        return source_path

    def _wait_between_requests(
        self,
        current_row: int,
        total_rows: int,
    ) -> None:
        """
        Aplica una pausa entre jugadores, pero no después del último.
        """
        if self._delay <= 0.0:
            return

        if current_row >= total_rows:
            return

        time.sleep(
            self._delay
        )

    @property
    def client(
        self,
    ) -> FaceitApiClient:
        return self._client

    @property
    def mapper(
        self,
    ) -> FaceitPlayerRecordMapper:
        return self._mapper

    @property
    def recent_matches(
        self,
    ) -> int:
        return self._recent_matches

    @property
    def strict(
        self,
    ) -> bool:
        return self._strict

    @property
    def delay(
        self,
    ) -> float:
        return self._delay

    @property
    def maximum_seed_one_players(
        self,
    ) -> int | None:
        return self._maximum_seed_one_players

    @property
    def errors(
        self,
    ) -> tuple[dict[str, Any], ...]:
        return tuple(
            self._errors
        )

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"recent_matches={self._recent_matches}, "
            f"strict={self._strict}, "
            f"delay={self._delay:.2f}, "
            f"maximum_seed_one_players="
            f"{self._maximum_seed_one_players!r})"
        )
