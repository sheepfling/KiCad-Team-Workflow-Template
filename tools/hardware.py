"""Cross-platform typed product policy and deterministic review artifacts."""
from __future__ import annotations

import argparse
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from .hwrepo.cli_output import issue_text
from .hwrepo.generation import check_generation, generate, snapshot, verify_snapshot
from .hwrepo.product import check


def _mapping(value: object) -> dict[str, object]:
    return cast(dict[str, object], value) if isinstance(value, dict) else {}


def _items(value: object) -> tuple[object, ...]:
    return tuple(cast(Sequence[object], value)) if isinstance(value, (list, tuple)) else ()


def format_text(command: str, result: dict[str, object], output: Path | None) -> str:
    """Keep product findings and review-only snapshot scope visible in a short view."""
    title = {
        "check": "Hardware policy",
        "generate": "Hardware generation",
        "snapshot": "Hardware snapshot",
        "verify-snapshot": "Hardware snapshot verification",
    }[command]
    status = str(result.get("status", "FAIL"))
    lines = [f"{title}: {status}"]
    if output is not None:
        lines.append(f"Output: {output}")
    products = _items(result.get("products"))
    if products:
        lines.append(f"Products: {', '.join(str(item) for item in products)}")
    open_items = _mapping(result.get("open_items"))
    review = tuple(
        f"{product}: {item}"
        for product, values in open_items.items()
        for item in _items(values)
    )
    if review:
        lines.append(f"Open review items: {len(review)}")
        lines.extend(f"  - {item}" for item in review[:3])
    issues = _items(result.get("issues"))
    drift = _items(result.get("generation_drift"))
    if issues or drift:
        lines.append(f"Policy issues: {len(issues)}; generation drift: {len(drift)}")
        findings = tuple(issue_text(item) for item in issues) + tuple(str(item) for item in drift)
        lines.extend(f"  - {item}" for item in findings[:5])
        if len(issues) + len(drift) > 5:
            lines.append("  More findings are available with --format json.")
    generated = _items(result.get("generated"))
    if command == "generate" and status == "PASS":
        lines.append(f"Generated: {len(generated)} file(s)")
        lines.extend(f"  {item}" for item in generated[:5])
        if len(generated) > 5:
            lines.append("  Full inventory: rerun with --format json.")
    manifest = _mapping(result.get("manifest"))
    if manifest:
        lines.append(f"Commit: {manifest.get('commit', '?')}")
        lines.append(f"Working tree clean: {manifest.get('working_tree_clean', '?')}")
        lines.append(f"Artifacts: {len(_mapping(manifest.get('artifacts_sha256')))}")
        checks = _mapping(manifest.get("checks"))
        for name, check_status in checks.items():
            lines.append(f"  {name}: {check_status}")
    if result.get("artifacts") is not None:
        lines.append(f"Verified artifacts: {result['artifacts']}")
    if result.get("scope"):
        lines.append(f"Scope: {str(result['scope']).replace('_', ' ')}")
    if result.get("error"):
        lines.append(f"Error: {result['error']}")
    if result.get("build_authorized") is False or manifest.get("build_authorized") is False:
        lines.append("Build authorized: no")
    if status != "PASS":
        if drift:
            lines.append("Next: Regenerate review views, inspect the drift, and rerun the check.")
        elif issues:
            lines.append("Next: Repair the named policy issues and rerun the check.")
        else:
            lines.append("Next: Repair the named input or tool error and rerun the command.")
        lines.append("Full structured result: rerun with --format json.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "generate", "snapshot", "verify-snapshot"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--release", action="store_true", help="Fail closed: build/release authorization is not implemented")
    parser.add_argument("--output", type=Path, help="New directory for a review snapshot")
    parser.add_argument("--format", choices=("json", "text"), default="json",
                        help="Output format (default: json)")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.release and args.command != "check":
            parser.error("--release is only valid with check")
        if args.command == "check":
            policy = check(root, args.release)
            result: dict[str, object] = policy.model_dump(mode="json")
            if policy.status == "PASS":
                generation_drift = check_generation(root)
                result["generation_drift"] = generation_drift
                if generation_drift:
                    result["status"] = "FAIL"
        elif args.command == "generate":
            result = {
                "status": "PASS",
                "generated": generate(root),
                "build_authorized": False,
            }
        elif args.command == "snapshot":
            if args.output is None:
                parser.error("snapshot requires --output")
            result = {
                "status": "PASS",
                "manifest": snapshot(root, args.output).model_dump(mode="json"),
            }
        else:
            if args.output is None:
                parser.error("verify-snapshot requires --output")
            result = verify_snapshot(args.output.resolve()).model_dump(mode="json")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        result = {"status": "FAIL", "error": str(exc), "build_authorized": False}
    import json  # CLI serialization boundary; the service layer returns models.

    print(json.dumps(result, indent=2) if args.format == "json" else
          format_text(args.command, result, args.output))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
