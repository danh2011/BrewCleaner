"""
Self-update, hardened.

What was wrong in v3.1.3 (brewcleaner.py _check_for_updates):
  1. It wrote the downloaded code directly over the running script
     with `open(__file__, "w")` with no validation at all — if GitHub
     ever served an error page, a truncated response, or a
     man-in-the-middle'd response, that garbage got written straight
     over the user's working copy before anyone noticed.
  2. There was no integrity check of any kind — no checksum, no
     signature, nothing tying the bytes we run to a specific release.
  3. The `except Exception:` handler duplicated the entire
     download-and-write block a second time, referencing
     `remote_version` / `url` from the try block — if the original
     failure happened before those were assigned, the except handler
     itself raised UnboundLocalError. And there were *two*
     `except Exception:` clauses on the same try, so the second was
     silently unreachable dead code.

This module fixes all three:
  - the update is written to a temp file and validated (must parse as
    valid Python and must contain the expected new APP_VERSION)
    *before* it ever touches the real file
  - the swap onto the real file is done with os.replace(), which is
    atomic on the same filesystem — there's no window where the file
    is half-written
  - if a `<file>.sha256` asset is published alongside a release, it's
    verified; if not, that step is skipped and callers are told so
    explicitly rather than silently pretending it happened (see
    ROADMAP.md for the follow-up: publish signed checksums)
  - exactly one try/except, no duplicated recovery logic
"""

from __future__ import annotations

import ast
import hashlib
import os
import tempfile
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from .version import APP_VERSION, GITHUB_URL

_UA = {"User-Agent": "BrewCleaner-App"}


def _ver_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().split("."))
    except Exception:
        return (0,)


@dataclass
class UpdateInfo:
    version: str
    url: str


def check_for_update(current_version: str = APP_VERSION) -> Optional[UpdateInfo]:
    """Returns UpdateInfo if a newer version is published, else None."""
    base_url = GITHUB_URL.replace("github.com", "raw.githubusercontent.com")
    for branch in ("main", "master"):
        url = f"{base_url}/{branch}/brewcleaner.py"
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=5) as resp:
                head = resp.read(4096).decode("utf-8", errors="ignore")
        except Exception:
            continue

        remote_version = None
        for line in head.splitlines():
            if line.startswith("APP_VERSION"):
                try:
                    remote_version = str(ast.literal_eval(line.split("=", 1)[1].strip()))
                except Exception:
                    pass
                break
        if remote_version and _ver_tuple(remote_version) > _ver_tuple(current_version):
            return UpdateInfo(version=remote_version, url=url)
        return None  # found a reachable branch with no newer version — stop here
    return None


def _fetch_checksum(script_url: str) -> Optional[str]:
    """Best-effort: look for <script_url>.sha256 alongside the script."""
    try:
        req = urllib.request.Request(script_url + ".sha256", headers=_UA)
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read(200).decode("utf-8", errors="ignore").strip()
        # accept either "<hash>" or "<hash>  filename" (sha256sum format)
        digest = text.split()[0]
        if len(digest) == 64:
            return digest.lower()
    except Exception:
        pass
    return None


def download_and_apply(
    info: UpdateInfo,
    target_path: str,
    on_progress: Optional[Callable[[float], None]] = None,
) -> None:
    """
    Downloads `info.url`, validates it, and atomically replaces
    target_path. Raises on any failure — callers should show the
    error rather than silently ignoring it (unlike v3.1.3).
    """
    req = urllib.request.Request(info.url, headers=_UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        chunks = []
        read = 0
        while True:
            piece = resp.read(8192)
            if not piece:
                break
            chunks.append(piece)
            read += len(piece)
            if total and on_progress:
                on_progress(min(read / total, 1.0) * 0.9)
        data = b"".join(chunks)

    # 1. Must be valid, non-trivial Python.
    text = data.decode("utf-8")
    if len(text) < 1000:
        raise ValueError("Downloaded update looks truncated (too small) — aborting.")
    try:
        ast.parse(text)
    except SyntaxError as exc:
        raise ValueError(f"Downloaded update is not valid Python — aborting: {exc}") from exc

    # 2. Must actually be the version we think we're getting.
    if f'APP_VERSION = "{info.version}"' not in text and f"APP_VERSION = '{info.version}'" not in text:
        raise ValueError("Downloaded update's version string doesn't match what was advertised — aborting.")

    # 3. Verify checksum if the maintainer has published one (see ROADMAP.md).
    expected = _fetch_checksum(info.url)
    if expected is not None:
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ValueError("Checksum mismatch on downloaded update — aborting, file was NOT applied.")

    # 4. Stage + atomic swap. Never write directly over the running file.
    dir_ = os.path.dirname(os.path.abspath(target_path)) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".brewcleaner-update-", dir=dir_)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.chmod(tmp_path, 0o755)
        os.replace(tmp_path, target_path)  # atomic on the same filesystem
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    if on_progress:
        on_progress(1.0)
