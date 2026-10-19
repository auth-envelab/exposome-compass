"""Deterministic local files, bounded output directories and input validation."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .errors import CompassError


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False,
                               allow_nan=False) + '\n', encoding='utf-8')


def load_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError, OSError) as exc:
        raise CompassError(f'Invalid JSON file: {path}') from exc
    if not isinstance(obj, dict):
        raise CompassError(f'Expected a JSON object: {path}')
    return obj


def finite_number(raw: str | int | float | None, *, name: str, allow_blank: bool = False) -> float | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if allow_blank:
            return None
        raise CompassError(f'Missing numerical value for {name}')
    try:
        value = float(raw)
    except (ValueError, TypeError) as exc:
        raise CompassError(f'Invalid numerical value for {name}: {raw!r}') from exc
    if not math.isfinite(value):
        raise CompassError(f'Non-finite numerical value for {name}: {raw!r}')
    return value


def regular_path(path: Path, *, must_exist: bool = False) -> Path:
    path = Path(path).absolute()
    for part in [path, *path.parents]:
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise CompassError(f'Links/junctions are not supported for protected file operations: {part}')
    if must_exist and not path.is_file():
        raise CompassError(f'Required file does not exist: {path}')
    return path


def create_stage(destination: Path) -> Path:
    destination = regular_path(destination)
    if destination.exists():
        raise CompassError(f'Existing result directory is immutable: {destination}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f'.{destination.name}-building-', dir=destination.parent))


def publish_stage(stage: Path, destination: Path) -> None:
    destination = regular_path(destination)
    if destination.exists():
        raise CompassError(f'Destination already exists: {destination}')
    stage.rename(destination)


def discard_stage(stage: Path) -> None:
    if stage.is_dir() and not stage.is_symlink():
        shutil.rmtree(stage)


def verify_reference(directory: str | Path) -> dict:
    """Validate output CSV hashes, without treating them as provider authenticity."""
    root = regular_path(Path(directory))
    manifest = load_json(root / 'reference_manifest.json')
    if manifest.get('format') != 'exposome-compass-environmental-v1':
        raise CompassError('Unknown environmental reference format')
    files = manifest.get('files_sha256', {})
    if not isinstance(files, dict) or not files or any('/' in k or '\\' in k for k in files):
        raise CompassError('Malformed reference file manifest')
    for name, expected in files.items():
        path = regular_path(root / name, must_exist=True)
        if sha256(path) != expected:
            raise CompassError(f'Reference file changed or corrupted: {path}')
    return manifest


def validate_key(country: str, postcode: str) -> tuple[str, str]:
    country = str(country).strip().upper()
    postcode = str(postcode).strip()
    if len(country) != 2 or not country.isalpha():
        raise CompassError('Country must be a two-letter ISO country code')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 _-]{0,23}', postcode):
        raise CompassError('Postcode must contain safe letters, digits, spaces, underscore or hyphen')
    return country, postcode
