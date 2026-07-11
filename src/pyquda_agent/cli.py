"""Command-line interface for pyquda-agent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from pyquda_agent.app import run_command
from pyquda_agent.config import DEFAULT_API_KEY_FILE
from pyquda_agent.config import DEFAULT_OUTPUT_PATH
from pyquda_agent.config import DEFAULT_PYQUDA_REPO
from pyquda_agent.config import RunConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pyquda-agent", description="PyQUDA analysis and script-generation helper.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Parse a PyQUDA task and generate a script or template.")
    run_parser.add_argument("task_description", help="Natural-language task description.")
    run_parser.add_argument("--backend", required=True, choices=("api", "codex"))
    run_parser.add_argument("--model", default=None, help="API model as provider/model_id for --backend api.")
    run_parser.add_argument("--api-key-file", type=Path, default=DEFAULT_API_KEY_FILE)
    run_parser.add_argument("--base-url", default=None)
    run_parser.add_argument("--pyquda-repo", type=Path, default=DEFAULT_PYQUDA_REPO)
    run_parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    run_parser.add_argument("--interactive", action=argparse.BooleanOptionalAction, default=True)
    run_parser.add_argument("--max-questions", type=int, default=7)
    run_parser.add_argument("--save-session", type=Path, default=None)
    run_parser.add_argument("--resume-session", type=Path, default=None)
    run_parser.add_argument("--print-context", action="store_true")
    run_parser.add_argument("--dry-run", action="store_true")
    run_parser.add_argument("--verbose", action="store_true")
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.command != "run":
        raise ValueError(f"Unsupported command {args.command!r}.")
    if args.backend == "codex" and args.model:
        print("warning: --model is ignored for backend='codex'.", file=sys.stderr)
    if args.backend == "api" and args.model:
        print("warning: --model is currently ignored for backend='api' on the fixed local workflow.", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _validate_args(args)
        result = run_command(
            RunConfig(
                task_description=args.task_description,
                backend=args.backend,
                model=args.model,
                api_key_file=args.api_key_file,
                base_url=args.base_url,
                pyquda_repo=args.pyquda_repo.expanduser().resolve(),
                output=args.output.expanduser().resolve(),
                interactive=args.interactive,
                max_questions=args.max_questions,
                save_session=args.save_session.expanduser().resolve() if args.save_session else None,
                resume_session=args.resume_session.expanduser().resolve() if args.resume_session else None,
                print_context=args.print_context,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
