"""Choose reviewed parts, populate matching footprints and prepare an order list."""
from __future__ import annotations

import argparse
from pathlib import Path

from .hwrepo.contract_coach import (
    AutoNetlistRunner,
    ContainerNetlistRunner,
    LocalNetlistRunner,
)
from .hwrepo.part_picker import create_picker, resume_selection, selection
from .hwrepo.part_picker_view import (
    picker_text,
    save_picker,
    save_selection,
    selection_text,
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
        "Start: python -B -m tools.parts --project YOUR_PROJECT --picker. "
        "Choose reviewed parts, preview and apply, then rerun without --picker for an order list."
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
    mode.add_argument("--picker", action="store_true",
                      help="Open the guided catalog choices workflow in a local review page")
    mode.add_argument("--selection", type=Path,
                      help="Preview a downloaded selection, or apply the resulting locked map")
    mode.add_argument("--sync-models", action="store_true",
                      help="Preview model assignments from saved parts after KiCad's F8 update")
    parser.add_argument("--apply", action="store_true",
                        help="Apply exactly a previously previewed, locked --selection map")
    parser.add_argument("--native-summary", type=Path,
                        help="Reuse source-bound capture for the picker or order review")
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
    mutation = args.selection is not None or args.sync_models
    if args.apply and args.selection is None:
        parser.error("--apply requires a previously previewed --selection map")
    if args.native_summary is not None and (mutation or args.init_preferences is not None):
        parser.error("--native-summary applies only to the picker or order review")
    if mutation and (args.runner != "auto" or args.cli != "kicad-cli"):
        parser.error("--runner and --cli apply only to fresh capture")
    if (args.picker or mutation) and any(value is not None for value in (
        args.preferences, args.boards, args.spare_percent, args.spare_minimum,
    )):
        parser.error("Set quantities with the order review; the picker preserves saved build preferences")
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
        if args.picker:
            picker = create_picker(root, args.project, output, runner, args.native_summary)
            save_picker(output, picker)
            print(picker.model_dump_json(indent=2) if args.format == "json" else picker_text(picker))
            return 0 if picker.status == "READY" else 1
        if mutation:
            result = (selection(root, args.project, args.selection, output, apply=args.apply)
                      if args.selection is not None
                      else resume_selection(root, args.project, output))
            save_selection(output, result)
            print(result.model_dump_json(indent=2) if args.format == "json" else selection_text(result))
            return 1 if result.status == "BLOCKED" else 0
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
