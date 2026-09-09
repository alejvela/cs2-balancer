# Frozen LAN statistics acceptance (SCRUM-24)

This synthetic, deliberately small tournament protects the meaning of the complete
CSV-to-Spanish-HTML pipeline. Run `python -m pytest
tests/integration/test_lan_tournament_statistics.py` from the repository root.
The existing `../match_data_map0_1.csv` remains the real schema reference.
Neither root `match_data_map0_1.csv` nor `data/players.csv` is used.

## Manifest and boundaries

```text
lan_tournament_acceptance/
  README.md
  expected.json
  group-a/map-0.csv             BO1, one map
  group-b/map-0.csv             BO1, one map
  semifinal/map-0.csv           BO3, two maps
  semifinal/map-1.csv
  final/map-0.csv               BO5, three maps
  final/map-1.csv
  final/map-2.csv
  zz-duplicate/reordered.csv    BO1 metadata, no accepted maps
  zz-malformed/bad.csv          BO1 metadata, no accepted maps
```

BestOf values in expected.json are converted explicitly to domain enums. There
are six discovered folders, nine CSVs, seven imported maps, one duplicate, one
invalid CSV and four accepted series. Every valid CSV has ten players, five Azul
and five Rojo. No completion, winner, bracket or team standings are asserted:
three played maps in a BO5 only means three played maps.

The duplicate is final/map-0.csv with reversed row order, exported under another
filename in another folder. Final sorts first, so it supplies original provenance.
The malformed CSV has the otherwise complete header with only `kills` missing.
Both diagnostic folders contribute zero maps and zero statistical series.
The clean-control test copies only the explicit seven-file manifest.

Group and final maps reuse `reused-match-id`; the semifinal uses distinct
`semifinal-export-0` and `semifinal-export-1`. Thus neither equality nor inequality
of matchids defines a series. Parent folders do.

## Raw arithmetic worksheet

Player IDs are the decimal strings 76561198000000000 through 76561198000000010.
The following suffixes abbreviate them only in this document:

| Suffix | Name | Specialty override on the base map |
|---|---|---|
| 00 | Atlas | 30 kills, 10 deaths, 3000 damage |
| 01 | Boreal | 8 entry attempts, 5 wins |
| 02 | Clutch | 2 attempts / 1 win in each of v1 and v2 |
| 03 | Combo | 3 doubles, 2 triples, 1 quadruple, 1 ace |
| 04 | Flash | 16 enemies flashed, 8 flash successes |
| 05 | Socorro | 12 assists |
| 06 | Quimico | 300 generic utility damage, 8 successes |
| 07 | Cirujano | 12 headshots |
| 08 | Mira | 12 headshots, 80 shots on target |
| 09 | Ahorro | 1500 live time, 2000 money saved |
| 10 | Cometa | 60 kills, 6000 damage, 5 deaths, 15 assists; see CSV |

Base map: 15 kills/deaths, 1500 damage, 3 assists, 3 entries/1 win,
one double, one attempt/no wins in each supported clutch size, 8 utility uses
with 75 damage and 4 successes/enemies, 8 flashes with 4 successes/enemies,
100 shots/30 on target, 5 headshots, 1000 live time, 500 saved, 10000 earned,
4000 equipment, 300 kill reward; remaining counters zero.
Final map 2 doubles **every raw counter**, creating nonconstant per-map impact.
These are parser-valid synthetic exports, not a reconstructed round-by-round match.

Players 00-08 appear on all seven maps: totals equal eight base profiles across
four series. Cometa replaces Ahorro only in group-b: Cometa has one base profile,
one map/series; Ahorro has seven base profiles, six maps and three series.
Examples: Atlas totals 240 kills, 80 deaths, 24000 damage, 24 assists;
Clutch totals 16/8 v1 attempts/wins and 16/8 v2 attempts/wins;
Combo totals 24 doubles, 16 triples, 8 quadruples, 8 aces.
All raw fields for all eleven players are frozen and independently summed with
stdlib csv in the test. The production parser and aggregation do not supply
the oracle. Derived ratios use those integer totals and explicit denominators.

Atlas_2 occurs in group-a and both semifinal maps (three observations); Atlas
occurs four times and is canonical. Ahorro/Zorro each occur three times; Ahorro
wins the existing lexical tie. Both identities remain their original steamid64.

## Frozen scoring, order and awards

Component constants were calculated offline from the documented v1 equations,
not captured from production output. See the repository's
[v1 formula](../../../docs/player_impact_rating_v1.md) for the authoritative formula.
For example Atlas combat is
`0.45*S(24000/7,1500) + 0.35*S(240/7,15) + 20*240/(240+80)`
= 86.86388861566186, where `S(x,s)=100*(1-exp(-x/s))`.
His six components are 86.86388861566186, 35.1981585818815,
20.433053835830716, 0, 43.52818779922407, 39.73878153305503.
Weights 0.40/0.15/0.10/0.15/0.10/0.10 give 50.39528155035795.
The test combines frozen components independently; it does not implement a
second scoring engine. No production snapshot generator is provided.

Tournament order by suffix: **10, 02, 00, 03, 01, 05, 04, 06, 09, 07, 08**.
Cometa scores 93.1878020062863 but is ineligible (1 < ceil(7/2)=4).
MVP is Clutch, scoring 53.27743508347539. All other players are eligible.
Exact full-ID orders for every map and all four series live in expected.json.
Flash/Quimico and Cirujano/Mira have tied impact: the full ranking tie-break
ends in canonical ID. The final and tournament impact must differ from the
arithmetic mean of their map impacts.

Merit recipients in catalog order:
el_verdugo=00, la_apisonadora=00, el_abrelatas=01,
sin_miedo_al_exito=01, rey_del_clutch=02, el_coleccionista=03,
pikachu=04, el_escudero=05, el_alquimista=06, el_cirujano=08,
el_francotirador_sin_mira=08, el_superviviente=09, tio_gilito=09.
Cirujano and Mira tie at 96/120 headshots and at both first secondary totals;
Mira wins the next secondary criterion, 640 versus 240 shots on target.
Reversing player enumeration preserves all awards. Pikachu is SUPPORT;
Alquimista uses generic utility damage. Charmander is never awarded, although
the report can explain why it is unavailable.

## Review and intentional updates

Tests cover structured results, Spanish semantic sections, award recipients,
MVP, canonical identity, diagnostics, local anchors, inline styling and absence
of runtime dependencies. Two independent imports and two disk report exports
must agree exactly, including HTML, without accumulated duplicate state.
HTML is compared across runs, not stored as a whole-document golden snapshot.

To change this fixture, first explain the intended product scenario, edit raw
records, then reconcile integer totals, ratios, component arithmetic, tie-breaks
and ordered recipients against the existing contracts. Update expected.json
only after that review. Never refresh expectations from observed production
output to make a failing test pass. Expectation changes require review because
they can represent a product-contract change. A genuine production defect must
be reported for Tech Lead approval before changing production behavior.
