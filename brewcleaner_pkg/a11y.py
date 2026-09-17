"""
WCAG contrast ratio checking — accessibility pass, new in v4.0.

A real, testable slice of "accessibility pass": most of what makes a
Tk/customtkinter app accessible (native VoiceOver labels, robust tab
order) is limited by what Tk itself exposes on macOS, which isn't
something a code change here can fix. Color contrast is different —
it's fully under the app's control and mechanically checkable, so
that's what this module does: compute WCAG 2.1 contrast ratios for
this app's actual theme colors and flag any text/background pair
that falls below the AA minimum (4.5:1 for normal text, 3:1 for large
text / UI components).

See tests/test_a11y.py, which runs this against the real _LIGHT and
_DARK dicts in ui/_shared.py — so a future color change that breaks
contrast fails CI instead of shipping.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _relative_luminance(hex_color: str) -> float:
    r, g, b = (c / 255.0 for c in _hex_to_rgb(hex_color))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """WCAG 2.1 contrast ratio between two colors, always >= 1.0."""
    l1 = _relative_luminance(fg_hex)
    l2 = _relative_luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)

# (foreground key, background key, minimum ratio, description)
# — the text/background pairs that actually appear together in the UI.
# 3.0 is used for keys that are large text or UI-component-level
# (icons, borders) per WCAG's own distinction; 4.5 for regular body text.
_PAIRS: Tuple[Tuple[str, str, float, str], ...] = (
    ("text", "bg", 4.5, "primary text on app background"),
    ("text", "panel", 4.5, "primary text on panel background"),
    ("text", "sidebar", 4.5, "primary text on sidebar background"),
    ("text2", "panel", 4.5, "secondary text on panel background"),
    ("text2", "bg", 4.5, "secondary text on app background"),
    ("accent", "bg", 3.0, "accent-colored UI elements on app background"),
    ("accent", "panel", 3.0, "accent-colored UI elements on panel background"),
    ("ok", "panel", 3.0, "success indicator on panel background"),
    ("warn", "panel", 3.0, "warning indicator on panel background"),
    ("err", "panel", 3.0, "error indicator on panel background"),
    ("tfg", "tbg", 4.5, "terminal text on terminal background"),
)


def audit_theme_contrast(theme: Dict[str, str]) -> List[str]:
    """
    Returns a list of human-readable failure descriptions (empty if
    every checked pair passes). Skips a pair if either key is missing
    from the given theme dict rather than raising, since not every
    theme necessarily defines every optional key.
    """
    failures = []
    for fg_key, bg_key, minimum, desc in _PAIRS:
        if fg_key not in theme or bg_key not in theme:
            continue
        ratio = contrast_ratio(theme[fg_key], theme[bg_key])
        if ratio < minimum:
            failures.append(
                f"{desc} ({fg_key}={theme[fg_key]} on {bg_key}={theme[bg_key]}): "
                f"{ratio:.2f}:1, needs {minimum}:1")
    return failures
