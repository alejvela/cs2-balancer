# LAN player ranking contract

SCRUM-22 provides immutable, presentation-independent rankings at map, series,
and tournament scope. It consumes SCRUM-20 aggregated `PlayerStatistics` and
calculates each entry through the frozen SCRUM-21
`calculate_player_impact(...)` path. It does not redefine statistics or impact.

## Identity, aggregation, and ordering

`steamid64` / `player_id` is canonical identity. Names and raw team strings come
from the deterministic SCRUM-20 alias/team policies and never split a player.

Map ranking aggregates one `PlayedMap`. Series ranking first aggregates every
current map in an `ImportedSeries` or `PlayedSeries`, including incomplete BO3 or
BO5 data and `best_of=None`. Tournament ranking uses SCRUM-19's accepted map set
through `aggregate_tournament`. Series and tournament scores are calculated from
their aggregate statistics; map impact scores are never averaged.

Entries use this complete ordering:

1. impact score descending;
2. damage per map descending;
3. supported 1v1/1v2 clutch wins descending;
4. entry wins descending;
5. kills per map descending;
6. `player_id` ascending.

Ranks are strict contiguous ordinals `1..N`; there are no shared ranks because
the final identity key makes the comparison total. Input enumeration order does
not affect results. A scope with no aggregated players returns a valid immutable
ranking with no entries.

Map context contains authoritative series id, raw match id, and map number.
Series context is the authoritative `series_id`. Tournament context is the
explicit application-provided tournament id.

## Evidence and eligibility

Every entry exposes its full `PlayerStatistics`, versioned `PlayerImpactResult`,
component breakdown, aliases, teams, participation counts, and all frozen
tie-break evidence. Ranking results expose the underlying
`LAN_IMPACT_VERSION = "1.0"`.

Tournament ranking contains every canonical participant exactly once. Each
entry includes SCRUM-21 `TournamentImpactEligibility`, calculated against the
maximum maps played by any aggregated tournament player. Eligibility neither
filters entries nor changes impact or rank. Map and series entries have no
tournament eligibility.

Tournament ranking is not MVP eligibility. An ineligible small-sample player may
legitimately appear first; a later award layer decides whether eligibility is
required.

## Non-goals

This layer implements no MVP selection, awards, humorous titles, HTML, CLI, GUI,
team ranking, rank history, opponent-strength adjustment, new statistics, or new
impact formula. It is independent of ScoringModel, ObjectiveEngine, balance
restrictions, and the FAST, STABLE, and GLOBAL optimizers.
