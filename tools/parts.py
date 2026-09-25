"""Make a guided component review, BOM and DigiKey upload list for one board."""
from __future__ import annotations

import argparse
from pathlib import Path

from .hwrepo.contract_coach import (
    AutoNetlistRunner,
    ContainerNetlistRunner,
    LocalNetlistRunner,
)
from .hwrepo.parts_workflow import (
    init_preferences,
    load_preferences,
    new_receipt,
    prepare,
    save_report,
    text_report,
)


def count(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use a whole number") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("Use zero or a positive whole number")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, epilog=(
        "Start: python -B -m tools.parts --project YOUR_PROJECT. "
        "Open the printed review page, fix missing part details, then rerun."
    ))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--project", required=True, help="ID shown by tools.template list")
    parser.add_argument("--boards", type=count, help="Number of boards (default: saved value or 1)")
    parser.add_argument("--spare-percent", type=count, help="Extra parts percent, 0–100 (default 0)")
    parser.add_argument("--spare-minimum", type=count, help="Minimum extras per part (default 0)")
    parser.add_argument("--preferences", type=Path,
                        help="Saved JSON preferences; default: island docs/purchasing.json if present")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--init-preferences", type=Path,
                      help="Create a new preferences JSON under this island's docs/ and exit")
    mode.add_argument("--native-summary", type=Path,
                      help="Reuse a source-bound native summary; otherwise capture a fresh netlist")
    parser.add_argument("--runner", choices=("auto", "local", "container"), default="auto")
    parser.add_argument("--cli", default="kicad-cli", help="Exact local KiCad CLI, if selected")
    parser.add_argument("--output", type=Path, help="Fresh receipt directory below ignored build/")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args()
    if args.boards == 0:
        parser.error("--boards must be at least 1")
    if args.spare_percent is not None and args.spare_percent > 100:
        parser.error("--spare-percent must be between 0 and 100")
    if (args.native_summary is not None or args.init_preferences is not None) and (
        args.runner != "auto" or args.cli != "kicad-cli"
    ):
        parser.error("--runner and --cli apply only to fresh capture")
    if args.init_preferences is not None and args.output is not None:
        parser.error("--output applies only to a parts review")
    root = args.root.resolve()
    try:
        if args.init_preferences is not None:
            preferences = load_preferences(
                root, args.project, args.preferences, args.boards,
                args.spare_percent, args.spare_minimum,
            )
            path = init_preferences(root, args.project, args.init_preferences, preferences)
            if args.format == "json":
                print(preferences.model_dump_json(indent=2))
            else:
                print(f"Saved preferences: {path}\nEdit reviewed DigiKey SKUs here if needed.\n"
                      "Next: python -B -m tools.parts --project " + args.project
                      + " --preferences " + path.relative_to(root).as_posix())
            return 0
        output = new_receipt(root, args.project, args.output)
        runner = (LocalNetlistRunner(args.cli) if args.runner == "local"
                  else ContainerNetlistRunner() if args.runner == "container"
                  else AutoNetlistRunner(args.cli))
        report = prepare(
            root, args.project, output, runner, args.native_summary, args.preferences,
            args.boards, args.spare_percent, args.spare_minimum,
        )
        save_report(output, report)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(report.model_dump_json(indent=2) if args.format == "json" else text_report(report))
    return 0 if report.status == "READY_FOR_ORDER_REVIEW" else 1


if __name__ == "__main__":
    raise SystemExit(main())
