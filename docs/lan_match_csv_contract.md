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

Each supported file is a complete 5v5 export and therefore must contain exactly
10 rows with unique `steamid64` values. All rows must have one `matchid` and one
`mapnumber`. A file that violates any of these rules is invalid.

## Tournament folder import

The tournament root contains direct child directories, and each direct child is
the authoritative `PlayedSeries` boundary. Only regular `.csv` files immediately
inside those directories are discovered. CSV files at the tournament root,
nested directories, and non-CSV files are ignored. Empty child directories are
still reported as discovered series folders but produce no series and no issue.

Folders and files are sorted by case-insensitive name with the original name as
a deterministic tie-breaker. Maps in a completed series are sorted by
`mapnumber`; if different files in one folder contain the same map number, the
first file in discovery order wins and the later file is reported invalid.

`BestOf` is required external metadata keyed by the series folder name. The
importer never infers BO1, BO3, or BO5 from the number of files because an export
may represent an incomplete series. A folder containing valid maps but lacking
metadata retains those maps in an `ImportedSeries` whose `best_of` is `None` and
reports a structured series issue; it does not construct a `PlayedSeries`.
Supplying the metadata on a later stateless rescan constructs the domain series.
Partial BO3 and BO5 exports are valid; counts exceeding BestOf are series issues
without discarding the parsed maps. Unknown metadata keys and values that are not
`BestOf` members are also explicit series issues.

Exact duplicate detection is tournament-global and uses SHA-256 over canonical
parsed data. Every `PlayerMapStatistics` field is serialized in supported-column
order and records are sorted by `steamid64`. Thus filenames, BOM, line endings,
CSV quoting, and source row order do not affect identity, while any parsed value
change does. Only successfully validated content establishes the first accepted
copy. Later copies with that fingerprint, including copies under a new name or
another series folder, are reported as skipped duplicates and never merged or
counted again. Provenance remains the path of both the accepted file and each
skipped copy. Re-running an import has no hidden state and produces the same
result for the same folder contents.

A missing or non-directory tournament root fails the operation. Individual
unreadable, malformed, inconsistent, or duplicate-map files are collected as
structured issues, and valid files continue to be available. The returned
immutable result includes discovered folders and CSV count, accepted files and
maps, skipped duplicates, invalid files, series-level metadata issues, and all
series that could be safely constructed.

SCRUM-19 performs no K/D, ADR, Player Impact, ranking, award, or tournament
aggregate calculation.

## Semantic limits

The export proves only a generic `utility_damage` value. It does not distinguish
Molotov/incendiary damage, so this field cannot support a fire-damage award unless
a later source provides that explicit metric.
