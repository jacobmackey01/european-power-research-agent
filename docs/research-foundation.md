# Research foundation

## Source that motivated the project

OpenAI. (2026, July 29).
[*How enabling two settings tripled our scores on the ARC-AGI-3
benchmark*](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/).
Research publication.

The supplied publication reports the following result on the ARC-AGI-3 public
task set:

- official generic harness: 13.3% Relative Human Action Efficiency;
- Responses API harness with retained reasoning and compaction: 38.3%;
- approximately six times fewer output tokens with the improved harness.

The proposed mechanism is cumulative memory. In the generic harness, private
reasoning was discarded after each action and older public actions were removed
by a rolling truncation window. Continuing through the Responses API made prior
reasoning available, while compaction preserved useful state over longer runs.

These figures are cited as the motivation for this repository, not as results
produced by it.

## Transfer hypothesis

Energy-market research can have the same abstract shape as a long-running
interactive puzzle:

1. inspect an unfamiliar state;
2. choose an action;
3. observe a deterministic result;
4. revise a hypothesis;
5. remember failed paths and accumulated evidence;
6. stop when the evidence supports a decision.

The domain is intentionally different from ARC-AGI-3. A positive result would
therefore be evidence that retained reasoning helps this particular research
harness—not proof of a general law about all agents or all analytical work.

## Implementation sources

- [OpenAI model guidance](https://developers.openai.com/api/docs/guides/latest-model)
  recommends GPT-5.6 Sol for frontier capability, explicit reasoning effort,
  the Responses API for tool-using workflows, and `reasoning.context="all_turns"`
  with `previous_response_id` when prior reasoning remains relevant.
- [Conversation state](https://developers.openai.com/api/docs/guides/conversation-state)
  documents continuation with `previous_response_id`.
- [Compaction](https://developers.openai.com/api/docs/guides/compaction)
  documents server-side context management for long-running conversations.
- [Function calling](https://developers.openai.com/api/docs/guides/function-calling)
  documents strict JSON schemas and `function_call_output` continuation items.
- [ARC Prize](https://arcprize.org/arc-agi/3/) describes ARC-AGI-3 and provides
  public interactive tasks.

## Design boundary

GPT-5.6 Sol is the controller. It may choose tools, compare returned evidence,
revise a plan, and write a concise memo. It is not the numerical authority.

The deterministic environment owns:

- time-zone and unit checks;
- walk-forward folds;
- confidence intervals and significance calculations;
- strategy-cost and stress calculations;
- benchmark labels and scoring.

This boundary reduces the opportunity for fabricated calculations while still
testing the model's multi-step research judgment.

## Research questions

The MVP is designed to answer:

1. Does retained reasoning improve episode success versus a stateless rolling
   window when all other observable components are held constant?
2. On sufficiently long episodes, does compaction preserve or improve task
   success while reducing output-token use?
3. At a fixed harness condition, does `max` reasoning improve enough over
   `xhigh`, `high`, or `medium` to justify its latency and cost?
4. Which failure modes remain: wrong tool selection, repeated calls, premature
   conclusions, missed counter-evidence, or unsupported citations?

Short development episodes may not reach the compaction threshold. They verify
the API path but cannot by themselves establish a compaction benefit.
