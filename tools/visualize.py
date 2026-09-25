"""Inspect PCB 3D model coverage and export reviewable views and geometry."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .hwrepo.three_d import generate, render_text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--project", required=True, help="One registered PCB or PCB-only project ID")
    parser.add_argument("--check-models", action="store_true", help="Inspect model coverage without KiCad")
    parser.add_argument("--runner", choices=("auto", "local", "container"), default="auto",
                        help="Exact local CLI or project digest-pinned Docker image")
    parser.add_argument("--cli", default="kicad-cli", help="KiCad CLI path for an exact local runner")
    parser.add_argument("--output", type=Path, help="Fresh receipt directory under ignored build/")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--detail", choices=("brief", "full"), default="brief",
                        help="Expand human model findings; JSON always includes all findings")
    args = parser.parse_args()
    if args.check_models and args.runner != "auto":
        parser.error("--runner is used only when generating 3D exports")
    if args.format == "json" and args.detail != "brief":
        parser.error("--detail is for text; JSON already includes every finding")
    try:
        report = generate(args.root, args.project, check_models=args.check_models,
                          runner=args.runner, cli=args.cli, output=args.output,
                          detail=args.detail)
    except (OSError, ValueError) as exc:
        print(f"Cannot create 3D receipt: {exc}", file=sys.stderr)
        return 2
    print(report.model_dump_json(indent=2) if args.format == "json"
          else render_text(report, args.detail))
    return 0 if report.status == "PASS" else (2 if report.status == "ERROR" else 1)


if __name__ == "__main__":
    raise SystemExit(main())
