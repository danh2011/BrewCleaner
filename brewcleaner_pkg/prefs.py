"""
Preferences storage, with a schema version so a future BrewCleaner
release can migrate old prefs.json files instead of guessing at
missing keys (v3.1.3 had no version field at all).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

PREFS_PATH = Path.home() / ".config" / "brewcleaner" / "prefs.json"
SNAPS_PATH = Path.home() / ".config" / "brewcleaner" / "snapshots"

_SCHEMA_VERSION = 2

_DEFAULTS: Dict[str, Any] = {
    "_schema": _SCHEMA_VERSION,
    "theme": "system",
    "notifications": True,
    "auto_refresh": True,
    "auto_update": True,
    # v4.0 additions:
    "confirm_destructive": True,   # show a preview/dry-run before destructive ops
    "restore_removes_extras": False,  # snapshot restore default behaviour
}


def _migrate(p: Dict[str, Any]) -> Dict[str, Any]:
    version = p.get("_schema", 1)
    if version < 2:
        p.setdefault("auto_update", True)
        p.setdefault("confirm_destructive", True)
        p.setdefault("restore_removes_extras", False)
    p["_schema"] = _SCHEMA_VERSION
    return p


def load_prefs() -> Dict[str, Any]:
    try:
        raw = json.loads(PREFS_PATH.read_text())
    except Exception:
        return dict(_DEFAULTS)
    merged = dict(_DEFAULTS)
    merged.update(raw)
    return _migrate(merged)


def save_prefs(p: Dict[str, Any]) -> None:
    PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    p.setdefault("_schema", _SCHEMA_VERSION)
    PREFS_PATH.write_text(json.dumps(p, indent=2))
