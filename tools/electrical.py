"""Analyze grounding, startup/steady-state power and high-frequency circuit behavior."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .hwrepo.contract_coach import (
    AutoNetlistRunner,
    ContainerNetlistRunner,
    LocalNetlistRunner,
    NetlistRunner,
)
from .hwrepo.electrical_runner import analyze, format_report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--project", required=True)
    parser.add_argument("--output", type=Path, help="Fresh directory below ignored build/")
    parser.add_argument("--native-summary", type=Path, help="Existing source-bound native project summary")
    parser.add_argument("--runner", choices=("auto", "local", "container"), default="auto")
    parser.add_argument("--cli", default="kicad-cli")
    parser.add_argument("--ngspice", default="ngspice", help="Exact contract-pinned ngspice executable")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", args.project) is None:
        parser.error("Invalid project ID")
    runner: NetlistRunner = (LocalNetlistRunner(args.cli) if args.runner == "local" else
                            ContainerNetlistRunner() if args.runner == "container" else AutoNetlistRunner(args.cli))
    try:
        report = analyze(args.root, args.project, args.output, args.native_summary,
                         args.cli, args.ngspice, runner)
    except (OSError, ValueError) as exc:
        print(f"Cannot create electrical receipt: {exc}", file=sys.stderr)
        return 2
    print(report.model_dump_json(indent=2) if args.format == "json" else format_report(report))
    return 0 if report.status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
