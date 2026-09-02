# LAN Player Impact Rating v1.0

## Purpose and version

LAN Player Impact Rating version `1.0` is an absolute, deterministic estimate of
useful individual contribution during the maps a player actually played. It is
calculated from one SCRUM-20 `PlayerStatistics` object, so map, series, and
tournament scores all use the same path. Series and tournament impact is never
an average of previously calculated map scores.

The result range is 0–100. Higher is better. Intermediate values are never
rounded. This is our own transparent LAN metric; it is not HLTV Rating 2.0,
Rating 3.0, or a reverse-engineering of any proprietary formula.

The complete formula and constants in this document, including
`MULTIKILL_VALUE_PER_MAP_SCALE = 5.0`, are frozen for model version `1.0`.
Any future formula change requires a new version identifier.

## Shared saturation function

For non-negative metric `x` and documented positive scale `s`:

```text
S(x, s) = 100 × (1 - exp(-x / s))
```

The function is zero at zero, scores approximately 63.2 at the scale, increases
smoothly, and approaches but never exceeds 100. Scales are strong-performance
reference values rather than fitted tournament-relative parameters. No
percentile, min/max, z-score, opponent pool, or rank changes a player's score.

## Weights and exact components

The canonical top-level weights sum to 1.0:

| Component | Weight | Maximum final contribution |
|---|---:|---:|
| Combat | 0.40 | 40 |
| Opening / Entry | 0.15 | 15 |
| Multikill | 0.10 | 10 |
| Supported Clutch | 0.15 | 15 |
| Teamplay | 0.10 | 10 |
| Utility / Flash | 0.10 | 10 |

Final impact is the sum of `component score × component weight`. Every component
and the final score is bounded to 0–100.

### Combat

```text
damage_score = S(damage_per_map, 1500)
kill_score = S(kills_per_map, 15)
survival_engagement_score = 100 × kills / (kills + deaths), or 0 if both are zero
combat = 0.45 × damage_score
       + 0.35 × kill_score
       + 0.20 × survival_engagement_score
```

Damage is the canonical combat-damage field. `health_points_dealt_total` is not
also scored. The survival term is coupled to offensive engagement, so a passive
zero-kill player cannot score by merely avoiding deaths. Headshot rate and shot
accuracy are retained as unweighted evidence because they are weapon- and
role-dependent and would correlate with combat quality.

### Opening / Entry

```text
wins_per_map = entry_wins / maps_played
attempts_per_map = entry_count / maps_played
volume = S(wins_per_map, 2)
confidence = 1 - exp(-attempts_per_map / 3)
efficiency = 100 × entry_success_rate × confidence
opening = 0.60 × volume + 0.40 × efficiency
```

Zero opportunities score zero. Volume and confidence prevent a single 1/1 from
automatically outranking repeated successful entries such as 8/12.

### Multikill

Independent exported events have values 2K=1, 3K=2, 4K=4, and 5K=7.

```text
weighted_value = enemy2ks + 2×enemy3ks + 4×enemy4ks + 7×enemy5ks
multikill = S(weighted_value / maps_played, 5)
```

Events are not cumulative or recursively expanded.

The frozen `MULTIKILL_VALUE_PER_MAP_SCALE` is `5.0`. Calibration found that
scale 3 saturated ordinary-good evidence too early. Scale 5 preserves useful
discrimination: a weighted value near 7/map scores about 75, and approximately
11.5/map is required to reach 90. Scale 6 was considered unnecessarily
conservative.

### Supported clutch

Only exported 1v1 and 1v2 evidence is used. Win values are 1v1=1 and 1v2=1.75.

```text
weighted_wins = v1_wins + 1.75×v2_wins
wins_per_map = weighted_wins / maps_played
attempts_per_map = (v1_count + v2_count) / maps_played
volume = S(wins_per_map, 0.75)
confidence = 1 - exp(-attempts_per_map / 1)
efficiency = 100 × supported_clutch_success_rate × confidence
supported_clutch = 0.60 × volume + 0.40 × efficiency
```

Zero supported opportunities score zero. This is not a universal clutch metric;
1v3, 1v4, and 1v5 evidence is absent.

### Teamplay

```text
teamplay = S(assists_per_map, 6)
```

V1 deliberately uses assists alone here. Flash evidence is not counted twice.

### Utility / Flash

```text
utility_volume = S(utility_damage_per_map, 150)
utility_confidence = 1 - exp(-(utility_count / maps_played) / 8)
utility_efficiency = 100 × utility_success_rate × utility_confidence
utility_bucket = 0.60 × utility_volume + 0.40 × utility_efficiency

flash_volume = S(enemies_flashed_per_map, 8)
flash_confidence = 1 - exp(-(flash_count / maps_played) / 8)
flash_efficiency = 100 × flash_success_rate × flash_confidence
flash_bucket = 0.60 × flash_volume + 0.40 × flash_efficiency

utility_flash = 0.50 × utility_bucket + 0.50 × flash_bucket
```

Zero opportunities contribute zero efficiency. Generic `utility_damage` remains
generic and is never described as HE, Molotov, incendiary, or fire damage.

## Explanation and identity

Every result contains the player id, canonical display name, model version,
unrounded final score, component scores, weights, weighted contributions, and
the important source/normalized evidence. `steamid64` remains identity. Aliases
and team strings do not change numerical impact.

## Tournament participation eligibility

Eligibility is separate from impact and does not modify the score:

```text
required_maps = ceil(maximum maps played by any tournament player × 0.50)
eligible = player maps_played >= required_maps
```

Map and series comparisons do not use this tournament-global policy.

## Future deterministic comparison evidence

SCRUM-22 may compare, in order: impact score descending, damage per map
descending, supported clutch wins descending, entry wins descending, kills per
map descending, then `steamid64` ascending. SCRUM-21 exposes this key but does
not rank players or select an MVP.

## Formula evaluation

Synthetic evaluation (`final, combat, opening, multikill, clutch, teamplay,
utility/flash`):

| Archetype | Final | Combat | Opening | Multi | Clutch | Team | Utility |
|---|---:|---:|---:|---:|---:|---:|---:|
| Fragger | 40.33 | 75.18 | 0.00 | 63.21 | 0.00 | 39.35 | 0.00 |
| Entry | 43.23 | 65.02 | 82.35 | 0.00 | 0.00 | 48.66 | 0.00 |
| Support | 44.51 | 58.78 | 33.34 | 0.00 | 0.00 | 86.47 | 73.57 |
| Clutch | 42.73 | 61.46 | 0.00 | 0.00 | 88.54 | 48.66 | 0.00 |
| Balanced | 64.36 | 67.60 | 66.08 | 55.07 | 61.48 | 68.86 | 57.97 |
| Passive | 10.82 | 23.21 | 0.00 | 0.00 | 0.00 | 15.35 | 0.00 |
| Small-sample star | 80.88 | 84.09 | 87.97 | 69.88 | 90.42 | 73.64 | 61.33 |
| Zero-opportunity | 22.41 | 48.93 | 0.00 | 0.00 | 0.00 | 28.35 | 0.00 |

The broad support profile can narrowly exceed the frag-only profile, while
dramatically stronger combat still receives a strong combat contribution. The
small-sample star keeps its quality score but fails tournament eligibility when
below the separate participation threshold.

Real SCRUM-18 fixture evaluation:

| Player | Final | Combat | Opening | Multi | Clutch | Team | Utility |
|---|---:|---:|---:|---:|---:|---:|---:|
| Snkr | 52.32 | 68.52 | 52.66 | 69.88 | 0.00 | 48.66 | 51.61 |
| weyS | 51.19 | 67.29 | 30.97 | 83.47 | 0.00 | 63.21 | 49.59 |
| ☢️ FuTuZ | 48.20 | 52.86 | 32.04 | 45.12 | 69.47 | 56.54 | 16.64 |
| zakk | 67.23 | 68.21 | 78.34 | 75.34 | 71.47 | 48.66 | 50.72 |
| JotaeNeI- | 50.31 | 61.16 | 52.66 | 45.12 | 0.00 | 73.64 | 60.73 |
| ☢️ NGRZ | 67.00 | 75.55 | 52.66 | 90.93 | 71.47 | 48.66 | 41.97 |
| zvn | 53.15 | 65.85 | 50.91 | 63.21 | 0.00 | 81.11 | 47.37 |
| login- | 29.26 | 41.78 | 0.00 | 0.00 | 0.00 | 73.64 | 51.88 |
| R1beh | 39.50 | 49.95 | 54.78 | 45.12 | 0.00 | 39.35 | 28.51 |
| ☢️-Delarosa- | 60.23 | 53.01 | 71.90 | 55.07 | 66.85 | 84.01 | 43.03 |

These rounded values are audit presentation only. Tests use full precision and
verify exact contribution reconciliation and deterministic reruns. No single
component can exceed its declared final contribution cap.

## Limitations and non-goals

V1 has no round-by-round context, opponent strength, win/loss contextual
weighting, 1v3/1v4/1v5 clutch data, exact incendiary/Molotov metric,
objective/bomb statistics, or trade-kill information. It does not implement
rankings, leaderboards, MVP selection, awards, humorous titles, HTML, or GUI.
