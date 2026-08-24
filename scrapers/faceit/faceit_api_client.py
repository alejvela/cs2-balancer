from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any

import requests

from scrapers.faceit.activity_statistics import (
    ActivityStatistics,
)


class FaceitApiError(RuntimeError):
    """
    Error producido durante una llamada a la FACEIT Data API.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any | None = None,
    ) -> None:
        super().__init__(
            message
        )

        self.status_code = status_code
        self.response_body = response_body


class FaceitPlayerNotFoundError(FaceitApiError):
    """
    Indica que FACEIT no ha encontrado el recurso solicitado.
    """


class FaceitGameNotFoundError(FaceitApiError):
    """
    Indica que el jugador no tiene datos utilizables para ninguno
    de los juegos admitidos.
    """


class FaceitApiClient:
    """
    Cliente de la FACEIT Data API v4.

    Para cada jugador obtiene:

        - Perfil general.
        - Juego efectivo: CS2 o CS:GO como fallback.
        - ELO y nivel.
        - Estadísticas lifetime.
        - Estadísticas de partidas recientes.
        - Historial de los últimos 90 días.
        - Resumen de actividad por ventanas independientes.

    Ventanas de actividad:

        - 0 a 7 días.
        - 8 a 30 días.
        - 31 a 90 días.
    """

    BASE_URL = (
        "https://open.faceit.com/data/v4"
    )

    RETRYABLE_STATUS_CODES = {
        429,
        500,
        502,
        503,
        504,
    }

    HISTORY_WINDOW_DAYS = 90
    HISTORY_PAGE_SIZE = 100
    HISTORY_MAXIMUM_OFFSET = 1000

    def __init__(
        self,
        api_key: str,
        preferred_game_id: str = "cs2",
        fallback_game_ids: tuple[str, ...] = ("csgo",),
        timeout: float = 20.0,
        retries: int = 3,
        retry_delay: float = 1.0,
        session: requests.Session | None = None,
    ) -> None:
        self._api_key = self._validate_text(
            api_key,
            "api_key",
        )

        self._preferred_game_id = self._validate_text(
            preferred_game_id,
            "preferred_game_id",
        )

        self._fallback_game_ids = (
            self._validate_game_ids(
                fallback_game_ids
            )
        )

        if isinstance(timeout, bool) or not isinstance(
            timeout,
            (int, float),
        ):
            raise TypeError(
                "timeout must be numeric."
            )

        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero."
            )

        if (
            isinstance(retries, bool)
            or not isinstance(retries, int)
        ):
            raise TypeError(
                "retries must be an integer."
            )

        if retries <= 0:
            raise ValueError(
                "retries must be greater than zero."
            )

        if (
            isinstance(retry_delay, bool)
            or not isinstance(
                retry_delay,
                (int, float),
            )
        ):
            raise TypeError(
                "retry_delay must be numeric."
            )

        if retry_delay < 0:
            raise ValueError(
                "retry_delay cannot be negative."
            )

        self._timeout = float(
            timeout
        )

        self._retries = retries

        self._retry_delay = float(
            retry_delay
        )

        self._session = (
            session
            or requests.Session()
        )

        self._session.headers.update(
            {
                "Authorization": (
                    f"Bearer {self._api_key}"
                ),
                "Accept": "application/json",
                "User-Agent": "LAN-Balancer/2.0",
            }
        )

    def get_player_by_nickname(
        self,
        nickname: str,
    ) -> dict[str, Any]:
        """
        Busca un jugador por nickname sin restringir inicialmente
        el juego, permitiendo el fallback de CS2 a CS:GO.
        """
        nickname = self._validate_text(
            nickname,
            "nickname",
        )

        payload = self._request(
            method="GET",
            path="/players",
            params={
                "nickname": nickname,
            },
        )

        return self._validate_player_payload(
            payload=payload,
            identifier=nickname,
        )

    def get_player_by_game_player_id(
        self,
        game_player_id: str,
        game_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Busca un jugador por identificador de plataforma.
        """
        game_player_id = self._validate_text(
            game_player_id,
            "game_player_id",
        )

        resolved_game_id = (
            self._validate_text(
                game_id,
                "game_id",
            )
            if game_id is not None
            else self._preferred_game_id
        )

        payload = self._request(
            method="GET",
            path="/players",
            params={
                "game": resolved_game_id,
                "game_player_id": game_player_id,
            },
        )

        return self._validate_player_payload(
            payload=payload,
            identifier=game_player_id,
        )

    def get_player(
        self,
        player_id: str,
    ) -> dict[str, Any]:
        player_id = self._validate_text(
            player_id,
            "player_id",
        )

        payload = self._request(
            method="GET",
            path=f"/players/{player_id}",
        )

        return self._validate_player_payload(
            payload=payload,
            identifier=player_id,
        )

    def get_player_stats(
        self,
        player_id: str,
        game_id: str,
    ) -> dict[str, Any]:
        """
        Obtiene las estadísticas lifetime del juego seleccionado.
        """
        player_id = self._validate_text(
            player_id,
            "player_id",
        )

        game_id = self._validate_text(
            game_id,
            "game_id",
        )

        payload = self._request(
            method="GET",
            path=(
                f"/players/{player_id}"
                f"/stats/{game_id}"
            ),
        )

        if not isinstance(
            payload,
            dict,
        ):
            raise FaceitApiError(
                "FACEIT returned an invalid lifetime "
                "statistics response.",
                response_body=payload,
            )

        return payload

    def get_recent_match_stats(
        self,
        player_id: str,
        game_id: str,
        limit: int = 30,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Obtiene estadísticas recientes del juego seleccionado.

        Una respuesta con items=[] es válida.
        """
        player_id = self._validate_text(
            player_id,
            "player_id",
        )

        game_id = self._validate_text(
            game_id,
            "game_id",
        )

        self._validate_limit(
            limit=limit,
            maximum=100,
        )

        self._validate_offset(
            offset=offset,
            maximum=200,
        )

        payload = self._request(
            method="GET",
            path=(
                f"/players/{player_id}"
                f"/games/{game_id}/stats"
            ),
            params={
                "limit": limit,
                "offset": offset,
            },
        )

        return self._validate_collection_payload(
            payload=payload,
            default_start=offset,
        )

    def get_player_history_page(
        self,
        player_id: str,
        game_id: str,
        from_timestamp: int,
        to_timestamp: int,
        offset: int = 0,
        limit: int = HISTORY_PAGE_SIZE,
    ) -> dict[str, Any]:
        """
        Obtiene una página del historial de partidas.

        Los timestamps se expresan en Unix time, en segundos.
        """
        player_id = self._validate_text(
            player_id,
            "player_id",
        )

        game_id = self._validate_text(
            game_id,
            "game_id",
        )

        from_timestamp = self._validate_timestamp(
            from_timestamp,
            "from_timestamp",
        )

        to_timestamp = self._validate_timestamp(
            to_timestamp,
            "to_timestamp",
        )

        if to_timestamp < from_timestamp:
            raise ValueError(
                "to_timestamp cannot be lower than "
                "from_timestamp."
            )

        self._validate_limit(
            limit=limit,
            maximum=100,
        )

        self._validate_offset(
            offset=offset,
            maximum=self.HISTORY_MAXIMUM_OFFSET,
        )

        payload = self._request(
            method="GET",
            path=(
                f"/players/{player_id}/history"
            ),
            params={
                "game": game_id,
                "from": from_timestamp,
                "to": to_timestamp,
                "offset": offset,
                "limit": limit,
            },
        )

        validated = self._validate_collection_payload(
            payload=payload,
            default_start=offset,
        )

        validated["from"] = payload.get(
            "from",
            from_timestamp,
        )

        validated["to"] = payload.get(
            "to",
            to_timestamp,
        )

        return validated

    def get_player_history(
        self,
        player_id: str,
        game_id: str,
        days: int = HISTORY_WINDOW_DAYS,
        reference_timestamp: int | None = None,
    ) -> dict[str, Any]:
        """
        Obtiene todo el historial disponible dentro de una ventana.

        La consulta se pagina hasta que:

            - la API devuelve menos elementos que el límite;
            - devuelve una página vacía;
            - se alcanza el máximo offset admitido.
        """
        if (
            isinstance(days, bool)
            or not isinstance(days, int)
        ):
            raise TypeError(
                "days must be an integer."
            )

        if days <= 0:
            raise ValueError(
                "days must be greater than zero."
            )

        to_timestamp = (
            int(time.time())
            if reference_timestamp is None
            else self._validate_timestamp(
                reference_timestamp,
                "reference_timestamp",
            )
        )

        from_timestamp = (
            to_timestamp
            - days * 24 * 60 * 60
        )

        all_items: list[dict[str, Any]] = []

        offset = 0
        history_complete = True

        while offset <= self.HISTORY_MAXIMUM_OFFSET:
            page = self.get_player_history_page(
                player_id=player_id,
                game_id=game_id,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                offset=offset,
                limit=self.HISTORY_PAGE_SIZE,
            )

            page_items = page.get(
                "items",
                [],
            )

            valid_items = [
                dict(item)
                for item in page_items
                if isinstance(item, Mapping)
            ]

            all_items.extend(
                valid_items
            )

            if not page_items:
                break

            if len(page_items) < self.HISTORY_PAGE_SIZE:
                break

            offset += self.HISTORY_PAGE_SIZE

        else:
            history_complete = False

        if (
            offset > self.HISTORY_MAXIMUM_OFFSET
            and len(all_items) >= self.HISTORY_MAXIMUM_OFFSET
        ):
            history_complete = False

        return {
            "from": from_timestamp,
            "to": to_timestamp,
            "items": all_items,
            "count": len(all_items),
            "history_complete": history_complete,
        }

    def get_player_activity_statistics(
        self,
        player_id: str,
        game_id: str,
        reference_timestamp: int | None = None,
    ) -> ActivityStatistics:
        """
        Obtiene y resume la actividad de los últimos 90 días.
        """
        resolved_reference_timestamp = (
            int(time.time())
            if reference_timestamp is None
            else self._validate_timestamp(
                reference_timestamp,
                "reference_timestamp",
            )
        )

        history = self.get_player_history(
            player_id=player_id,
            game_id=game_id,
            days=self.HISTORY_WINDOW_DAYS,
            reference_timestamp=(
                resolved_reference_timestamp
            ),
        )

        return ActivityStatistics.from_history(
            history_items=history.get(
                "items",
                [],
            ),
            reference_timestamp=(
                resolved_reference_timestamp
            ),
            history_complete=bool(
                history.get(
                    "history_complete",
                    True,
                )
            ),
        )

    def get_player_bundle_by_nickname(
        self,
        nickname: str,
        recent_matches: int = 30,
    ) -> dict[str, Any]:
        player = self.get_player_by_nickname(
            nickname=nickname,
        )

        return self._build_player_bundle(
            player=player,
            recent_matches=recent_matches,
        )

    def get_player_bundle_by_game_player_id(
        self,
        game_player_id: str,
        recent_matches: int = 30,
    ) -> dict[str, Any]:
        """
        Busca primero en CS2 y después en los juegos fallback.
        """
        last_error: Exception | None = None

        for game_id in self.supported_game_ids:
            try:
                player = (
                    self.get_player_by_game_player_id(
                        game_player_id=game_player_id,
                        game_id=game_id,
                    )
                )

                return self._build_player_bundle(
                    player=player,
                    recent_matches=recent_matches,
                )

            except FaceitPlayerNotFoundError as error:
                last_error = error

        raise FaceitPlayerNotFoundError(
            "FACEIT did not find a player for the supplied "
            "platform identifier in the supported games."
        ) from last_error

    def _build_player_bundle(
        self,
        player: dict[str, Any],
        recent_matches: int,
    ) -> dict[str, Any]:
        self._validate_limit(
            limit=recent_matches,
            maximum=100,
        )

        player_id = self._extract_player_id(
            player
        )

        game_id = self.resolve_player_game(
            player
        )

        lifetime_statistics = self.get_player_stats(
            player_id=player_id,
            game_id=game_id,
        )

        recent_statistics = (
            self._get_optional_recent_statistics(
                player_id=player_id,
                game_id=game_id,
                recent_matches=recent_matches,
            )
        )

        activity_statistics = (
            self._get_optional_activity_statistics(
                player_id=player_id,
                game_id=game_id,
            )
        )

        return {
            "player": player,
            "game_id": game_id,
            "statistics": lifetime_statistics,
            "recent_statistics": recent_statistics,
            "activity_statistics": (
                activity_statistics.as_dict()
            ),
        }

    def resolve_player_game(
        self,
        player: dict[str, Any],
    ) -> str:
        """
        Selecciona CS2 o el primer juego fallback utilizable.
        """
        games = player.get(
            "games"
        )

        if not isinstance(
            games,
            dict,
        ):
            raise FaceitGameNotFoundError(
                "The FACEIT player does not contain "
                "game information.",
                response_body=player,
            )

        for game_id in self.supported_game_ids:
            game_data = games.get(
                game_id
            )

            if not isinstance(
                game_data,
                dict,
            ):
                continue

            if self._has_usable_game_data(
                game_data
            ):
                return game_id

        available_games = ", ".join(
            str(game)
            for game in games.keys()
        )

        raise FaceitGameNotFoundError(
            "The player has no usable data for the "
            "supported Counter-Strike games. "
            f"Available games: {available_games or 'none'}.",
            response_body=player,
        )

    @staticmethod
    def _has_usable_game_data(
        game_data: dict[str, Any],
    ) -> bool:
        return any(
            game_data.get(field) not in {
                None,
                "",
            }
            for field in (
                "faceit_elo",
                "skill_level",
                "game_player_id",
            )
        )

    def _get_optional_recent_statistics(
        self,
        player_id: str,
        game_id: str,
        recent_matches: int,
    ) -> dict[str, Any]:
        empty_result = {
            "start": 0,
            "end": 0,
            "items": [],
        }

        try:
            return self.get_recent_match_stats(
                player_id=player_id,
                game_id=game_id,
                limit=recent_matches,
            )

        except FaceitPlayerNotFoundError:
            return empty_result

    def _get_optional_activity_statistics(
        self,
        player_id: str,
        game_id: str,
    ) -> ActivityStatistics:
        """
        La ausencia de historial no invalida al jugador.

        Los errores de autenticación, permisos o conectividad siguen
        propagándose para no esconder problemas reales.
        """
        try:
            return self.get_player_activity_statistics(
                player_id=player_id,
                game_id=game_id,
            )

        except FaceitPlayerNotFoundError:
            return ActivityStatistics.empty(
                history_complete=True,
            )

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = (
            f"{self.BASE_URL}{path}"
        )

        last_error: Exception | None = None

        for attempt in range(
            1,
            self._retries + 1,
        ):
            try:
                response = self._session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self._timeout,
                )

            except requests.RequestException as error:
                last_error = error

                if attempt >= self._retries:
                    raise FaceitApiError(
                        "Could not connect to FACEIT: "
                        f"{error}"
                    ) from error

                self._sleep_before_retry(
                    attempt
                )

                continue

            response_body = self._read_response_body(
                response
            )

            if response.status_code == 404:
                raise FaceitPlayerNotFoundError(
                    "The requested FACEIT resource "
                    "was not found.",
                    status_code=response.status_code,
                    response_body=response_body,
                )

            if response.status_code in {
                401,
                403,
            }:
                raise FaceitApiError(
                    "FACEIT rejected the API key or "
                    "request permissions.",
                    status_code=response.status_code,
                    response_body=response_body,
                )

            if (
                response.status_code
                in self.RETRYABLE_STATUS_CODES
            ):
                last_error = FaceitApiError(
                    "FACEIT returned a temporary error "
                    f"({response.status_code}).",
                    status_code=response.status_code,
                    response_body=response_body,
                )

                if attempt >= self._retries:
                    raise last_error

                self._sleep_before_retry(
                    attempt=attempt,
                    retry_after=self._read_retry_after(
                        response
                    ),
                )

                continue

            if not response.ok:
                raise FaceitApiError(
                    "FACEIT returned an unexpected "
                    f"HTTP status {response.status_code}.",
                    status_code=response.status_code,
                    response_body=response_body,
                )

            return response_body

        raise FaceitApiError(
            f"FACEIT request failed: {last_error}"
        ) from last_error

    @staticmethod
    def _validate_collection_payload(
        payload: Any,
        default_start: int,
    ) -> dict[str, Any]:
        if not isinstance(
            payload,
            dict,
        ):
            raise FaceitApiError(
                "FACEIT returned an invalid collection response.",
                response_body=payload,
            )

        items = payload.get(
            "items",
            [],
        )

        if not isinstance(
            items,
            list,
        ):
            raise FaceitApiError(
                "FACEIT returned an invalid items collection.",
                response_body=payload,
            )

        return {
            "start": payload.get(
                "start",
                default_start,
            ),
            "end": payload.get(
                "end",
                default_start + len(items),
            ),
            "items": items,
        }

    @staticmethod
    def _read_response_body(
        response: requests.Response,
    ) -> Any:
        try:
            return response.json()

        except ValueError:
            return response.text

    @staticmethod
    def _read_retry_after(
        response: requests.Response,
    ) -> float | None:
        value = response.headers.get(
            "Retry-After"
        )

        if value is None:
            return None

        try:
            return max(
                0.0,
                float(value),
            )

        except ValueError:
            return None

    def _sleep_before_retry(
        self,
        attempt: int,
        retry_after: float | None = None,
    ) -> None:
        delay = (
            retry_after
            if retry_after is not None
            else min(
                self._retry_delay
                * (2 ** (attempt - 1)),
                10.0,
            )
        )

        if delay > 0:
            time.sleep(
                delay
            )

    @staticmethod
    def _validate_player_payload(
        payload: Any,
        identifier: str,
    ) -> dict[str, Any]:
        if not isinstance(
            payload,
            dict,
        ):
            raise FaceitApiError(
                "FACEIT returned an invalid player "
                f"response for '{identifier}'.",
                response_body=payload,
            )

        player_id = payload.get(
            "player_id"
        )

        if (
            not isinstance(player_id, str)
            or not player_id.strip()
        ):
            raise FaceitPlayerNotFoundError(
                "FACEIT did not return a valid player "
                f"for '{identifier}'.",
                response_body=payload,
            )

        return payload

    @staticmethod
    def _extract_player_id(
        player: dict[str, Any],
    ) -> str:
        player_id = player.get(
            "player_id"
        )

        if (
            not isinstance(player_id, str)
            or not player_id.strip()
        ):
            raise FaceitApiError(
                "The player response does not contain "
                "a valid player_id.",
                response_body=player,
            )

        return player_id.strip()

    @staticmethod
    def _validate_game_ids(
        game_ids: tuple[str, ...],
    ) -> tuple[str, ...]:
        if game_ids is None:
            return ()

        if not isinstance(
            game_ids,
            tuple,
        ):
            raise TypeError(
                "fallback_game_ids must be a tuple."
            )

        result: list[str] = []

        for game_id in game_ids:
            validated = FaceitApiClient._validate_text(
                game_id,
                "fallback_game_id",
            )

            if validated not in result:
                result.append(
                    validated
                )

        return tuple(
            result
        )

    @staticmethod
    def _validate_limit(
        limit: int,
        maximum: int,
    ) -> None:
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
        ):
            raise TypeError(
                "limit must be an integer."
            )

        if not 1 <= limit <= maximum:
            raise ValueError(
                f"limit must be between 1 and {maximum}."
            )

    @staticmethod
    def _validate_offset(
        offset: int,
        maximum: int,
    ) -> None:
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
        ):
            raise TypeError(
                "offset must be an integer."
            )

        if not 0 <= offset <= maximum:
            raise ValueError(
                f"offset must be between 0 and {maximum}."
            )

    @staticmethod
    def _validate_timestamp(
        value: int,
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

    @property
    def preferred_game_id(
        self,
    ) -> str:
        return self._preferred_game_id

    @property
    def fallback_game_ids(
        self,
    ) -> tuple[str, ...]:
        return self._fallback_game_ids

    @property
    def supported_game_ids(
        self,
    ) -> tuple[str, ...]:
        return (
            self._preferred_game_id,
            *self._fallback_game_ids,
        )

    def close(
        self,
    ) -> None:
        self._session.close()

    def __enter__(
        self,
    ) -> FaceitApiClient:
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ) -> None:
        self.close()

    def __repr__(
        self,
    ) -> str:
        return (
            f"{self.__class__.__name__}("
            f"preferred_game_id="
            f"{self._preferred_game_id!r}, "
            f"fallback_game_ids="
            f"{self._fallback_game_ids!r}, "
            f"history_window_days="
            f"{self.HISTORY_WINDOW_DAYS}, "
            f"timeout={self._timeout}, "
            f"retries={self._retries})"
        )
