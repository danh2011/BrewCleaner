"""
Regression test for the v4.0 GUI mixin split (see ROADMAP.md).

App (in brewcleaner.py) is built from 22 mixins in ui/*.py, all
sharing state via `from ui._shared import *`. That's easy to get
subtly wrong (a name only available in one mixin, a duplicate method
across two of them, a missing import) — this test catches that class
of bug without needing a real display, by stubbing out tkinter/
customtkinter with permissive fakes and then actually importing every
mixin and constructing the real merged class from them, exactly like
brewcleaner.py does.

This does NOT verify the GUI actually looks right or that individual
methods work correctly when called (that still needs a real macOS
box) — it verifies the class can be built at all, which is the thing
most likely to break silently during a refactor like this one.
"""

import glob
import importlib
import sys
import types

import pytest


@pytest.fixture(scope="module", autouse=True)
def fake_gui_stack():
    class FakeWidget:
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, name):
            def method(*a, **k):
                return None
            return method

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

    class FakeCTk(FakeWidget):
        pass

    for name in ("CTk", "CTkToplevel", "CTkFrame", "CTkLabel", "CTkButton",
                 "CTkEntry", "CTkTextbox", "CTkFont", "CTkProgressBar",
                 "CTkScrollableFrame", "CTkCheckBox", "CTkRadioButton",
                 "CTkSwitch", "CTkOptionMenu", "CTkComboBox", "CTkImage",
                 "CTkSegmentedButton", "CTkTabview", "CTkSlider", "CTkCanvas"):
        setattr(fake_ctk, name, FakeCTk)
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

    yield fake_ctk

    for mod_name, orig in saved.items():
        if orig is None:
            sys.modules.pop(mod_name, None)
        else:
            sys.modules[mod_name] = orig
    # Drop any ui.* modules imported under the fakes so a later test
    # session importing the real GUI stack doesn't get stale classes.
    for name in list(sys.modules):
        if name == "ui" or name.startswith("ui."):
            del sys.modules[name]


def _mixin_module_names():
    names = []
    for path in sorted(glob.glob("ui/*.py")):
        stem = path.split("/")[-1][:-3]
        if stem in ("_shared", "__init__", "splash"):
            continue
        names.append(f"ui.{stem}")
    return names


def test_every_mixin_module_imports_cleanly(fake_gui_stack):
    for mod_name in _mixin_module_names():
        importlib.import_module(mod_name)  # raises on any undefined name


def test_merged_app_class_builds(fake_gui_stack):
    classes = []
    for mod_name in _mixin_module_names():
        mod = importlib.import_module(mod_name)
        mixin_names = [n for n in dir(mod) if n.endswith("Mixin")]
        assert mixin_names, f"{mod_name} has no *Mixin class defined"
        classes.append(getattr(mod, mixin_names[0]))

    App = type("App", tuple(classes) + (fake_gui_stack.CTk,), {})
    assert App.__mro__  # C3 linearization succeeded — no MRO conflict
    assert hasattr(App, "_open_command_palette")
    assert hasattr(App, "_steps_done")
    assert hasattr(App, "_goto")


def test_no_duplicate_method_names_across_mixins(fake_gui_stack):
    """
    Regression test for the exact v3.1.3 bug class this whole refactor
    started by fixing: a method silently defined twice (in one class,
    or now across two mixins) with the second/later one winning.
    """
    seen = {}
    dupes = []
    for mod_name in _mixin_module_names():
        mod = importlib.import_module(mod_name)
        mixin_names = [n for n in dir(mod) if n.endswith("Mixin")]
        cls = getattr(mod, mixin_names[0])
        for attr_name, value in vars(cls).items():
            if attr_name.startswith("__"):
                continue
            if callable(value):
                if attr_name in seen and seen[attr_name] != mod_name:
                    dupes.append((attr_name, seen[attr_name], mod_name))
                else:
                    seen[attr_name] = mod_name
    assert not dupes, f"Method(s) defined in more than one mixin: {dupes}"
