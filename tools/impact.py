"""Explain which project lanes a Git change needs, with conservative fallback."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from .hwrepo.impact import plan_paths
from .hwrepo.models import ImpactPlan
from .hwrepo.selection import ProjectSelector, resolve_project_ids


def changed_paths(root: Path, base: str, head: str) -> tuple[str, ...]:
    """Include both sides of renames so removed owners cannot disappear."""
    result = subprocess.run(
        ("git", "-C", str(root), "diff", "--name-only", "-z", "--no-renames",
         base, head, "--"),
        capture_output=True,
        check=False,
    )
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Cannot determine changed paths: {detail}")
    return tuple(path for path in result.stdout.decode("utf-8").split("\0") if path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base", help="Base commit for a Git diff")
    source.add_argument("--path", action="append", dest="paths",
                        help="Plan one changed repository path directly; may be repeated")
    source.add_argument("--full", action="store_true", help="Request complete acceptance")
    source.add_argument("--select-project", help="Request one project lane")
    source.add_argument("--select-tag", help="Request lanes with one metadata tag")
    source.add_argument("--select-product", help="Request all member lanes of one product")
    parser.add_argument("--exclude-tag", help="Remove tagged lanes from a manual selection")
    parser.add_argument("--head", default="HEAD", help="Head commit (default: HEAD)")
    parser.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args()
    manual_selection = any(
        value is not None for value in (
            args.select_project, args.select_tag, args.select_product,
        )
    )
    if args.exclude_tag and not manual_selection:
        parser.error("--exclude-tag requires a manual project, tag or product selection")
    if manual_selection and not (args.select_project or args.select_tag or args.select_product):
        parser.error("Manual selector value must not be empty")
    root = args.root.resolve()
    try:
        if manual_selection:
            selector_name = (
                "project" if args.select_project is not None
                else "tag" if args.select_tag is not None else "product"
            )
            selector_value = args.select_project or args.select_tag or args.select_product
            selector = ProjectSelector(
                project_ids=(args.select_project,) if args.select_project else (),
                tags=(args.select_tag,) if args.select_tag else (),
                product_ids=(args.select_product,) if args.select_product else (),
                excluded_tags=(args.exclude_tag,) if args.exclude_tag else (),
            )
            selected = resolve_project_ids(root, selector)
            plan = ImpactPlan(
                scope="focused", projects=selected, changed_paths=(),
                reasons=(f"Manual {selector_name} selector: {selector_value}",),
            )
        else:
            paths = (
                changed_paths(root, args.base, args.head) if args.base is not None
                else tuple(args.paths or ())
            )
            plan = plan_paths(root, paths)
            if args.full:
                plan = plan.model_copy(update={"reasons": ("Full run requested",)})
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.format == "json":
        print(plan.model_dump_json())
    else:
        print(f"Impact: {plan.scope.upper()}")
        print("Projects: " + (", ".join(plan.projects) or "none"))
        print("Documentation changed: " + ("yes" if plan.docs_changed else "no"))
        for reason in plan.reasons:
            print(f"Reason: {reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
