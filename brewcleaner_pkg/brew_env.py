"""
The environment used for every `brew` subprocess call, kept in one
place so it can be tested and so Apple Silicon vs Intel prefixes are
handled consistently everywhere (v3.1.3 built this dict inline at
import time in the main script, which also meant it couldn't be
reasoned about or tested independently of importing all of Tk).
"""

from __future__ import annotations

import os
from typing import Dict


def build_brew_env(base_env: Dict[str, str] | None = None) -> Dict[str, str]:
    base_env = dict(base_env if base_env is not None else os.environ)
    # Apple Silicon uses /opt/homebrew, Intel uses /usr/local — put both
    # ahead of PATH so this works regardless of which Mac it's running on.
    prefix_path = "/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin"
    return {
        **base_env,
        "PATH": f"{prefix_path}:{base_env.get('PATH', '')}",
        "HOMEBREW_NO_AUTO_UPDATE": "1",
        "HOMEBREW_NO_ANALYTICS": "1",
        "HOMEBREW_NO_ENV_HINTS": "1",
        "HOMEBREW_INSTALL_CLEANUP": "0",
        "HOMEBREW_MAKE_JOBS": str(min(os.cpu_count() or 4, 8)),
        "HOMEBREW_CURL_RETRIES": "3",
        "HOMEBREW_NO_GITHUB_API": "1",
    }


def homebrew_prefix() -> str:
    """Best-effort guess at the active Homebrew prefix for this Mac."""
    return "/opt/homebrew" if os.path.exists("/opt/homebrew/bin/brew") else "/usr/local"
