# GLOBAL bound safety and proof contracts ? SCRUM-50

Baseline: `4741749d39187748fd1547c75c13fa780dd816de`.
The audited objective is the actual engine passed to GlobalOptimizer, not an
engine reconstructed from application configuration. No scoring formula,
weights, preset, traversal ordering, CLI/HTML or STABLE behavior is tuned.

## Objective and bound audit

Let T be the number of teams, s their required size, p_i the authoritative
`ScoringModel.power(player_i)`, w_r a restriction's nonnegative weight, q_r its
score, and P_r its nonnegative structural penalty. The valid assignment domain
has exactly s original problem players per team and satisfies the problem's
protected-seed maximum. Teams have canonical labels 1..T and players within each
team are represented in problem-index order. Unknown objectives may depend on
team labels/order; those labels are all searched. The problem provides no
additional hard locked-player contract via an arbitrary prepared root.

| Component | Actual objective | Legacy bound proposal | Certified status / prerequisites |
| --- | --- | --- | --- |
| Power | Team mean = float sum of p_i / size; global mean = statistics.mean(team means); spread = max(mean)-min(mean); score = clamp(100*(1-spread/global_mean),0,100). If global mean <=0, score is 100 only for zero spread. Penalty 0. | Each partial team gets [current sum + k smallest remaining, current sum + k largest remaining]/s; R=max(0,max lower-min upper); U=clamp(100*(1-R/(sum p_i/(T*s))),0,100). | Admissible over real arithmetic for exact matching scalar powers, fixed equal sizes, complete remaining pool and positive mean. The legacy floating implementation alone is **not** a certificate: summation grouping and the two global-mean computations can differ. Certified pruning uses the outward enclosure below. |
| ELO Balance | Population standard deviation of team ELO means, then clamp of the logistic normalizer: 100/(1+exp(steepness*(sigma-midpoint))), with its overflow guards. Missing ELO values follow TeamStatistics; an entirely missing metric produces its existing zero average. Penalty 0. | 100. | Conservative universal component ceiling. No nontrivial ELO algorithm is claimed. A custom normalizer/evaluator is not assumed permutation invariant. |
| ELO Spread | max team ELO mean - min team ELO mean, mapped by piecewise linear interpolation through configured thresholds: ideal=>100, good=>85, acceptable=>60, poor=>25, maximum=>0. Penalty 0. | 100 (shared optimistic ELO contribution in legacy aggregation). | Conservative. Generated team names/IDs must be unique for the dictionary reduction; incoming noncanonical representations need an objective witness before proof. |
| KD | Population standard deviation of team KD means; default linear normalizer gives 100 at sigma<=0, 0 at sigma>=max_deviation, otherwise 100*(1-sigma/max_deviation). Penalty 0. | 100. | Conservative component ceiling; no KD tightening is claimed. |
| TeamSize | Base score 100. Penalty=min(100, penalty_per_position * sum abs(actual_size-expected_size)); diagnostic compliance is not the scoring contribution. | 100, penalty omitted. | Exact base score; omitting a nonnegative penalty is optimistic, including when objective expected size differs from the hard problem size. |
| Seed | Base score 100. Total excess=sum max(0, team seed count-maximum_per_team); penalty=min(maximum_penalty, penalty_per_excess_player*excess). | 100, penalty omitted. | Exact base score, conservative omission of nonnegative penalties. Hard feasibility uses **problem** seed level/maximum; another objective seed penalty remains a soft term, not an invented hard constraint. |
| Aggregation | ObjectiveResult computes weighted_score=sum(w_r*q_r), total_weight=sum(w_r), score=clamp(weighted_score/total_weight - sum(P_r),0,100); zero total weight gives 0. Penalties are not weight-scaled. | Weighted combination of Power estimate and 100 for other named components, with calculator weights. | Matching weights alone is insufficient. The certified combination uses the actual restriction order and actual denominator, outward arithmetic and no negative weights. Unknown/omitted/custom components invalidate Power tightening. The exact unchanged ObjectiveEngine/ObjectiveResult clamp independently proves a whole-objective ceiling of 100. An arbitrary numeric engine has **no assumed ceiling**. |

ScoringModel's base Power is the available-component weighted average (or its
configured fallback when coverage is insufficient), clamped to 0..100; optional
ActivityFactorModel applies its existing per-player activity/level adjustment and
clamp. The certificate does not duplicate that model: it checks every effective
metric p_i equals the active model's output on the actual problem player. Known
scoring/components/normalizers/activity implementations must be unchanged.
Unknown subclasses, replaced methods/helpers or extensions fall back safely.
The runtime compares restriction types/implementations, effective weights,
normalizers, scalar scoring pipeline, data and calculator implementation. Names
and factory weights by themselves never establish compatibility.

## Floating Power enclosure

The certified path is intentionally limited to audited CPython binary64,
round-to-nearest arithmetic (3.11, 3.12 and 3.14), nonnegative scalar p_i<=100,
s<=1,000,000, and either all zero Power or max p_i>=2^-500. Other arithmetic/data
regimes use the proven whole-objective ceiling or exhaustive fallback; they are
not assigned an unverified numerical estimate.

For n=s, let M=n*max p_i. Take H as an outward-rounded upper bound on 2M and
E=(8n+8)*ulp(H), represented as an exact Fraction. A sequential positive float
sum incurs at most one half-ulp local error per addition. In the compensated
sum, the hi update's error is canceled by its residual correction; the error in
hi+lo telescopes to the two residual-operation errors, the lo addition error,
and the final conversion. All intermediate magnitudes stay within 2M on the
supported regime (E is much smaller than M). E therefore bounds both summation
paths, in any player order. This is an arithmetic enclosure, not an empirically
chosen score tolerance.

Implementation evidence: CPython [3.11 sum](https://github.com/python/cpython/blob/v3.11.17/Python/bltinmodule.c)
uses sequential float addition; [3.12 sum](https://github.com/python/cpython/blob/v3.12.15/Python/bltinmodule.c)
and [3.14 sum](https://github.com/python/cpython/blob/v3.14.6/Python/bltinmodule.c)
use the compensated update audited above. No third-party bound formula is used.

For each team, sum its fixed input powers exactly as binary rational numbers,
then add the k smallest/largest remaining powers exactly. Reusing players across
team possibilities only relaxes constraints. Subtract/add E to enclose the
actual final float sum; divide by s with outward rounding. These means enclose
every real completion's computed means, including division by 3 or 5.

If the resulting intervals are [L_t,H_t], an outward lower bound on computed
spread is max(0,max L_t-min H_t). An outward upper bound on the global mean is
the exact average of the upper endpoints rounded upward. Since Power score is
monotonically decreasing in spread and increasing in positive global mean,
propagating those endpoints through division/subtraction/multiplication with
nextafter toward the optimistic direction encloses the **computed** Power score.
All-zero inputs use the exact 100 branch.

The numerator uses the actual restriction ordering, nonnegative weights and
upward operations. Its denominator matches the actual objective's weight sum.
Ignoring nonnegative penalties and applying the objective clamp preserves an
upper bound. Overflow in the conservative numerator falls back to ceiling 100;
invalid present decision numbers still fail through models.numeric.finite_real.

The legacy calculator is only a proposal/diagnostic. A suggested score prune is
accepted only after this independent enclosure (or whole-objective ceiling)
justifies it. Wrong metrics, wrong weights, omitted/custom restrictions and
unknown calculators cannot discard a branch with an unsafe Power estimate.
Opaque objectives returning values above 100 get upper_bound=None and no score
pruning. With use_power_bound=False, no Power interval/bound work is executed.

## Feasibility, symmetry and root completeness

Capacity lookahead: remaining player count cannot exceed total remaining team
capacity. Seed lookahead: remaining protected count cannot exceed sum of the
minimum of each team's physical slots and remaining protected allowance. These
are necessary conditions, not scoring assumptions. SCRUM-49 gates are retained;
hard assignment capacity/seed maxima apply regardless of flags. Untrusted
lookahead callbacks are independently checked in proof mode. Ordinary custom
feasibility callbacks retain their behavior but cannot contribute an unverified
skip to proof. An unexpected assignment ValueError (e.g. floating overflow) is
not mistaken for a hard constraint: ordinary search becomes unproven; proof
mode propagates the error. Counter increments/limit priority are unchanged. The new initial domain-witness
evaluation is validation work, not a complete-search-state evaluation; its
budget/timing treatment remains within the existing validation scope.

All built-in restrictions are permutation invariant over real arithmetic with
uniform team capacities and seed rules. Labels in diagnostics do not change the
score for canonical generated teams. However, ELO/KD variance reductions with
more than two teams are not certified bitwise permutation invariant. Proof mode
therefore disables that symmetry reduction. Unknown/order-sensitive objectives
also disable symmetry, including ordinary mode. For recognized ordinary search,
the established reduction remains, but proof requires certified symmetry.
Traversal/evaluation/validation overrides are not certified by a stop label:
proof mode explicitly rejects unknown critical solver implementations. The next
metric must match the actual problem prefix. Candidate-set and ordering checks
ensure a reduction cannot silently omit a
non-equivalent branch or turn branch ordering into pruning.

A factory root fixing at most one protected seed per team covers a representative
of every assignment up to team permutation only when that permutation is safe.
With maximum>1, round-robin seed grouping fixes which seeds share teams, which
team relabeling cannot repair. An arbitrary partial root is not evidence of
full-domain completeness. Proof mode starts from an empty root when this
coverage cannot be certified, reusing the same DFS/assignment algorithm. Unknown
objectives also expand unsafe factory seed roots in ordinary mode. Ordinary
caller-specific roots otherwise remain usable but explicitly unproven.
Root player indices must cover exactly the sequential prefix; SCRUM-49 hard
capacity/protected-count validation still applies.

## Proof/result contract

GlobalOptimizationResult exposes search_exhausted separately from
optimality_proven and carries an immutable GlobalProofCertificate. A completed
search alone is not proof. The certificate records root coverage, safe symmetry,
score/feasibility pruning, audited traversal implementation, exact ranking,
incumbent domain witness, exact final
verification and the selected bound strategy. optimality_proven is true only
when **all** these obligations hold and the search exhausted without a limit.
GlobalReportResult exposes the same certificate and delegates search_exhausted;
no CLI/HTML layout or rendering is changed. Direct result construction cannot
claim proof without a matching certificate or after budget termination.

With require_proof=True, candidate comparison is strict score>best and pruning
requires certified upper<=best; neither minimum_improvement nor score_tolerance
can discard a genuinely better solution. Existing presets/tuning values are not
changed. Ordinary ranking retains its strict configured improvement threshold
and bound tolerance. If either loses a strictly better candidate or prunes with
upper>best, proof is withheld even if SEARCH_EXHAUSTED is returned.

Initial incumbent semantics remain SCRUM-49: optional only when disabled,
authoritatively evaluated when enabled, finite score consistency checked.
Every incumbent needs an exact scoring witness built with fresh Teams, original
problem players and canonical IDs/index order, even when metadata already matches.
This detects stale statistics caches and object-identity-sensitive scores. Ordinary use remains
accepted with an unproven certificate if that witness differs; proof mode fails
explicitly. No synthetic baseline is introduced. Final teams are independently
reevaluated by the same effective objective; disagreement beyond configured
tolerance always fails. Proof requires exact equality even inside tolerance;
ordinary tolerated drift withholds proof.

require_proof=True retains the explicit config rejection of artificial budgets.
If proof cannot be completed at runtime, the result is unproven with
PROOF_NOT_COMPLETED, while search_exhausted remains independently recorded.
Invalid arithmetic, inconsistent final scores or unverified search reductions
fail explicitly rather than fabricate a certificate. Node/evaluation/time
termination never certifies proof, even if its incumbent happens to be optimal.

All proof statements assume a deterministic, finite, total objective on the
canonical assignment domain, unchanged inputs/code during the run and ordinary
IEEE rounding. Runtime checks do not purport to prove arbitrary program purity,
external concurrent mutation or behavior outside the declared domain. Unknown
pure objectives can nonetheless be proved by full labeled enumeration with no
unverified score or symmetry reduction.

## Independent oracle and compatibility evidence

The reference enumerates all labeled destinations with itertools.product,
filters exact team sizes and problem protected counts directly, builds fresh
Team objects with original problem players, and invokes the actual objective.
It never uses the bound calculator, search state/root, symmetry helper or solver
for enumeration or validity filtering.

Tests cross incumbent/Power/symmetry on/off over Power-only, all six components,
reordered components, incompatible weights/metrics, an extra restriction and an
order-sensitive unbounded numeric objective. Further cases cover multi-seed
roots, three-team metrics, all prefix descendants, non-dyadic team averages,
near-tolerance improvements, replaced evaluator/helper implementations,
malicious calculators, nonfinite values, incumbent witnesses, final drift and
all budget kinds. Certified upper bounds must dominate oracle descendants with
**no** tolerance slack; any returned proof must match the oracle's exact maximum.

Production ordinary-mode fingerprints retain their teams/scores and bounded
traversal; corrected tests stop equating arbitrary prepared roots/scripted
bounds with a proof. No frozen expectation is regenerated to pass validation.
SCRUM-51 retains budget/counter/time scope and stop-taxonomy redesign. No new
ELO bound, scoring formula, weight tuning, random traversal, CLI, HTML, STABLE or
importer work is included.
