from brewcleaner_pkg.menubar_core import (
    format_menu_title, format_status_line, build_open_gui_command,
    build_quick_clean_command, get_outdated_count,
)


def test_format_menu_title_variants():
    assert format_menu_title(None) == "🍺 ?"
    assert format_menu_title(0) == "🍺"
    assert format_menu_title(5) == "🍺 5"


def test_format_status_line_variants():
    assert format_status_line(None) == "Couldn't check for updates"
    assert format_status_line(0) == "Everything up to date"
    assert format_status_line(1) == "1 package outdated"
    assert format_status_line(4) == "4 packages outdated"


def test_build_open_gui_command_excludes_menubar_flag():
    cmd = build_open_gui_command("/opt/brewcleaner/brewcleaner.py", python_exe="/usr/bin/python3")
    assert cmd == ["/usr/bin/python3", "/opt/brewcleaner/brewcleaner.py"]
    assert "--menubar" not in cmd


def test_build_quick_clean_command_is_safe_cleanup_only():
    cmd = build_quick_clean_command()
    assert cmd.startswith("brew cleanup")
    assert "uninstall" not in cmd
    assert "--force" not in cmd  # menu bar quick action should never be a --force op


def test_get_outdated_count_returns_none_on_total_failure(monkeypatch):
    def boom(*a, **k):
        raise OSError("brew not found")
    monkeypatch.setattr("subprocess.run", boom)
    assert get_outdated_count({}) is None


def test_get_outdated_count_sums_formula_and_cask(monkeypatch):
    class FakeResult:
        def __init__(self, out, rc=0):
            self.stdout = out
            self.returncode = rc

    calls = {"n": 0}

    def fake_run(cmd, **kwargs):
        calls["n"] += 1
        if "--cask" in cmd:
            return FakeResult("firefox\n")
        return FakeResult("git\nnode\n")

    monkeypatch.setattr("subprocess.run", fake_run)
    assert get_outdated_count({}) == 3
