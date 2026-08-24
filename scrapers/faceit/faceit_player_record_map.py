from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from statistics import mean
from typing import Any

from scrapers.player_record import (
    ActivityRecord,
    PlayerRecord,
)


class FaceitPlayerRecordMapper:
    """
    Convierte las respuestas obtenidas desde FACEIT en PlayerRecord.

    Responsabilidades:

        - Extraer ELO y nivel desde games[game_id].
        - Extraer estadísticas lifetime.
        - Calcular estadísticas recientes.
        - Conservar la actividad de los últimos 90 días.
        - Mantener Seed, Role y Team procedentes del CSV de entrada.
        - Soportar el fallback de CS2 a CS:GO.

    El mapper no decide el equipo del jugador. Únicamente conserva
    `team_number`, que procede de la configuración del evento.
    """

    LIFETIME_ALIASES: dict[str, tuple[str, ...]] = {
        "matches": (
            "matches",
            "match count",
            "games",
            "games played",
        ),
        "wins": (
            "wins",
            "victories",
        ),
        "winrate": (
            "win rate %",
            "win rate",
            "winrate",
            "winrate %",
        ),
        "kd": (
            "average k/d ratio",
            "average kd ratio",
            "avg k/d ratio",
            "avg kd",
            "k/d ratio",
            "kd ratio",
            "kd",
        ),
        "kpr": (
            "average kills per round",
            "avg kills per round",
            "kills per round",
            "kpr",
        ),
        "dpr": (
            "average deaths per round",
            "avg deaths per round",
            "deaths per round",
            "dpr",
        ),
        "adr": (
            "average adr",
            "avg adr",
            "average damage per round",
            "adr",
        ),
        "hs": (
            "average headshots %",
            "average headshot %",
            "avg headshots %",
            "headshots %",
            "headshot %",
            "hs %",
            "hs",
        ),
        "kast": (
            "average kast %",
            "kast %",
            "kast",
        ),
        "rating": (
            "average rating",
            "rating",
        ),
        "clutch": (
            "clutch win rate %",
            "clutch %",
            "clutch",
        ),
    }

    MATCH_ALIASES: dict[str, tuple[str, ...]] = {
        "kills": (
            "kills",
        ),
        "deaths": (
            "deaths",
        ),
        "rounds": (
            "rounds",
            "rounds played",
        ),
        "kd": (
            "k/d ratio",
            "kd ratio",
            "kd",
        ),
        "kpr": (
            "kills per round",
            "kpr",
        ),
        "dpr": (
            "deaths per round",
            "dpr",
        ),
        "adr": (
            "adr",
            "average damage per round",
        ),
        "hs": (
            "headshots %",
            "headshot %",
            "hs %",
            "hs",
        ),
        "kast": (
            "kast %",
            "kast",
        ),
        "rating": (
            "rating",
        ),
        "clutch": (
            "clutch %",
            "clutch win rate %",
            "clutch",
        ),
        "result": (
            "result",
            "win",
            "won",
        ),
    }

    def __init__(
        self,
        game_id: str = "cs2",
        source_name: str = "FACEIT",
    ) -> None:
        self._game_id = self._validate_text(
            game_id,
            "game_id",
        )

        self._source_name = self._validate_text(
            source_name,
            "source_name",
        )

    def map_bundle(
        self,
        bundle: Mapping[str, Any],
        requested_nickname: str | None = None,
        role: str | None = None,
        seed: int | None = None,
        team_number: int | None = None,
    ) -> PlayerRecord:
        """
        Convierte un bundle de FACEIT en PlayerRecord.

        Bundle esperado:

            {
                "player": {...},
                "game_id": "cs2" | "csgo",
                "statistics": {...},
                "recent_statistics": {
                    "items": [...]
                },
                "activity_statistics": {
                    "matches_0_7_days": 5,
                    "matches_8_30_days": 12,
                    "matches_31_90_days": 20,
                    "total_matches_90_days": 37,
                    "last_match_at": 1785800000,
                    "days_since_last_match": 1,
                    "history_complete": True
                }
            }

        `team_number` no se obtiene desde FACEIT. Procede exclusivamente
        del CSV inicial y se conserva para el modo de evaluación de
        equipos predeterminados.
        """
        if bundle is None:
            raise ValueError(
                "bundle cannot be None."
            )

        if not isinstance(bundle, Mapping):
            raise TypeError(
                "bundle must be a mapping."
            )

        player = self._require_mapping(
            bundle.get("player"),
            "bundle.player",
        )

        statistics = self._optional_mapping(
            bundle.get("statistics")
        )

        recent_statistics = self._optional_mapping(
            bundle.get("recent_statistics")
        )

        activity_statistics = self._optional_mapping(
            bundle.get("activity_statistics")
        )

        activity = ActivityRecord.from_mapping(
            activity_statistics
        )

        resolved_game_id = self._optional_text(
            bundle.get("game_id")
        )

        if resolved_game_id is None:
            resolved_game_id = self._game_id

        game_data = self._extract_game_data(
            player=player,
            game_id=resolved_game_id,
        )

        lifetime = self._optional_mapping(
            statistics.get("lifetime")
        )

        faceit_nickname = self._optional_text(
            player.get("nickname")
        )

        nickname = (
            self._optional_text(requested_nickname)
            or faceit_nickname
        )

        if nickname is None:
            raise ValueError(
                "FACEIT did not return a valid nickname."
            )

        self._required_text(
            player.get("player_id"),
            "player.player_id",
        )

        steam_id = self._first_text(
            game_data.get("game_player_id"),
            player.get("steam_id_64"),
            player.get("steam_id"),
        )

        elo = self._optional_int(
            game_data.get("faceit_elo")
        )

        faceit_level = self._optional_int(
            game_data.get("skill_level")
        )

        lifetime_values = self._extract_lifetime_values(
            lifetime
        )

        recent_values = self._extract_recent_values(
            recent_statistics
        )

        profile_nickname = (
            faceit_nickname
            or nickname
        )

        profile_url = self._build_profile_url(
            profile_nickname
        )

        source = (
            self._source_name
            if resolved_game_id == "cs2"
            else (
                f"{self._source_name} "
                "CS:GO fallback"
            )
        )

        validated_seed = self._validate_optional_positive_integer(
            value=seed,
            field_name="seed",
        )

        validated_team_number = (
            self._validate_optional_positive_integer(
                value=team_number,
                field_name="team_number",
            )
        )

        return PlayerRecord(
            nickname=nickname,

            profile_url=profile_url,
            steam_id=steam_id,
            faceit_url=profile_url,
            csstats_url=None,

            elo=elo,
            faceit_level=faceit_level,

            kd=self._prefer_recent(
                recent_values.get("kd"),
                lifetime_values.get("kd"),
            ),

            rating=self._prefer_recent(
                recent_values.get("rating"),
                lifetime_values.get("rating"),
            ),

            adr=self._prefer_recent(
                recent_values.get("adr"),
                lifetime_values.get("adr"),
            ),

            kpr=self._prefer_recent(
                recent_values.get("kpr"),
                lifetime_values.get("kpr"),
            ),

            dpr=self._prefer_recent(
                recent_values.get("dpr"),
                lifetime_values.get("dpr"),
            ),

            hs=self._prefer_recent(
                recent_values.get("hs"),
                lifetime_values.get("hs"),
            ),

            kast=self._prefer_recent(
                recent_values.get("kast"),
                lifetime_values.get("kast"),
            ),

            winrate=lifetime_values.get(
                "winrate"
            ),

            recent_winrate=recent_values.get(
                "winrate"
            ),

            clutch=self._prefer_recent(
                recent_values.get("clutch"),
                lifetime_values.get("clutch"),
            ),

            matches=self._optional_int(
                lifetime_values.get("matches")
            ),

            activity=activity,

            banned_matches_percentage=None,

            role=self._optional_text(role),
            seed=validated_seed,
            team_number=validated_team_number,

            source=source,
        )

    def map_player_and_stats(
        self,
        player: Mapping[str, Any],
        statistics: Mapping[str, Any] | None = None,
        recent_statistics: Mapping[str, Any] | None = None,
        activity_statistics: Mapping[str, Any] | None = None,
        requested_nickname: str | None = None,
        role: str | None = None,
        seed: int | None = None,
        team_number: int | None = None,
        game_id: str | None = None,
    ) -> PlayerRecord:
        """
        Método auxiliar para mapear respuestas proporcionadas
        individualmente.
        """
        return self.map_bundle(
            bundle={
                "player": player,
                "game_id": (
                    game_id
                    or self._game_id
                ),
                "statistics": (
                    statistics
                    or {}
                ),
                "recent_statistics": (
                    recent_statistics
                    or {"items": []}
                ),
                "activity_statistics": (
                    activity_statistics
                    or {}
                ),
            },
            requested_nickname=requested_nickname,
            role=role,
            seed=seed,
            team_number=team_number,
        )

    def _extract_game_data(
        self,
        player: Mapping[str, Any],
        game_id: str,
    ) -> Mapping[str, Any]:
        """
        Extrae games[game_id].
        """
        games = self._optional_mapping(
            player.get("games")
        )

        game_data = games.get(
            game_id
        )

        if not isinstance(
            game_data,
            Mapping,
        ):
            available_games = ", ".join(
                str(key)
                for key in games.keys()
            )

            raise ValueError(
                f"The player does not contain data for "
                f"'{game_id}'. Available games: "
                f"{available_games or 'none'}."
            )

        return game_data

    def _extract_lifetime_values(
        self,
        lifetime: Mapping[str, Any],
    ) -> dict[str, float | int | None]:
        """
        Extrae y normaliza las estadísticas acumuladas.
        """
        normalized = self._normalize_mapping(
            lifetime
        )

        matches = self._find_number(
            normalized,
            self.LIFETIME_ALIASES["matches"],
        )

        wins = self._find_number(
            normalized,
            self.LIFETIME_ALIASES["wins"],
        )

        winrate = self._find_number(
            normalized,
            self.LIFETIME_ALIASES["winrate"],
        )

        if (
            winrate is None
            and matches is not None
            and matches > 0
            and wins is not None
        ):
            winrate = (
                wins
                / matches
                * 100.0
            )

        return {
            "matches": (
                int(matches)
                if matches is not None
                else None
            ),
            "wins": (
                int(wins)
                if wins is not None
                else None
            ),
            "winrate": self._percentage(
                winrate
            ),
            "kd": self._find_number(
                normalized,
                self.LIFETIME_ALIASES["kd"],
            ),
            "kpr": self._find_number(
                normalized,
                self.LIFETIME_ALIASES["kpr"],
            ),
            "dpr": self._find_number(
                normalized,
                self.LIFETIME_ALIASES["dpr"],
            ),
            "adr": self._find_number(
                normalized,
                self.LIFETIME_ALIASES["adr"],
            ),
            "hs": self._percentage(
                self._find_number(
                    normalized,
                    self.LIFETIME_ALIASES["hs"],
                )
            ),
            "kast": self._percentage(
                self._find_number(
                    normalized,
                    self.LIFETIME_ALIASES["kast"],
                )
            ),
            "rating": self._find_number(
                normalized,
                self.LIFETIME_ALIASES["rating"],
            ),
            "clutch": self._percentage(
                self._find_number(
                    normalized,
                    self.LIFETIME_ALIASES["clutch"],
                )
            ),
        }

    def _extract_recent_values(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, float | None]:
        """
        Calcula las medias de las partidas recientes.

        Cuando no existen partidas recientes, devuelve None para cada
        métrica y el mapper utilizará los valores lifetime.
        """
        raw_items = payload.get(
            "items",
            [],
        )

        if not isinstance(
            raw_items,
            list,
        ):
            return self._empty_recent_values()

        if not raw_items:
            return self._empty_recent_values()

        matches: list[dict[str, float | None]] = []

        for item in raw_items:
            if not isinstance(
                item,
                Mapping,
            ):
                continue

            stats = item.get(
                "stats"
            )

            if not isinstance(
                stats,
                Mapping,
            ):
                continue

            matches.append(
                self._parse_match_stats(
                    stats
                )
            )

        if not matches:
            return self._empty_recent_values()

        wins = [
            match["win"]
            for match in matches
            if match.get("win") is not None
        ]

        return {
            "kd": self._average_field(
                matches,
                "kd",
            ),
            "kpr": self._average_field(
                matches,
                "kpr",
            ),
            "dpr": self._average_field(
                matches,
                "dpr",
            ),
            "adr": self._average_field(
                matches,
                "adr",
            ),
            "hs": self._percentage(
                self._average_field(
                    matches,
                    "hs",
                )
            ),
            "kast": self._percentage(
                self._average_field(
                    matches,
                    "kast",
                )
            ),
            "rating": self._average_field(
                matches,
                "rating",
            ),
            "clutch": self._percentage(
                self._average_field(
                    matches,
                    "clutch",
                )
            ),
            "winrate": (
                float(
                    mean(wins)
                    * 100.0
                )
                if wins
                else None
            ),
        }

    def _parse_match_stats(
        self,
        stats: Mapping[str, Any],
    ) -> dict[str, float | None]:
        """
        Normaliza las estadísticas de una partida individual.
        """
        normalized = self._normalize_mapping(
            stats
        )

        kills = self._find_number(
            normalized,
            self.MATCH_ALIASES["kills"],
        )

        deaths = self._find_number(
            normalized,
            self.MATCH_ALIASES["deaths"],
        )

        rounds = self._find_number(
            normalized,
            self.MATCH_ALIASES["rounds"],
        )

        kd = self._find_number(
            normalized,
            self.MATCH_ALIASES["kd"],
        )

        if (
            kd is None
            and kills is not None
            and deaths is not None
        ):
            kd = (
                kills / deaths
                if deaths > 0
                else kills
            )

        kpr = self._find_number(
            normalized,
            self.MATCH_ALIASES["kpr"],
        )

        if (
            kpr is None
            and kills is not None
            and rounds is not None
            and rounds > 0
        ):
            kpr = (
                kills
                / rounds
            )

        dpr = self._find_number(
            normalized,
            self.MATCH_ALIASES["dpr"],
        )

        if (
            dpr is None
            and deaths is not None
            and rounds is not None
            and rounds > 0
        ):
            dpr = (
                deaths
                / rounds
            )

        return {
            "kd": kd,
            "kpr": kpr,
            "dpr": dpr,
            "adr": self._find_number(
                normalized,
                self.MATCH_ALIASES["adr"],
            ),
            "hs": self._find_number(
                normalized,
                self.MATCH_ALIASES["hs"],
            ),
            "kast": self._find_number(
                normalized,
                self.MATCH_ALIASES["kast"],
            ),
            "rating": self._find_number(
                normalized,
                self.MATCH_ALIASES["rating"],
            ),
            "clutch": self._find_number(
                normalized,
                self.MATCH_ALIASES["clutch"],
            ),
            "win": self._parse_result(
                self._find_raw_value(
                    normalized,
                    self.MATCH_ALIASES["result"],
                )
            ),
        }

    @staticmethod
    def _average_field(
        matches: Iterable[Mapping[str, Any]],
        field: str,
    ) -> float | None:
        values = [
            float(match[field])
            for match in matches
            if match.get(field) is not None
        ]

        if not values:
            return None

        return float(
            mean(values)
        )

    @staticmethod
    def _parse_result(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return (
                1.0
                if value
                else 0.0
            )

        if isinstance(value, (int, float)):
            return (
                1.0
                if float(value) > 0
                else 0.0
            )

        text = str(
            value
        ).strip().casefold()

        if text in {
            "1",
            "true",
            "win",
            "won",
            "victory",
            "w",
        }:
            return 1.0

        if text in {
            "0",
            "false",
            "loss",
            "lost",
            "defeat",
            "l",
        }:
            return 0.0

        return None

    @classmethod
    def _find_number(
        cls,
        values: Mapping[str, Any],
        aliases: Iterable[str],
    ) -> float | None:
        return cls._to_float(
            cls._find_raw_value(
                values,
                aliases,
            )
        )

    @classmethod
    def _find_raw_value(
        cls,
        values: Mapping[str, Any],
        aliases: Iterable[str],
    ) -> Any:
        for alias in aliases:
            normalized_alias = cls._normalize_key(
                alias
            )

            if normalized_alias in values:
                return values[
                    normalized_alias
                ]

        return None

    @classmethod
    def _normalize_mapping(
        cls,
        values: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {
            cls._normalize_key(key): value
            for key, value in values.items()
        }

    @staticmethod
    def _normalize_key(
        value: Any,
    ) -> str:
        text = str(
            value
        ).strip().casefold()

        return re.sub(
            r"[^a-z0-9]+",
            "_",
            text,
        ).strip("_")

    @staticmethod
    def _to_float(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return float(
                value
            )

        if isinstance(value, (int, float)):
            return float(
                value
            )

        text = (
            str(value)
            .strip()
            .replace("\u00a0", "")
            .replace(" ", "")
            .replace("%", "")
        )

        if not text:
            return None

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = (
                    text
                    .replace(".", "")
                    .replace(",", ".")
                )
            else:
                text = text.replace(
                    ",",
                    "",
                )

        else:
            text = text.replace(
                ",",
                ".",
            )

        try:
            return float(
                text
            )

        except ValueError:
            return None

    @classmethod
    def _optional_int(
        cls,
        value: Any,
    ) -> int | None:
        number = cls._to_float(
            value
        )

        if number is None:
            return None

        return int(
            round(number)
        )

    @staticmethod
    def _validate_optional_positive_integer(
        value: Any,
        field_name: str,
    ) -> int | None:
        """
        Valida Seed y Team sin imponer todavía un límite máximo.

        El rango concreto de Team se comprobará posteriormente según
        el número de equipos configurado para el evento.
        """
        if value is None:
            return None

        if isinstance(value, bool):
            raise TypeError(
                f"{field_name} must be an integer or None."
            )

        if isinstance(value, int):
            integer = value

        else:
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
                    f"{field_name} must be an integer or None."
                ) from error

            if not number.is_integer():
                raise ValueError(
                    f"{field_name} must be an integer or None."
                )

            integer = int(
                number
            )

        if integer <= 0:
            raise ValueError(
                f"{field_name} must be greater than zero."
            )

        return integer

    @staticmethod
    def _percentage(
        value: float | None,
    ) -> float | None:
        if value is None:
            return None

        return max(
            0.0,
            min(
                100.0,
                float(value),
            ),
        )

    @staticmethod
    def _prefer_recent(
        recent: float | None,
        lifetime: float | None,
    ) -> float | None:
        if recent is not None:
            return float(
                recent
            )

        if lifetime is not None:
            return float(
                lifetime
            )

        return None

    @staticmethod
    def _build_profile_url(
        nickname: str,
    ) -> str:
        return (
            "https://www.faceit.com/en/players/"
            f"{nickname}"
        )

    @staticmethod
    def _first_text(
        *values: Any,
    ) -> str | None:
        for value in values:
            text = (
                FaceitPlayerRecordMapper
                ._optional_text(value)
            )

            if text is not None:
                return text

        return None

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
    def _required_text(
        value: Any,
        field_name: str,
    ) -> str:
        text = (
            FaceitPlayerRecordMapper
            ._optional_text(value)
        )

        if text is None:
            raise ValueError(
                f"{field_name} is required."
            )

        return text

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
    def _require_mapping(
        value: Any,
        field_name: str,
    ) -> Mapping[str, Any]:
        if not isinstance(
            value,
            Mapping,
        ):
            raise TypeError(
                f"{field_name} must be a mapping."
            )

        return value

    @staticmethod
    def _optional_mapping(
        value: Any,
    ) -> Mapping[str, Any]:
        if isinstance(
            value,
            Mapping,
        ):
            return value

        return {}

    @staticmethod
    def _empty_recent_values() -> dict[str, None]:
        return {
            "kd": None,
            "kpr": None,
            "dpr": None,
            "adr": None,
            "hs": None,
            "kast": None,
            "rating": None,
            "clutch": None,
            "winrate": None,
        }

    @property
    def game_id(
        self,
    ) -> str:
        return self._game_id

    @property
    def source_name(
        self,
    ) -> str:
        return self._source_name

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"game_id={self._game_id!r}, "
            f"source_name={self._source_name!r})"
        )
