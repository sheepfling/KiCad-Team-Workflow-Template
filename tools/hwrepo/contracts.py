"""I/O boundary helpers.

Raw JSON is decoded here only. Callers must immediately validate it into a
Pydantic model from hwrepo.models; dictionaries do not cross this boundary.
"""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TypeVar

from pydantic import BaseModel, ValidationError

Model = TypeVar("Model", bound=BaseModel)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_number(value: str) -> None:
    raise ValueError(f"Invalid JSON number: {value}")


def read_model(path: Path, model: type[Model]) -> Model:
    """Decode one JSON file and validate it before it reaches application code."""
    document = path.read_text(encoding="utf-8")
    # This first decode exists solely to fail duplicate keys/non-finite numbers.
    # Pydantic's JSON decoder then preserves JSON's valid array/enum semantics
    # while applying strict scalar validation and producing immutable tuples.
    try:
        json.loads(
            document,
            object_pairs_hook=_unique_object,
            parse_constant=_invalid_number,
        )
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    try:
        return model.model_validate_json(document, strict=True)
    except ValidationError as exc:
        raise ValueError(f"{path}: {exc}") from exc


def write_model(path: Path, model: BaseModel) -> None:
    """Serialize a validated model with deterministic UTF-8 JSON formatting."""
    path.write_text(
        model.model_dump_json(by_alias=True, indent=2, exclude_none=True) + "\n",
        encoding="utf-8",
    )


def repo_path(root: Path, value: str) -> Path:
    """Require a portable, exact-case path that stays inside root."""
    if not value or "\\" in value or ":" in value:
        raise ValueError(f"Nonportable repository path: {value!r}")
    posix = PurePosixPath(value)
    if (
        posix.is_absolute()
        or PureWindowsPath(value).drive
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ValueError(f"Unsafe repository path: {value!r}")
    root = root.resolve()
    current = root
    reserved = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }
    for component in posix.parts:
        if (
            component.endswith((".", " "))
            or component.split(".")[0].upper() in reserved
            or any(character in '<>"|?*' or ord(character) < 32 for character in component)
        ):
            raise ValueError(f"Nonportable repository path: {value!r}")
        if current.is_dir():
            names = {entry.name for entry in current.iterdir()}
            if component not in names and component.casefold() in {
                name.casefold() for name in names
            }:
                raise ValueError(f"Path case mismatch: {value!r}")
        current = current / component
        if current.is_symlink() or (
            current.exists() and current.resolve() != current.absolute()
        ):
            raise ValueError(f"Linked repository path: {value!r}")
    if root not in current.resolve().parents:
        raise ValueError(f"Escaping repository path: {value!r}")
    return current
