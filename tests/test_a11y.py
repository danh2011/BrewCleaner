"""
Accessibility pass, part 1: color contrast.

Runs the WCAG audit (brewcleaner_pkg/a11y.py) against the app's real
_LIGHT and _DARK theme dicts in ui/_shared.py, so a future color
tweak that breaks contrast fails CI instead of just shipping. Fixed
two real failures during v4.0 (see git history / ROADMAP.md): the
light theme's "ok" and "warn" indicator colors were both under the
3:1 minimum against a white panel.
"""

import sys
import types

import pytest

from brewcleaner_pkg.a11y import audit_theme_contrast


@pytest.fixture(scope="module")
def real_theme_dicts():
    # ui/_shared.py imports customtkinter/tkinter at module level, so
    # stub them the same way tests/test_ui_wiring.py does — we only
    # need the plain-data _LIGHT/_DARK dicts, not a working GUI.
    class FakeWidget:
        def __init__(self, *a, **k):
            pass
        def __getattr__(self, name):
            return lambda *a, **k: None
        def __call__(self, *a, **k):
            return FakeWidget()

    fake_tk = types.ModuleType("tkinter")
    for name in ("Tk", "Toplevel", "Frame", "Label", "Button", "Entry", "Text",
                 "Canvas", "StringVar", "BooleanVar", "IntVar", "PhotoImage",
                 "Event", "TclError", "Menu", "Scrollbar", "Listbox"):
        setattr(fake_tk, name, FakeWidget)
    fake_tk.messagebox = types.ModuleType("tkinter.messagebox")
    fake_tk.filedialog = types.ModuleType("tkinter.filedialog")

    fake_ctk = types.ModuleType("customtkinter")
    for name in ("CTk", "CTkToplevel", "CTkFrame", "CTkLabel", "CTkButton",
                 "CTkEntry", "CTkTextbox", "CTkFont", "CTkProgressBar",
                 "CTkScrollableFrame"):
        setattr(fake_ctk, name, FakeWidget)
    fake_ctk.set_appearance_mode = lambda *a, **k: None
    fake_ctk.get_appearance_mode = lambda *a, **k: "Light"
    fake_ctk.set_default_color_theme = lambda *a, **k: None

    saved = {}
    for mod_name, mod in (("tkinter", fake_tk),
                           ("tkinter.messagebox", fake_tk.messagebox),
                           ("tkinter.filedialog", fake_tk.filedialog),
                           ("customtkinter", fake_ctk)):
        saved[mod_name] = sys.modules.get(mod_name)
        sys.modules[mod_name] = mod
    sys.modules.pop("ui._shared", None)

    import ui._shared as shared
    yield shared._LIGHT, shared._DARK

    for mod_name, orig in saved.items():
        if orig is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = orig
    sys.modules.pop("ui._shared", None)


def test_light_theme_meets_wcag_aa(real_theme_dicts):
    light, _dark = real_theme_dicts
    failures = audit_theme_contrast(light)
    assert not failures, "Light theme contrast failures:\n" + "\n".join(failures)


def test_dark_theme_meets_wcag_aa(real_theme_dicts):
    _light, dark = real_theme_dicts
    failures = audit_theme_contrast(dark)
    assert not failures, "Dark theme contrast failures:\n" + "\n".join(failures)
