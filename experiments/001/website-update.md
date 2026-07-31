# Paste-ready portfolio update

## Status label

SEALED BENCHMARK COMPLETE · RETENTION EFFECT SUPPORTED

## Project copy

Can an LLM produce better multi-step power-market research when it retains its
reasoning and accumulated evidence rather than repeatedly reconstructing the
investigation?

Inspired by OpenAI's ARC-AGI-3 harness research, I built and preregistered a
controlled Responses API experiment using GPT-5.6 Sol at max reasoning. Eight
hash-locked synthetic European power-market investigations each required five
sequential evidence gates. I ran every case twice across three conditions:
stateless with a three-action rolling history, retained reasoning, and retained
reasoning with deliberately forced compaction—48 API runs in randomized order.

Retained reasoning achieved 16/16 exact successes and a 100/100 mean score,
versus 0/16 and 0/100 for the stateless baseline. The paired episode-level
difference was +100 points (95% CI [100, 100], exact sign-flip p=0.0078), while
using 35.2% fewer output tokens and costing 41.9% less. Every stateless run
exhausted the fixed step budget after losing and reconstructing earlier evidence.

Forced compaction fired in all 16 designated runs, but it did not meet the
preregistered quality-preservation or output-token-reduction rules: it scored
97.5/100 with 14/16 exact successes, used 8.0% more output tokens, cost 39.2%
more, and took 198.6% longer than retained reasoning alone.

Decision: The experiment supports retained reasoning for this defined synthetic
memory-stress workflow. It does not support a compaction benefit at the aggressive
1,000-token threshold, and it does not claim live-market alpha or universal
generalisation. Full preregistration, cases, answer key, failures, usage, and raw
run records are published in the repository.

## Suggested tags

PYTHON

GPT-5.6 SOL

RESPONSES API

PREREGISTERED EVALUATION
