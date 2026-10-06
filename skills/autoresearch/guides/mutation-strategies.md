# Mutation strategies

What to change per trial, by `target_shape`. Read at the start of Phase 3 and after every ~10 trials when proposing the next direction.

## Universal rules

- **One mutation per trial** — see [knowledge-base.md](knowledge-base.md) invariants
- **Mutate the most-leveraged dimension first** — exhaust cheap-but-impactful changes before architectural ones
- **Record `mutation_summary` in ≤ 120 chars** — this is the leaderboard's "why"
- **Stop mutating a dimension after 3 consecutive losses** — pivot to a different cluster

## By target shape

### `ml-training`

Order of attack (cheap → expensive):

1. **Optimizer + LR** — swap Muon ↔ AdamW; scale LR by 2× / 0.5×; warmup steps
2. **Batch size / sequence length** — keep tokens-per-step constant when possible
3. **Architecture knobs** — `DEPTH`, `WINDOW_PATTERN`, attention pattern
4. **Tokenizer / vocab** — only if metric is vocab-independent (e.g. `val_bpb`)
5. **Loss formulation** — last, since it changes the landscape

Reference: karpathy README "Design choices" + the hyperparameters list for small platforms.

### `prompt-tuning`

Order of attack:

1. **Instruction clarity** — reorder steps; make constraints explicit
2. **Few-shot examples** — add 1–3 worked examples; vary diversity
3. **Output format** — JSON schema, delimiters, chain-of-thought toggle
4. **Persona / framing** — last, since it's noisy and hard to attribute

Guard against eval-set memorization — keep a held-out slice.

### `retrieval-tuning`

Order of attack:

1. **`top_k` / chunk size / overlap** — cheap config knobs
2. **Reranker on/off** with default model
3. **Encoder swap** — only when 1–2 are exhausted; expensive index rebuild
4. **Hybrid search weights** (BM25 + dense) — last; lots of knobs

### `algorithm-perf`

Order of attack:

1. **Data structure swap** on the hot path (dict → array, list → set)
2. **Allocation reduction** — reuse buffers; precompute prefix sums
3. **Vectorize / batch** the inner loop
4. **Concurrency** — last; introduces correctness risk
5. **Algorithm change** — only after profiling confirms hot path is correct target

Track `correctness_oracle` as a guardrail — a faster wrong answer is a regression.

### `hyperparam-search`

Order of attack:

1. **Coarse sweep on 1 dimension** — geometric (×2, ×0.5)
2. **Local refinement** around the winner (×1.25, ×0.8)
3. **Joint sweep on 2 dimensions** only after marginal returns flatten
4. **Random search > grid** when ≥ 3 dimensions matter (Bergstra & Bengio)

## Mutation hygiene

| Do | Don't |
|----|-------|
| Comment the diff with rationale in the trial dir | Stack 3 unrelated changes |
| Keep the parent snapshot — never overwrite | Mutate the live artifact in the repo |
| Note expected direction in `mutation_summary` ("expect lower bpb via deeper net") | Use vague summaries like "tune" |
| Halt a cluster after 3 losses; pivot | Keep mutating the same dimension until budget runs out |

## When the loop stalls

Indicators:

- 5+ trials with no improvement
- All recent mutations in one cluster
- Variance ≈ improvement (you are measuring noise)

Responses (in `hitl`):

1. **Compact memory** — re-read `report.md`-in-progress, look for pattern in losses
2. **Switch cluster** — change which dimension you mutate
3. **Tighten metric** — variance might be inflating; raise `min_improvement`
4. **Stop** — accept current best; route to Phase 4

In `autonomous`, the orchestrator should call out a stall in INDEX after every compaction window and prompt the user on next session.

## Inspiration sources

- For ML training mutations: the karpathy/autoresearch `program.md` (default baseline) and `train.py` knobs
- For prompt mutations: known patterns (chain-of-thought, self-consistency, plan-and-execute) — try one per trial
- For algorithm mutations: the CLRS decision tables ([algorithm-complexity rule](../../../.cursor/rules/algorithm-complexity.mdc)) for data-structure swaps
