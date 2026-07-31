# Experiment 001 results

**Outcome:** retained reasoning was decisively better than the stateless
three-action rolling history on this sealed synthetic memory-stress set. Forced
compaction at 1,000 tokens did not preserve quality within the registered margin
and did not reduce output tokens.

The matrix ran from 12:33:28 to 13:12:13 UTC on 31 July 2026. It used
`gpt-5.6-sol`, `reasoning.effort="max"`, the standard service tier, eight
episodes, two repeats, and three harness conditions: 48 runs. Estimated matrix
cost was **$3.753741** using the preregistered 31 July price snapshot.

## Condition results

| Condition | Mean score | Exact success | Input tokens | Output tokens | Reasoning tokens | Duration | Estimated cost |
|---|---:|---:|---:|---:|---:|---:|---:|
| Stateless truncated | 0.0 | 0/16 | 139,099 | 25,601 | 18,710 | 599.7 s | $1.570628 |
| Retained reasoning | 100.0 | 16/16 | 115,066 | 16,577 | 7,804 | 411.1 s | $0.912708 |
| Retained + forced compaction | 97.5 | 14/16 | 148,875 | 17,904 | 3,168 | 1,227.9 s | $1.270406 |

All 16 stateless runs exhausted the frozen eight-step budget without submitting
a memo. The raw event records show **61 repeated deterministic tool calls** as
the rolling history discarded earlier evidence. Retained reasoning completed all
16 runs without a repeated or invalid tool call.

## Primary retention contrast

Retained reasoning versus stateless truncated:

- composite-score difference: **+100.0 points**;
- episode-clustered paired 95% bootstrap CI: **[100.0, 100.0]**;
- exact two-sided episode-level sign-flip test: **p=0.0078125**;
- exact-success difference: **+100 percentage points** (16/16 versus 0/16);
- 17.3% fewer input tokens, 35.2% fewer output tokens, and 58.3% fewer
  reasoning tokens;
- 31.4% lower measured latency and 41.9% lower estimated cost.

This satisfies the preregistered primary rule. The defensible claim is narrow:
on eight hash-locked synthetic power-market investigations whose final memo
required evidence older than a three-action rolling window, preserving Responses
API reasoning and state improved success and efficiency.

The experiment does not establish a universal memory advantage, performance on
live market research, or trading alpha. The set deliberately stresses the failure
mode under study, and eight episodes—not the 16 repeated draws—are the independent
units.

## Forced-compaction contrast

The API emitted **62 encrypted compaction items**, with at least one in every
compaction-condition run, so the activation gate passed. Nevertheless, forced
compaction versus retained reasoning without compaction produced:

- score difference: **-2.5 points**, 95% CI **[-6.875, 0.0]**;
- exact success: **14/16 versus 16/16**;
- output-token difference: **+82.94 per run**, 95% CI **[15.375, 145.063]**;
- 59.4% fewer reasoning tokens, but 29.4% more input tokens and 8.0% more total
  output tokens;
- 39.2% higher estimated cost and 198.6% higher measured latency.

The lower confidence bound crossed the registered -5 point non-inferiority
margin, so quality preservation was not established. Output tokens increased,
so the token-reduction rule also failed. One compacted run selected the wrong
decision and omitted the earliest metadata evidence (65/100); another made the
right decision but omitted that earliest evidence (95/100). These failures are
consistent with information loss under an intentionally aggressive threshold,
but that causal explanation is an inference rather than a separately proven
mechanism.

The combined retained-plus-compaction condition still beat the stateless
baseline. Because retained reasoning alone was both more accurate and more
efficient, the improvement should be attributed to retention in this study, not
to compaction.

## Reproducibility and audit trail

- [Preregistration](preregistration.json)
- [Released model-visible episodes](../../private/sealed-energy-memory-001/episodes.json)
- [Released evaluator-only answer key](../../private/sealed-energy-memory-001/answers.json)
- [Complete run records](../../outputs/experiment-001.json)
- [Result manifest and hashes](result-manifest.json)
- Published LF-normalized result SHA-256:
  `621d8d557f7bc3493670a2d90b5132147f0258ee40aeb171ef002a792366d50a`
- Original Windows checkpoint SHA-256 before Git newline normalization:
  `ba1e705e78939a40fd7be38b853d9084149e18920a53d1b125125c164c4b5a32`

The result file contains response IDs, tool events, scores, usage, activation
counts, pricing assumptions, paired intervals, and every failure. A post-run
secret scan found no API key or key-like string. A diagnostics-only code fix made
after freezing now surfaces repeated-call counts for missing-memo runs; it does
not change their registered zero score, any usage value, or any claim.

The experiment was inspired by OpenAI's
[*How enabling two settings tripled our scores on the ARC-AGI-3
benchmark*](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/).
Implementation choices follow OpenAI's current
[GPT-5.6 model guidance](https://developers.openai.com/api/docs/guides/latest-model)
and [compaction documentation](https://developers.openai.com/api/docs/guides/compaction).
Cost uses the recorded [API pricing](https://developers.openai.com/api/docs/pricing)
snapshot rather than claiming the estimate is immutable.
