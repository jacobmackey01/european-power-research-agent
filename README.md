# European Power Research Agent

A benchmarkable OpenAI Responses API harness for multi-step European
power-market research. GPT-5.6 Sol decides which analysis tool to use next;
deterministic Python functions own the data checks, calculations, validation,
and scoring.

This is deliberately not a chatbot wrapped around a spreadsheet. It is an
experiment in whether an agent that preserves its reasoning and observations
across a long investigation produces better, more efficient research decisions
than an otherwise equivalent agent with truncated memory.

## Research motivation

OpenAI's 29 July 2026 research publication,
[*How enabling two settings tripled our scores on the ARC-AGI-3
benchmark*](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/),
reported that GPT-5.6 Sol's public-set score increased from 13.3% with the
official harness to 38.3% when the Responses API harness retained reasoning and
used compaction. The publication also reported roughly six times fewer output
tokens. Its central finding was about the system around the model: an agent that
forgot private reasoning after every action and eventually lost older actions
had to repeatedly reconstruct what it had learned.

This repository tests whether that harness finding transfers to a very
different workflow: iterative energy-market research. It does **not** claim that
the ARC-AGI-3 score increase will reproduce in this domain. The transfer claim
is a hypothesis, measured here with controlled harness ablations.

The implementation follows OpenAI's current guidance to use the
[Responses API](https://developers.openai.com/api/docs/guides/latest-model),
continue stable multi-turn work with
[`previous_response_id`](https://developers.openai.com/api/docs/guides/conversation-state),
enable
[server-side compaction](https://developers.openai.com/api/docs/guides/compaction),
and expose calculations through strict
[function tools](https://developers.openai.com/api/docs/guides/function-calling).
ARC-AGI-3's public games are available from
[ARC Prize](https://arcprize.org/arc-agi/3/).

## What the agent does

Each benchmark episode presents an unfamiliar research question with a seeded,
known failure mode. The agent must build an evidence chain rather than guess:

```text
market question
      |
      v
GPT-5.6 Sol chooses one strict tool call
      |
      v
deterministic environment returns evidence + evidence ID
      |
      +------> next decision (repeat)
      |
      v
evidence-cited research memo
      |
      v
deterministic evaluator
```

The initial public development set covers:

- a duplicated local hour at the daylight-saving transition;
- a silent GW-to-MW unit-scale shift;
- a regime-dependent forecasting signal that does not survive inference and
  transaction-cost stress.

The model never performs the authoritative arithmetic. Tools return
pre-computed, deterministic statistics, and the evaluator checks the submitted
conclusion, root cause, required evidence, citation validity, and unnecessary
repeated calls.

## The three harness conditions

| Condition | Private reasoning | Earlier public actions | Compaction |
|---|---|---|---|
| `stateless-truncated` | discarded each turn | rolling window only | no |
| `retained-reasoning` | retained with `previous_response_id` | retained | no |
| `retained-reasoning-compaction` | retained with `previous_response_id` | retained | yes |

The stateless condition is intentionally weaker but transparent: each API call
is independent and receives only a bounded text record of recent tool
observations. The other conditions use the Responses API's native continuation.
This lets the project isolate the value of memory and compaction while holding
the model, prompt, tools, episodes, and evaluator constant.

## Experiment 001 result

The preregistered 31 July 2026 experiment ran eight sealed synthetic episodes,
twice per condition, with GPT-5.6 Sol at `max` reasoning: 48 runs in total.

| Condition | Mean score | Exact success | Estimated cost |
|---|---:|---:|---:|
| `stateless-truncated` | 0.0 / 100 | 0 / 16 | $1.5706 |
| `retained-reasoning` | 100.0 / 100 | 16 / 16 | $0.9127 |
| `retained-reasoning-compaction` | 97.5 / 100 | 14 / 16 | $1.2704 |

Retained reasoning improved the primary composite score by 100 points versus
the stateless rolling-history baseline (episode-clustered 95% CI [100, 100],
exact two-sided sign-flip `p=0.0078125`). It also used 35.2% fewer output tokens
and cost 41.9% less. Every stateless run exhausted the fixed eight-step budget
after losing and reconstructing older evidence; the raw logs contain 61 repeated
tool calls.

The forced 1,000-token compaction condition activated in all 16 runs, but its
separate hypothesis was **not** supported. It missed the preregistered five-point
non-inferiority margin, achieved 14/16 rather than 16/16 exact successes, used
8.0% more output tokens, cost 39.2% more, and took 198.6% longer than retained
reasoning without compaction. The combined harness still beat the stateless
baseline, but this experiment attributes that result to retention—not a measured
compaction benefit.

Read the [preregistration](experiments/001/README.md), [full result and claim
boundary](experiments/001/results.md), and [raw run records](outputs/experiment-001.json).

## Why GPT-5.6 Sol with `max` reasoning

The default experiment uses `gpt-5.6-sol` with explicit
`reasoning.effort="max"` because the purpose is to study a quality-first,
multi-step controller that must revise hypotheses over several tool calls. That
is different from a short schema-parsing function, where low effort is usually
the better latency and cost baseline.

`max` is an experimental treatment, not a universal best setting. The
evaluation protocol requires comparison with lower efforts before making a
cost-effectiveness claim. A one-episode API smoke test can use `low` to verify
request compatibility without pretending it measures research quality.

## Quick start

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Supply the API key through the process environment or an ignored local
environment file. The repository contains only a blank `.env.example`.

```powershell
$env:OPENAI_API_KEY = "your-key-from-a-secure-secret-store"
power-research-agent list-episodes
power-research-agent run `
  --episode dst-transition-duplicate `
  --mode retained-reasoning-compaction `
  --effort max
```

Run all three conditions only when you intentionally want to make the
corresponding live API calls:

```powershell
power-research-agent evaluate `
  --episodes all `
  --modes all `
  --effort max `
  --output outputs/benchmark.json
```

For the one-time unseen evaluation, model-visible cases and the evaluator-only
answer key were stored separately and kept out of Git until the run was frozen.
The preregistration initially contained only their hashes. The runner verified
those hashes before the first paid call and checkpointed every randomized run:

```powershell
power-research-agent verify-suite `
  --preregistration experiments/001/preregistration.json `
  --episodes-file private/sealed-energy-memory-001/episodes.json `
  --answers-file private/sealed-energy-memory-001/answers.json

power-research-agent experiment `
  --preregistration experiments/001/preregistration.json `
  --episodes-file private/sealed-energy-memory-001/episodes.json `
  --answers-file private/sealed-energy-memory-001/answers.json `
  --output outputs/experiment-001.json
```

The answer key was released only after result freezing, so the suite is now a
public regression set and cannot be called unseen in a future experiment. The
API key remains ignored, stays only in the process environment, and never appears
in the result file.

Local, deterministic tests make no API calls:

```powershell
pytest
```

## Evaluation discipline

The initial episodes are a transparent development set: their labels are in the
repository, although expected answers are never included in model inputs. The
Experiment 001 cases were hash-locked and unseen for their first run, then
released with all results. They are now suitable for regression testing, not a
second hidden-benchmark claim.

A defensible project result requires:

1. freezing the prompt, tools, scoring rule, model snapshot, and run budget;
2. creating a separate hidden episode set whose labels are withheld from model
   inputs and experiment-time code changes;
3. running repeated draws per condition in a frozen randomized order;
4. reporting task score, failure modes, input/output/reasoning tokens, latency,
   and estimated cost rather than selecting a single favourable run;
5. preserving raw response IDs and tool-event logs without storing secrets.

See [the evaluation protocol](docs/evaluation-protocol.md) and
[research foundation](docs/research-foundation.md) for the exact claims this
project can and cannot support.

## Commercial relevance

The project demonstrates a workflow relevant to energy analytics and junior
data-science work: messy time-series diagnostics, walk-forward validation,
statistical uncertainty, cost-aware strategy stress testing, programmatic LLM
integration, agent memory, hallucination controls, and reproducible evaluation.
The agent is an orchestration layer around auditable analytics—not a replacement
for validation or a source of trading advice.

## Status

Version `0.1.0` is an MVP research harness with deterministic development
episodes, three API conditions, a strict tool loop, scoring, a resumable
hash-locked experiment runner, paired inference, and offline tests. Experiment
001 is complete and public: it supports a retained-reasoning advantage on the
defined synthetic memory-stress set, while rejecting a compaction-efficiency
claim at the forced 1,000-token threshold.

Real market-data connectors, a larger independently authored hidden set, and a
production-scale long-context compaction study remain future phases.
