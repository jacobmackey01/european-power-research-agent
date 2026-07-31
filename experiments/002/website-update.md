# Paste-ready Sol versus Luna website update

Following [OpenAI's ARC-AGI-3 research on retained reasoning and
compaction](https://openai.com/index/how-two-settings-tripled-our-arc-agi-3-scores/),
I extended the same European Power Research Agent with a preregistered GPT-5.6
Luna/max replication, holding the synthetic cases, deterministic tools,
evaluator, three harness conditions, and 48-run design fixed from the original
Sol/max experiment. Luna reproduced the core retention result: retained
reasoning scored 94.4/100 with 13/16 exact successes versus 0/100 and 0/16 for a
stateless three-action history (paired episode difference +94.4, 95% CI [88.8,
98.1], exact sign-flip p=0.0078). Sol remained stronger in retained mode at
100/100 and 16/16, while Luna completed the full matrix 19.9% faster and at an
estimated $0.157 versus $3.754—about 24 times cheaper under their respective
price snapshots. Luna used 1.5% more output tokens overall, so the cost advantage
came from pricing rather than token efficiency. Forced compaction again failed
its preregistered quality-preservation and output-token-reduction rules; one Luna
compaction run hit an API 500 and was retained as a zero rather than selectively
rerun. Boundary: this is a controlled replication on the already released
eight-case synthetic suite, not a new hidden-set benchmark or evidence of live
market alpha, and p=0.0078 is the exact test's minimum with eight independent
episodes.
