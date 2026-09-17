"""
Disk space reporting — new in v4.0. Answers "how much would cleanup
actually free?" instead of making people run `brew cleanup` blind.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .brew_env import homebrew_prefix


def _du_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    try:
        for entry in path.rglob("*"):
            try:
                if entry.is_file() and not entry.is_symlink():
                    total += entry.stat().st_size
            except OSError:
                continue
    except OSError:
        pass
    return total


@dataclass
class DiskReport:
    cache_bytes: int
    old_versions_bytes: int
    downloads_bytes: int
    logs_bytes: int

    @property
    def total_bytes(self) -> int:
        return self.cache_bytes + self.old_versions_bytes + self.downloads_bytes + self.logs_bytes


def format_bytes(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TB"


def get_disk_report() -> DiskReport:
    """
    Estimates what `brew cleanup` and friends would free, by measuring
    the actual cache/log directories rather than parsing `brew cleanup
    -n` output (which is slow and its format isn't guaranteed stable
    across Homebrew versions).
    """
    prefix = homebrew_prefix()
    cache_dir = Path.home() / "Library" / "Caches" / "Homebrew"
    logs_dir = Path.home() / "Library" / "Logs" / "Homebrew"
    cellar = Path(prefix) / "Cellar"

    old_versions = 0
    try:
        for pkg_dir in cellar.iterdir() if cellar.exists() else []:
            if not pkg_dir.is_dir():
                continue
            versions = sorted([v for v in pkg_dir.iterdir() if v.is_dir()])
            # every version except the newest counts as "old"
            for v in versions[:-1]:
                old_versions += _du_bytes(v)
    except OSError:
        pass

    downloads = _du_bytes(cache_dir / "downloads") if (cache_dir / "downloads").exists() else 0
    cache_total = _du_bytes(cache_dir)
    cache_only = max(cache_total - downloads, 0)

    return DiskReport(
        cache_bytes=cache_only,
        old_versions_bytes=old_versions,
        downloads_bytes=downloads,
        logs_bytes=_du_bytes(logs_dir),
    )
