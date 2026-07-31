# Experiment 001 preregistration

Registered before any sealed-set model call: **31 July 2026 at 12:31:06 UTC**.

This experiment tests a transfer hypothesis motivated by OpenAI's
[*How enabling two settings tripled our scores on the ARC-AGI-3
benchmark*](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/).
It does not assume that the ARC-AGI-3 result transfers to energy research.

## Frozen design

- Eight unseen, synthetic European power-market investigations.
- Five sequential deterministic audit gates per investigation.
- Three GPT-5.6 Sol harness conditions.
- Two repeated runs per episode-condition pair: 48 paid runs.
- `reasoning.effort="max"` and standard service tier in every condition.
- Randomized execution order with registered seed `56073101`.
- Model-visible cases and evaluator-only labels stored separately.
- SHA-256 verification before any API call.
- A $4.50 estimated-cost guard, selected to fit the available account credit.

The primary contrast is retained reasoning versus a stateless three-action
rolling history. The primary outcome is the paired episode-level change in the
100-point composite score. Superiority requires both a positive 95% confidence
interval lower bound and a two-sided sign-flip p-value at or below 0.05.

The compaction contrast is separate. Public-case calibration showed that 4,000-
and 2,000-token thresholds did not emit a compaction item, while 1,000 did. The
registered compaction condition is therefore a **forced-compaction stress test**.
It can support a quality-preservation claim only if compaction activates in at
least 80% of its sealed runs. It must not be described as a production-scale
200,000-token compaction benchmark.

## Integrity boundary

At registration, only the exact hashes in
[`preregistration.json`](preregistration.json) are public. The model-visible case
file and evaluator-only answer key are ignored by Git. After all outputs are
frozen, both files and every successful or failed run will be disclosed. That
makes this a one-time unseen evaluation: the released cases become public test
fixtures and cannot be called hidden in a later experiment.

No result existed when this preregistration was committed. The 48-run matrix is
now complete. See [`results.md`](results.md) for the frozen outcome and
[`../../outputs/experiment-001.json`](../../outputs/experiment-001.json) for all
run records.

The primary retention claim was supported. The forced-compaction
quality-preservation and token-reduction claims were not supported.
