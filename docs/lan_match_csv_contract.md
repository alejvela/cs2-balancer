# LAN match CSV contract

Each CSV represents one played map. Its parent folder is the authoritative match
or series boundary; `matchid` must never be used to join files across folders.

## Schema and validation

All 36 columns are required and supported. Their names and order in the reference
export are:

`matchid`, `mapnumber`, `steamid64`, `team`, `name`, `kills`, `deaths`,
`damage`, `assists`, `enemy5ks`, `enemy4ks`, `enemy3ks`, `enemy2ks`,
`utility_count`, `utility_damage`, `utility_successes`, `utility_enemies`,
`flash_count`, `flash_successes`, `health_points_removed_total`,
`health_points_dealt_total`, `shots_fired_total`, `shots_on_target_total`,
`v1_count`, `v1_wins`, `v2_count`, `v2_wins`, `entry_count`, `entry_wins`,
`equipment_value`, `money_saved`, `kill_reward`, `live_time`,
`head_shot_kills`, `cash_earned`, `enemies_flashed`.

- `matchid`, `steamid64`, `team`, and `name` are non-empty strings.
- `steamid64` is the canonical player identifier. `name` is presentation data.
- Every other field is a required, base-10, non-negative integer.
- No field is nullable. Empty, missing, malformed, fractional, or negative numeric
  values reject the row; they are never coerced to zero.
- Zero is valid and means the measured event/value was observed as zero.
- Unknown and duplicate columns reject the schema. Column order is not semantic.

The raw immutable representation keeps all source values. Derived ratings and
aggregations belong to later layers and are not part of this contract.

## Semantic limits

The export proves only a generic `utility_damage` value. It does not distinguish
Molotov/incendiary damage, so this field cannot support a fire-damage award unless
a later source provides that explicit metric.
