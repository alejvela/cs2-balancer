# Player statistics aggregation contract

SCRUM-20 aggregates validated LAN map records without parsing CSVs or performing
presentation, ranking, award, MVP, or Player Impact work.

## Identity and deterministic context

`steamid64` is the player identity. Names and teams never participate in
identity. `observed_aliases` and `observed_teams` retain unique values in
case-insensitive lexical order. Within each map, series, or tournament scope,
`display_name` is the player's most frequently observed alias. Equal-frequency
aliases use the lexicographically ascending alias as a deterministic tie-breaker.
This is a canonical representative, not a claim about chronology. Players are
always returned by ascending `steamid64`.

## Raw additive totals

The additive fields are:

`kills`, `deaths`, `damage`, `assists`, `enemy5ks`, `enemy4ks`, `enemy3ks`,
`enemy2ks`, `utility_count`, `utility_damage`, `utility_successes`,
`utility_enemies`, `flash_count`, `flash_successes`,
`health_points_removed_total`, `health_points_dealt_total`,
`shots_fired_total`, `shots_on_target_total`, `v1_count`, `v1_wins`, `v2_count`,
`v2_wins`, `entry_count`, `entry_wins`, `equipment_value`, `money_saved`,
`kill_reward`, `live_time`, `head_shot_kills`, `cash_earned`, and
`enemies_flashed`.

`mapnumber` is context and is not summed. Every raw total remains available in
`PlayerRawTotals`; derived values are always recomputed from these totals.
Aggregation deliberately does not add further exporter-semantic validation such
as rejecting successes greater than attempts.

## Levels and participation

- Map aggregation gives every participant `maps_played=1` and `series_played=1`
  and preserves that map's team context.
- Series aggregation accepts `PlayedSeries` or `ImportedSeries`, including
  `best_of=None`. A participant's map count includes only maps they played, and
  their series count is one. Complete and incomplete BO1/BO3/BO5 series use the
  same arithmetic.
- Tournament aggregation consumes SCRUM-19 `TournamentImportResult.imported_files`
  as the authoritative, tournament-global deduplicated map set. Series count is
  the number of distinct authoritative `series_id` values in which the player or
  tournament has accepted maps.

Input order never controls result order or display-name selection.

## Derived metrics

Rates are ratios in `[0.0, 1.0]` when exporter successes do not exceed attempts;
they are never multiplied by 100. `safe_ratio` returns `0.0` for a zero
denominator. K/D separately returns `float(kills)` when deaths are zero, giving a
finite value without erasing kill information. Precisely,
`kd_ratio = kills / max(deaths, 1)`: 10 kills and zero deaths gives `10.0`, while
zero kills and zero deaths gives `0.0`. This is a finite reporting convention in
place of mathematical infinity or an undefined value and does not apply to any
other ratio.

The model exposes K/D; kills, deaths, damage, and assists per map; headshot rate;
shot accuracy; entry success; 1v1 and 1v2 success; supported clutch attempts,
wins, and success rate; flash success; enemies flashed per flash; utility
success; utility damage per use; and concise per-map utility, flash, entry, and
multikill metrics.

Supported clutch metrics combine only exported 1v1 and 1v2 evidence. The four
multikill counters remain independent categories and are summed only to count
exported multikill events. Generic `utility_damage` is not reinterpreted as HE,
Molotov, incendiary, or fire damage. No damage-efficiency metric is defined
because `damage` versus `health_points_dealt_total` semantics are not sufficiently
distinct for a useful additional ratio.
