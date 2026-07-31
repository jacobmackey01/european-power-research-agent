# Evaluation protocol

## Unit of evaluation

An episode is a market-research question, a deterministic tool environment, and
a sealed answer key. The agent receives the question and tool schemas. It never
receives the expected conclusion, expected root cause, required evidence IDs,
or scoring weights.

## Controlled factors

For a harness comparison, hold constant:

- model snapshot;
- reasoning effort and mode;
- instructions and tool descriptions;
- maximum steps and maximum output tokens;
- episode version;
- evaluator version;
- seed or repeated-run schedule;
- API service tier.

Change only the harness condition:

1. stateless with a bounded rolling record;
2. retained reasoning;
3. retained reasoning with compaction.

The retention contrast and the compaction contrast answer different questions.
`retained-reasoning` versus `stateless-truncated` estimates the value of preserving
reasoning and the complete action history. `retained-reasoning-compaction` versus
`retained-reasoning` estimates what happens when the retained state is compacted.
They are reported separately; a combined win over the stateless baseline does not
by itself prove that compaction added value.

## Score

Each run receives up to 100 points:

| Component | Points | Rule |
|---|---:|---|
| Decision | 30 | submitted conclusion equals the sealed label |
| Diagnosis | 25 | submitted root cause equals the sealed label |
| Required evidence | 25 | proportional credit for required evidence IDs cited |
| Citation validity | 10 | all cited IDs were actually observed from tools |
| Efficiency | 10 | no unnecessary duplicate tool calls |

A run without a submitted research memo receives zero. Tool errors, premature
text answers, unsupported IDs, duplicated calls, latency, and token counts are
reported separately so an identical total score cannot hide different failure
modes.

## Primary metrics

- mean episode score with uncertainty across repeated runs;
- exact task success rate;
- correct-decision and correct-diagnosis rates;
- required-evidence recall;
- unsupported-citation rate;
- duplicate and invalid tool calls;
- input, cached-input, cache-write, output, and reasoning tokens;
- wall-clock latency;
- estimated API cost using the price table recorded on the run date.

Cost is calculated after collection, not hard-coded into historical run files,
because model prices can change.

## Development set versus hidden set

The repository's initial episodes are public development fixtures. They catch
engineering regressions and make the scoring logic inspectable. They must not be
described as a blind evaluation.

Before publishing performance claims:

1. write additional episodes and answer keys;
2. freeze each episode with a content hash;
3. keep hidden labels outside the prompt-building and agent modules;
4. register the experiment configuration before viewing condition results;
5. execute the full run matrix without prompt edits between conditions;
6. publish all runs, including failures.

The experiment runner enforces this process by checking SHA-256 hashes before any
API call, deriving a deterministic randomized run order from the registered seed,
checkpointing every result, and refusing to resume against a different
preregistration.

## Repeated-run inference

The episode is the independent evaluation unit. Repeated model runs are paired by
episode, repeat, and harness condition; they are not treated as extra independent
episodes. Report episode-clustered paired mean differences, a 95% bootstrap
interval, and a two-sided episode-level sign-flip test. Freeze the bootstrap seed,
iteration count, superiority margin, and any non-inferiority margin before viewing
condition results.

Compaction is testable only when the response stream contains at least one
encrypted `compaction` output item. Sending `context_management` without crossing
the threshold is a configuration check, not a compaction experiment. A deliberately
low threshold must be labelled a forced-compaction stress test rather than a
production long-context benchmark.

## Leakage safeguards

- Tool output contains evidence, never an `expected_answer` field.
- The model has no filesystem or code-inspection tool.
- The evaluator runs after the agent stops.
- Episode labels are not used to generate the prompt.
- A future hidden set should be loaded by the evaluation process only, from a
  separately controlled manifest.

## Interpretation

A short smoke test confirms that the SDK request shape and tool continuation
work. It is not evidence that one harness is better. A small public development
set can reveal failures and generate hypotheses. Only repeated runs on a frozen,
unseen set support a comparative performance claim.

Synthetic seeded episodes support a claim about this harness on those controlled
failure modes. They do not establish live trading performance, real-market alpha,
or a universal advantage for retained reasoning across unrelated workflows.
