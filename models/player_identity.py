from __future__ import annotations

from typing import Any

from models.player import Player


def logical_player_identity(
    player: Player,
) -> str:
    """
    Devuelve una identidad determinista para un jugador.

    Prioridad:

        identity
            ↓
        steam_id
            ↓
        nickname
            ↓
        fallback estructural

    La identidad se normaliza con casefold().
    """
    if player is None:
        raise ValueError("player cannot be None.")

    explicit_identity = getattr(
        player,
        "identity",
        None,
    )

    normalized_identity = _normalize_text(explicit_identity)

    if normalized_identity:
        return f"identity:{normalized_identity}"

    steam_id = _normalize_text(
        getattr(
            player,
            "steam_id",
            None,
        )
    )

    if steam_id:
        return f"steam:{steam_id}"

    nickname = _normalize_text(
        getattr(
            player,
            "nickname",
            getattr(
                player,
                "nick",
                None,
            ),
        )
    )

    if nickname:
        return f"nick:{nickname}"

    return _fallback_player_identity(player)


def _fallback_player_identity(
    player: Player,
) -> str:
    """
    Último recurso para jugadores sin identidad explícita.

    Se evita utilizar id(player) porque no es estable entre
    ejecuciones.

    Esta identidad no debería utilizarse normalmente si el modelo
    Player está correctamente construido.
    """
    attributes = (
        "elo",
        "level",
        "kd",
        "rating",
        "adr",
        "kpr",
        "dpr",
        "hs",
        "kast",
        "winrate",
        "clutch",
        "matches",
        "seed",
    )

    values: list[str] = []

    for attribute in attributes:
        value = getattr(
            player,
            attribute,
            None,
        )

        values.append(f"{attribute}={_stable_value(value)}")

    return "anonymous:" + "|".join(values)


def _normalize_text(
    value: Any,
) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().casefold()

    if not normalized:
        return None

    return normalized


def _stable_value(
    value: Any,
) -> str:
    """
    Convierte valores simples a una representación estable.
    """
    if value is None:
        return "none"

    if isinstance(
        value,
        bool,
    ):
        return "true" if value else "false"

    if isinstance(
        value,
        float,
    ):
        return f"{value:.12g}"

    return str(value).strip().casefold()
