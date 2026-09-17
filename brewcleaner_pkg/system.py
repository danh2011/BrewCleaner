"""
macOS / Xcode Command Line Tools detection.

NOTE ON v3.1.3: this module used to be two copies of
`_xcode_install_guidance` living in the same file (one at the top of
brewcleaner.py, one ~30 lines later). Python doesn't warn about a
redefined top-level function, so the first copy silently became dead
code and nobody noticed. There is exactly one copy now, and it's
covered by tests/test_system.py so a future edit can't reintroduce
the duplicate without a test failing.
"""

from __future__ import annotations

import subprocess
from typing import Tuple, Dict

_MACOS_NAMES: Dict[int, str] = {
    26: "Tahoe", 15: "Sequoia", 14: "Sonoma", 13: "Ventura",
    12: "Monterey", 11: "Big Sur", 10: "Catalina",
}

# Apple's Xcode <-> macOS compatibility matrix (approximate minimums).
_XCODE_MIN_MACOS: Tuple[Tuple[int, int, str], ...] = (
    (26, 0, "26"),
    (15, 0, "16.2"),
    (14, 5, "16"),
    (13, 5, "15"),
    (12, 5, "14"),
    (11, 3, "13"),
    (10, 15, "12"),
)


def sys_is_dark() -> bool:
    try:
        r = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True, text=True, timeout=1)
        return r.stdout.strip() == "Dark"
    except Exception:
        return False


def get_macos_version() -> Tuple[int, int]:
    """Returns (major, minor), e.g. (14, 5). (0, 0) if it can't be read."""
    try:
        r = subprocess.run(["sw_vers", "-productVersion"],
                            capture_output=True, text=True, timeout=3)
        parts = r.stdout.strip().split(".")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
    except Exception:
        return (0, 0)


def get_recommended_xcode(mac_major: int, mac_minor: int) -> Tuple[str, str]:
    """
    Returns (xcode_version_str, download_url) for the newest Xcode
    that's compatible with the given macOS version.
    """
    dl_all = "https://developer.apple.com/download/all/?q=xcode"
    dl_latest = "https://developer.apple.com/xcode/"
    for min_major, min_minor, xcode_ver in _XCODE_MIN_MACOS:
        if (mac_major, mac_minor) >= (min_major, min_minor):
            url = dl_latest if (mac_major, mac_minor) >= _XCODE_MIN_MACOS[0][:2] else f"{dl_all}+{xcode_ver}"
            return xcode_ver, url
    return "12", f"{dl_all}+12"


def clt_installed() -> bool:
    """True if the Xcode Command Line Tools are installed."""
    try:
        r = subprocess.run(["xcode-select", "-p"], capture_output=True, timeout=4)
        return r.returncode == 0
    except Exception:
        return False


def xcode_app_installed() -> bool:
    import os
    return os.path.exists("/Applications/Xcode.app")


def xcode_install_guidance() -> dict:
    """
    Guidance for installing/upgrading Xcode CLT, tailored to the
    current macOS version.
    Keys: xcode_name, xcode_ver, macos_name, major, minor,
          method ("terminal"|"download"), note, dl_url
    """
    mac_major, mac_minor = get_macos_version()
    xcode_ver, dl_url = get_recommended_xcode(mac_major, mac_minor)
    mac_str = f"{mac_major}.{mac_minor}" if mac_major else "unknown"
    macos_name = _MACOS_NAMES.get(mac_major, f"macOS {mac_major}" if mac_major else "unknown macOS")

    if mac_major >= 13:
        method = "terminal"
        note = "Run in Terminal:  xcode-select --install"
    else:
        method = "download"
        note = (f"Your Mac (macOS {mac_str}) needs {xcode_ver}.\n"
                "Download from: developer.apple.com/download/all/\n"
                "(free Apple ID required — search 'Command Line Tools')")

    return {
        # NOTE: kept as the bare version string ("16", not "Xcode 16
        # Command Line Tools") on purpose — several call sites build
        # their own sentence around this value, e.g. f"Xcode {xcode_name}".
        "xcode_name": xcode_ver,
        "xcode_ver": xcode_ver,
        "macos_name": macos_name,
        "major": mac_major,
        "minor": mac_minor,
        "method": method,
        "note": note,
        "dl_url": dl_url,
    }
