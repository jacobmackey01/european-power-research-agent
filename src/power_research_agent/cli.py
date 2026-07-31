from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from power_research_agent.benchmark import load_sealed_suite
from power_research_agent.environment import ResearchEnvironment
from power_research_agent.episodes import get_episode, list_episodes
from power_research_agent.evaluation import benchmark_summary, score_run
from power_research_agent.experiment import run_preregistered_experiment
from power_research_agent.harness import HarnessConfig, ResponsesHarness
from power_research_agent.models import HarnessMode

EFFORTS = ("none", "low", "medium", "high", "xhigh", "max")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="power-research-agent",
        description="Run controlled Responses API harness experiments.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-episodes", help="List deterministic development episodes.")

    run_parser = subparsers.add_parser("run", help="Run and score one live API episode.")
    _add_shared_run_args(run_parser)
    run_parser.add_argument(
        "--episode",
        required=True,
        choices=[episode.episode_id for episode in list_episodes()],
    )
    run_parser.add_argument("--output", type=Path, help="Optional JSON output path.")

    eval_parser = subparsers.add_parser(
        "evaluate",
        help="Run a live matrix. This intentionally makes one or more paid API calls.",
    )
    _add_shared_run_args(eval_parser, include_mode=False)
    eval_parser.add_argument(
        "--episodes",
        nargs="+",
        default=["all"],
        choices=["all", *[episode.episode_id for episode in list_episodes()]],
    )
    eval_parser.add_argument(
        "--modes",
        nargs="+",
        default=["all"],
        choices=["all", *[mode.value for mode in HarnessMode]],
    )
    eval_parser.add_argument("--output", type=Path, required=True)

    verify_parser = subparsers.add_parser(
        "verify-suite",
        help="Verify a sealed suite and preregistered hashes without making API calls.",
    )
    _add_sealed_suite_args(verify_parser)

    experiment_parser = subparsers.add_parser(
        "experiment",
        help="Run or resume a hash-locked paid experiment from its preregistration.",
    )
    _add_sealed_suite_args(experiment_parser)
    experiment_parser.add_argument("--output", type=Path, required=True)
    experiment_parser.add_argument("--resume", action="store_true")
    return parser


def _add_sealed_suite_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--episodes-file", type=Path, required=True)
    parser.add_argument("--answers-file", type=Path, required=True)


def _add_shared_run_args(
    parser: argparse.ArgumentParser,
    *,
    include_mode: bool = True,
) -> None:
    if include_mode:
        parser.add_argument(
            "--mode",
            choices=[mode.value for mode in HarnessMode],
            default=HarnessMode.RETAINED_REASONING_COMPACTION.value,
        )
    parser.add_argument(
        "--model",
        default=os.getenv("POWER_AGENT_MODEL", "gpt-5.6-sol"),
    )
    parser.add_argument(
        "--effort",
        choices=EFFORTS,
        default=os.getenv("POWER_AGENT_REASONING_EFFORT", "max"),
    )
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-output-tokens", type=int, default=4096)
    parser.add_argument("--compact-threshold", type=int, default=200_000)
    parser.add_argument("--stateless-history-window", type=int, default=3)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "list-episodes":
        for episode in list_episodes():
            print(f"{episode.episode_id}\t{episode.title}")
        return 0

    if args.command == "verify-suite":
        suite = load_sealed_suite(
            args.episodes_file,
            args.answers_file,
            preregistration_path=args.preregistration,
        )
        print(
            json.dumps(
                {
                    "suite_id": suite.suite_id,
                    "episode_count": len(suite.episodes),
                    "episodes_sha256": suite.episodes_sha256,
                    "answers_sha256": suite.answers_sha256,
                    "status": "verified",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    _require_api_key()
    if args.command == "run":
        record = _run_once(args, get_episode(args.episode), HarnessMode(args.mode))
        payload = json.dumps(record, indent=2, sort_keys=True)
        print(payload)
        if args.output:
            _write_json(args.output, record)
        return 0 if record["score"]["exact_success"] else 2

    if args.command == "evaluate":
        episodes = (
            list_episodes()
            if "all" in args.episodes
            else [get_episode(episode_id) for episode_id in args.episodes]
        )
        modes = (
            list(HarnessMode) if "all" in args.modes else [HarnessMode(mode) for mode in args.modes]
        )
        records: list[dict[str, Any]] = []
        for episode in episodes:
            for mode in modes:
                print(
                    f"Running {episode.episode_id} with {mode.value}...",
                    file=sys.stderr,
                )
                records.append(_run_once(args, episode, mode))
        payload = {
            "experiment": {
                "model": args.model,
                "reasoning_effort": args.effort,
                "episode_ids": [episode.episode_id for episode in episodes],
                "modes": [mode.value for mode in modes],
            },
            "summary": benchmark_summary(records),
            "records": records,
        }
        _write_json(args.output, payload)
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
        return 0


    if args.command == "experiment":
        payload = run_preregistered_experiment(
            preregistration_path=args.preregistration,
            episodes_path=args.episodes_file,
            answers_path=args.answers_file,
            output_path=args.output,
            resume=args.resume,
            progress=lambda message: print(message, file=sys.stderr),
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "completed_runs": payload["completed_runs"],
                    "planned_runs": payload["planned_runs"],
                    "summary": payload["summary"],
                    "claim_assessment": payload["claim_assessment"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if payload["status"] == "complete" else 3

    raise AssertionError(f"Unhandled command: {args.command}")


def _run_once(
    args: argparse.Namespace,
    episode: Any,
    mode: HarnessMode,
) -> dict[str, Any]:
    environment = ResearchEnvironment(episode)
    config = HarnessConfig(
        mode=mode,
        model=args.model,
        reasoning_effort=args.effort,
        max_steps=args.max_steps,
        max_output_tokens=args.max_output_tokens,
        compact_threshold=args.compact_threshold,
        stateless_history_window=args.stateless_history_window,
    )
    run = ResponsesHarness(config).run(environment)
    score = score_run(run, episode)
    return {"run": run.to_dict(), "score": score.to_dict()}


def _require_api_key() -> None:
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Load it from a secure secret store or an "
            "ignored local environment file before making live API calls."
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
