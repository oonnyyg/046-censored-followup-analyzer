"""Command line entry: python -m followup_survival --records ... --config ... --out ..."""

import argparse
import os
import sys

from .analysis import analyze_all
from .errors import FollowupError
from .report import build_outputs
from .validation import load_query_days, load_records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m followup_survival",
        description="Kaplan-Meier survival report from censored follow-up records.",
    )
    parser.add_argument("--records", required=True, help="follow-up CSV path")
    parser.add_argument("--config", required=True, help="query-days JSON path")
    parser.add_argument("--out", required=True, help="output directory")
    args = parser.parse_args(argv)

    try:
        records = load_records(args.records)
        query_days = load_query_days(args.config)
        results = analyze_all(records)
        outputs = build_outputs(results, query_days)
        _write_atomically(args.out, outputs)
    except FollowupError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for filename in outputs:
        print(f"wrote {os.path.join(args.out, filename)}")
    return 0


def _write_atomically(out_dir: str, outputs: dict[str, str]) -> None:
    if os.path.exists(out_dir) and not os.path.isdir(out_dir):
        raise FollowupError(f"output path is not a directory: {out_dir}")

    target_paths = {name: os.path.join(out_dir, name) for name in outputs}

    os.makedirs(out_dir, exist_ok=True)
    written: list[str] = []
    try:
        for name, content in outputs.items():
            tmp_path = target_paths[name] + ".tmp"
            with open(tmp_path, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
            written.append(tmp_path)
        for tmp_path in written:
            os.replace(tmp_path, tmp_path[:-4])
    except OSError as exc:
        for tmp_path in written:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise FollowupError(f"failed writing report: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
