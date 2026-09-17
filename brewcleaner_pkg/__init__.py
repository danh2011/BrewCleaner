"""
BrewCleaner support package.

Everything that CAN be tested without a display lives here: version
detection, preferences, the package catalogue, snapshot logic, disk
reporting, and the self-update mechanism. The Tk/customtkinter GUI
(brewcleaner.py) imports from this package instead of redefining any
of this logic inline.

Keeping this split matters for two reasons:
  1. it lets these functions be unit tested (see tests/) without a
     display or Homebrew installed, and
  2. it stops the class of bug that shipped in v3.1.3, where the same
     function (`_xcode_install_guidance`) was accidentally defined
     twice in the same file and the first copy silently became dead
     code.
"""

from .version import APP_VERSION, GITHUB_URL

__all__ = ["APP_VERSION", "GITHUB_URL"]
