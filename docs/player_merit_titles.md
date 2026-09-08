# Player merit titles v1 (SCRUM-25)

Public API: `application.player_merits.generate_tournament_merits(statistics:
TournamentStatistics) -> TournamentMerits`. Consume SCRUM-20
`aggregate_tournament(import_result)` from SCRUM-18 validated input. No CSV
parsing, raw-total recomputation, ranking changes, or impact changes occur here.
Duplicate player ids in externally constructed aggregates are rejected.

Frozen domain objects: `MeritRule`, `MeritTieBreaker`, `MeritEvidence`,
`PlayerMerit`, `TournamentMerits`. Enums: `MeritCategory`, `MetricDirection`.
`WinnerMode` is removed: v1 has exactly one recipient per awarded title.
`TournamentMerits.for_rule(id)` returns an empty or one-element tuple.
Rules and secondary criteria contain immutable data, not callbacks.

## Frozen active catalog

The following row order is the output contract, stored in `ACTIVE_MERIT_IDS`.
It is independent of categories, names, or recipient identity. Omitted titles
leave a subsequence of this order. M = tournament maps played. P means the
existing SCRUM-21 `tournament_impact_eligibility(player, maximum_maps).eligible`,
i.e. `M >= ceil(maximum player maps * 0.50)`, computed before filtering.
Every primary denominator must also be positive.

All primary and secondary metrics maximize, except deaths, which minimizes.
Secondary metrics are applied in the exact left-to-right order below, followed
by the SCRUM-22 canonical fallback for every title.

| Stable id | Title | Category | Primary formula | Eligibility | Secondary criteria, in order |
|---|---|---|---|---|---|
| el_verdugo | El Verdugo | combat | kills | All | damage; kills / M |
| la_apisonadora | La Apisonadora | combat | damage / M | P; M > 0 | damage; kills / M |
| el_abrelatas | El Abrelatas | opening | entry_wins | All | entry_wins / entry_count; entry_count |
| sin_miedo_al_exito | Sin miedo al éxito | opening | entry_count / M | P; M > 0 | entry_wins / M; entry_count |
| rey_del_clutch | Rey del Clutch | clutch | v1_wins + v2_wins * 1.75 | All | v1_wins + v2_wins; (v1_wins + v2_wins) / (v1_count + v2_count); v1_count + v2_count |
| el_coleccionista | El Coleccionista | multikill | enemy2ks + enemy3ks * 2 + enemy4ks * 4 + enemy5ks * 7 | All | enemy5ks; enemy4ks; enemy3ks; enemy2ks |
| pikachu | Pikachu | support | enemies_flashed / M | P; M > 0 | flash_successes / flash_count; enemies_flashed; flash_successes |
| el_escudero | El Escudero | support | assists / M | P; M > 0 | assists |
| el_alquimista | El Alquimista | utility | utility_damage / M | P; M > 0 | utility_damage; utility_successes; utility_count |
| el_cirujano | El Cirujano | precision | head_shot_kills / kills | P; kills > 0 | head_shot_kills; kills; shots_on_target_total |
| el_francotirador_sin_mira | El Francotirador sin mira | precision | shots_on_target_total / shots_fired_total | P; shots_fired_total > 0 | shots_on_target_total; head_shot_kills |
| el_superviviente | El Superviviente | survival | live_time / M | P; M > 0 | live_time; fewer deaths |
| tio_gilito | Tío Gilito | economy | money_saved / M | P; M > 0 | money_saved; cash_earned |

`cash_earned` is used solely as the raw supported total, without inferring
strategic or economic quality. The same restriction applies to `money_saved`.
`live_time` retains unspecified input units; it is not labelled seconds.
`utility_damage` means generic utility damage. Assists do not use
`utility_successes` as a tie-break.

## Single-winner algorithm and evidence

For each rule independently, filter participation and defined-primary eligibility,
retain the best primary value, then narrow ties using each declared secondary
criterion in order. A defined secondary value (including zero) outranks undefined;
if all remaining values are undefined, continue. Never manufacture a zero ratio.
The final unresolved tie calls the existing SCRUM-22 `impact_tie_break_key` with
`calculate_player_impact`, reusing this order without a separate implementation:
impact descending, damage/map descending, supported clutch wins descending,
entry wins descending, kills/map descending, player_id ascending.

Only one recipient is emitted. Winning or losing a title never removes the
player from another title's candidate pool. Multiple different titles may be
awarded to the same player.

Primary and secondary comparisons use exact rational arithmetic without rounding
or tolerance. Canonical fallback retains SCRUM-22's existing numeric behavior.
Primary `evidence_value` is an integer when integral, otherwise an unrounded Python
float. Raw evidence preserves primary operands, secondary operands (including zero
denominators), and participation inputs; rule metadata supplies weights and formulas
for exact reconstruction. Aliases and teams come from SCRUM-20.

Clutch and multikill terms reuse SCRUM-21 `CLUTCH_WIN_WEIGHTS` and
`MULTIKILL_EVENT_WEIGHTS`; eligibility delegates to
`tournament_impact_eligibility`. No duplicated participation formula is implemented.

Missing primary metrics or zero primary denominators omit that candidate for the
rule. No candidates means no award; empty tournaments yield `TournamentMerits(())`.
Observed zero totals are valid and can yield a single zero-valued volume award.

Results enforce non-empty identifiers/titles, finite non-negative evidence,
unique raw evidence fields, at most one recipient per rule id (therefore also no
duplicate rule/player pairs), known active ids, and frozen catalog ordering.
Collections are immutable tuples. There is no shared-winner representation.

## Unavailable future title

- Stable id: `charmander`
- Display title: **Charmander**
- Meaning: highest genuine molotov/incendiary/fire contribution.
- Required metric: explicit molotov/incendiary/fire damage.
- Status: **unavailable**, represented by this documentation only.

Current SCRUM-18 input does not distinguish fire damage from generic utility damage.
`utility_damage` never activates Charmander; it supports El Alquimista. Charmander
is absent from the active catalog and rejected in `TournamentMerits`. No new CSV
columns or inferred fire damage are introduced.

## Tests

`tests/unit/models/test_player_merits.py` reuses SCRUM-20/21 factories and covers
all primary formulas, participation, identity, exact ties with one winner,
all secondary formulas/directions/order, defined versus undefined ratios,
SCRUM-22 fallback reuse, final player_id fallback, cross-title independence,
reverse/shuffled determinism, frozen order, unavailable Charmander, raw evidence,
zero denominators, immutable result invariants, and unchanged rankings/impact.
Some later criteria are algebraically redundant after earlier exact ties; these
are retained as specified and tested independently as well as catalog metadata.
