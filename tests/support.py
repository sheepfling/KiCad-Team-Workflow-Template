"""Isolated reference repositories, independent of an adopter's live records."""
from __future__ import annotations

import atexit
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from tools.hwrepo.repository import ephemeral, generated_artifact

SOURCE_ROOT = Path(__file__).resolve().parents[1]


def ignore_local(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name == ".git" or ephemeral(name)
            or (Path(directory, name).is_file()
                and generated_artifact(Path(directory, name).relative_to(SOURCE_ROOT).as_posix()))}


def initialize_git(root: Path) -> None:
    # Disposable repositories are deleted immediately after each test. Keep Git
    # from starting background maintenance that can recreate .git/objects during
    # TemporaryDirectory cleanup on macOS.
    for args in (("init", "-q"), ("config", "gc.auto", "0"),
                 ("config", "maintenance.auto", "false"), ("add", "--all")):
        subprocess.run(("git", "-C", str(root), *args), check=True, capture_output=True)


@lru_cache(maxsize=1)
def reference_root() -> Path:
    """Keep example contracts stable while live catalog projects grow or change."""
    temporary = tempfile.TemporaryDirectory(prefix="kicad-test-reference-")
    atexit.register(temporary.cleanup)
    destination = Path(temporary.name).resolve() / "repository"
    destination.mkdir()
    for directory in ("tools", "tests", "docs", "templates", "examples", ".github"):
        shutil.copytree(SOURCE_ROOT / directory, destination / directory, ignore=ignore_local)
    for name in (
        "README.md", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md",
        ".gitignore", ".gitattributes", "pyproject.toml",
    ):
        shutil.copy2(SOURCE_ROOT / name, destination / name)
    # Adopters may have their own root license or none yet; shared-tool tests
    # always exercise the original template notice in a disposable checkout.
    shutil.copy2(SOURCE_ROOT / "tests/fixtures/scaffold-license.txt", destination / "LICENSE")
    for directory in ("catalog", "projects", "products", "libraries",
                      "generated", "schemas"):
        (destination / directory).mkdir()
        readme = SOURCE_ROOT / directory / "README.md"
        if readme.exists():
            shutil.copy2(readme, destination / directory / "README.md")
    shutil.copytree(SOURCE_ROOT / "examples/catalog", destination / "catalog", dirs_exist_ok=True)
    shutil.copy2(
        SOURCE_ROOT / "catalog/documentation-policy.json",
        destination / "catalog/documentation-policy.json",
    )
    initialize_git(destination)
    return destination
