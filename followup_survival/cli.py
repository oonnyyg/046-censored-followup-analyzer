from __future__ import annotations

import argparse
import sys

from .config import load_config
from .errors import FollowupError
from .reader import read_records
from .report import write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m followup_survival",
        description=(
            "Build a reviewable Kaplan-Meier style survival report from "
            "censored follow-up records."
        ),
    )
    parser.add_argument(
        "--records",
        required=True,
        help="Path to the follow-up records CSV file.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the JSON configuration file with query_days.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where the three report files are written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        records = read_records(args.records, config)
        write_reports(records, config, args.output_dir)
    except FollowupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 1
    return 0
