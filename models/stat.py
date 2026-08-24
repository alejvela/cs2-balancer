from enum import Enum


class Stat(str, Enum):
    """
    Estadísticas soportadas por el motor.

    El valor de cada elemento coincide con el nombre del atributo
    existente en Player.
    """

    ELO = "elo"

    KD = "kd"

    RATING = "rating"

    ADR = "adr"

    KPR = "kpr"

    DPR = "dpr"

    HS = "hs"

    KAST = "kast"

    WINRATE = "winrate"

    CLUTCH = "clutch"

    MATCHES = "matches"

    FACEIT_LEVEL = "faceit_level"

    FACEIT_ELO = "faceit_elo"
