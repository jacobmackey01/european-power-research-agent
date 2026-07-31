# Experiment 002 results

**Outcome:** GPT-5.6 Luna at `max` reasoning reproduced the primary retained-state
advantage on the released synthetic memory-stress suite. It did not match Sol's
retained-mode accuracy, and forced compaction again failed its registered
quality-preservation and output-token-reduction rules.

The matrix ran from 21:07:15 to 21:39:22 UTC on 31 July 2026. It used
`gpt-5.6-luna`, `reasoning.effort="max"`, the standard service tier, eight
episodes, two repeats, and three harness conditions: 48 runs. Estimated matrix
cost was **$0.156525** using the preregistered 31 July Luna price snapshot.

This is Experiment 002 in the same ARC-AGI-3-inspired project as the Sol study.
It deliberately reused the released Experiment 001 suite, deterministic tools,
evaluator, prompts, step budget, and forced-compaction threshold. It is therefore
a controlled replication and regression test, not a second hidden-set result.

## Luna condition results

| Condition | Mean score | Exact success | Input tokens | Output tokens | Reasoning tokens | Duration | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stateless truncated | 0.0 | 0/16 | 138,457 | 24,060 | 17,826 | 377.8 s | $0.060700 |
| Retained reasoning | 94.375 | 13/16 | 115,753 | 19,020 | 10,416 | 282.1 s | $0.039131 |
| Retained + forced compaction | 93.75 | 15/16 | 180,128 | 17,887 | 2,658 | 1,133.3 s | $0.056694 |

All 16 stateless runs exhausted the frozen eight-step budget without submitting
a memo. Their event records contain **63 repeated deterministic tool calls** as
the three-action rolling history discarded earlier evidence. Neither retained
condition made a repeated or invalid tool call.

## Primary Luna retention contrast

Retained reasoning versus stateless truncated:

- composite-score difference: **+94.375 points**;
- episode-clustered paired 95% bootstrap CI: **[88.75, 98.125]**;
- exact two-sided episode-level sign-flip test: **p=0.0078125**;
- exact-success difference: **+81.25 percentage points** (13/16 versus 0/16);
- 16.4% fewer input tokens, 20.9% fewer output tokens, and 41.6% fewer
  reasoning tokens;
- 25.3% lower measured latency and 35.5% lower estimated cost.

This satisfies both preregistered Luna retention rules. Every one of the eight
independent episodes improved, which also means `p=0.0078125` is the smallest
two-sided exact sign-flip p-value available at this sample size. The result is
strong for this deliberately memory-stressing suite, but the eight-case design
cannot measure fine-grained general performance.

Three retained runs scored 70/100. Each recovered all required evidence and the
correct root cause but selected the wrong final decision label. Unlike Sol's
saturated 16/16 retained score, these misses expose variation that this scoring
rule can detect; they are also direct evidence that Luna did not match Sol's
accuracy in this condition.

## Forced-compaction contrast

The API emitted **74 encrypted compaction items**. Compaction activated in 15 of
16 designated runs, above the registered 80% activation gate. The remaining run
ended on an OpenAI API HTTP 500; it was retained as a zero rather than selectively
rerun. The other 15 compacted runs were exact successes.

Forced compaction versus retained reasoning without compaction produced:

- score difference: **-0.625 points**, 95% CI **[-16.875, 9.375]**;
- exact success: **15/16 versus 13/16**;
- output-token difference: **-70.813 per run**, 95% CI
  **[-283.438, 82.313]**;
- 74.5% fewer reasoning tokens, but 55.6% more input tokens;
- 44.9% higher estimated cost and 301.7% higher measured latency.

The score interval crossed the registered -5 point non-inferiority margin, and
the output-token interval crossed zero. Neither preregistered compaction claim
was supported. The combined retained-plus-compaction condition still beat the
stateless baseline, but this replication again attributes the measured benefit
to retained state rather than compaction at the aggressive 1,000-token threshold.

## Sol versus Luna: paired descriptive comparison

The model was the intended treatment change, but the two matrices ran in
separate time blocks after the suite had been released. These comparisons are
therefore descriptive; no cross-model significance test was preregistered.

| Condition | Sol mean / exact | Luna mean / exact | Descriptive result |
|---|---:|---:|---|
| Stateless truncated | 0.0; 0/16 | 0.0; 0/16 | Both failed every run |
| Retained reasoning | 100.0; 16/16 | 94.375; 13/16 | Sol +5.625 score points |
| Retained + forced compaction | 97.5; 14/16 | 93.75; 15/16 | Sol +3.75 points; Luna +1 exact run |

| Full 48-run matrix | Sol | Luna | Luna change |
|---|---:|---:|---:|
| Input tokens | 403,040 | 434,338 | +7.8% |
| Output tokens | 60,082 | 60,967 | +1.5% |
| Reasoning tokens | 29,682 | 30,900 | +4.1% |
| Measured API duration | 2,238.8 s | 1,793.3 s | -19.9% |
| Estimated cost | $3.753742 | $0.156525 | -95.8% |

Luna used **19.9% less summed API duration** and was **24 times cheaper** under
the two experiments' registered price snapshots. It was not more token-efficient
overall: input, output, and reasoning-token totals were all slightly higher. The
cost difference therefore comes from model pricing, not from a reduction in
total token use.

The defensible model-selection conclusion is workload-specific. Sol produced
the stronger retained-mode quality result; Luna preserved most of that quality,
replicated the central retention effect, completed faster, and cost much less.
A direct model-superiority claim would require an independently authored hidden
suite with Sol and Luna interleaved in the same randomized execution block.

## Reproducibility and audit trail

- [Preregistration](preregistration.json)
- [Released model-visible episodes](../../private/sealed-energy-memory-001/episodes.json)
- [Released evaluator-only answer key](../../private/sealed-energy-memory-001/answers.json)
- [Complete Luna run records](../../outputs/experiment-002.json)
- [Experiment 001 Sol results](../001/results.md)
- [Result manifest and hashes](result-manifest.json)
- Published LF-normalized result SHA-256:
  `7dcbdcca1994e0da8c2597d429b310700e3c79303022449ac13240600415342d`
- Original Windows checkpoint SHA-256 before Git newline normalization:
  `07799bdc21f314c5171ccaabd22371a0b02ce4446b0b535f31d5ed7cdf9aac52`

The result file contains response IDs, tool events, scores, usage, activation
counts, pricing assumptions, paired intervals, and every failure. The runner's
recorded preregistration hash matches the committed file, all 48 job IDs are
unique, and a post-run secret scan found no API key or key-like string.

The experiment was inspired by OpenAI's
[*How enabling two settings tripled our scores on the ARC-AGI-3
benchmark*](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/).
Cost uses the recorded [API pricing](https://developers.openai.com/api/docs/pricing)
snapshot rather than claiming the estimate is immutable.
