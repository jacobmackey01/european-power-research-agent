# Experiment 002: Luna replication

This experiment asks whether GPT-5.6 Luna at `max` reasoning reproduces the
retained-state result from Experiment 001 when the model is the only intended
treatment change.

It is the second experiment in the same ARC-AGI-3-inspired research programme,
not a separate project. The shared idea is to test whether an agent performs
better when the Responses API carries forward prior reasoning and accumulated
evidence, with compaction used to manage a longer investigation. Experiment 002
keeps that harness fixed and changes only the model family from Sol to Luna.

The 48-run matrix reuses the exact released synthetic cases, deterministic
tools, scoring rule, three harness conditions, two repeats, step budget,
compaction threshold, and service tier from Experiment 001. It changes the model
from `gpt-5.6-sol` to `gpt-5.6-luna` and uses a new randomized execution order.

## Evidential status

This is a preregistered replication on a **released** suite, not a second hidden
set. Expected answers remain absent from model inputs, but the cases and labels
were published after Experiment 001. The within-Luna retained-versus-stateless
contrast is the primary replication test. Comparisons with the earlier Sol run
are paired descriptive analyses because the models were executed at different
times rather than in one interleaved model-randomized matrix.

## Frozen execution

```powershell
power-research-agent verify-suite `
  --preregistration experiments/002/preregistration.json `
  --episodes-file private/sealed-energy-memory-001/episodes.json `
  --answers-file private/sealed-energy-memory-001/answers.json

power-research-agent experiment `
  --preregistration experiments/002/preregistration.json `
  --episodes-file private/sealed-energy-memory-001/episodes.json `
  --answers-file private/sealed-energy-memory-001/answers.json `
  --output outputs/experiment-002.json
```

The client-side cost guard stops before the next paid run when the accumulated
estimate plus its reserve would exceed the registered cap. An incomplete matrix
cannot support the replication claim and may be resumed only against the same
preregistration hash.
