from brewcleaner_pkg.notify import build_command, send


def test_build_command_basic():
    cmd = build_command("BrewCleaner", "Done")
    assert cmd[0] == "osascript"
    assert 'display notification "Done" with title "BrewCleaner"' in cmd[2]


def test_build_command_escapes_quotes():
    cmd = build_command('Title "quoted"', 'msg with "quotes" and \\backslash')
    script = cmd[2]
    assert '\\"quoted\\"' in script
    assert "\\\\backslash" in script


def test_build_command_with_subtitle():
    cmd = build_command("Title", "Message", subtitle="Sub")
    assert 'subtitle "Sub"' in cmd[2]


def test_send_disabled_does_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr("subprocess.run", lambda *a, **k: calls.append(1))
    result = send("T", "M", enabled=False)
    assert result is False
    assert calls == []


def test_send_swallows_errors(monkeypatch):
    def boom(*a, **k):
        raise OSError("no osascript here")
    monkeypatch.setattr("subprocess.run", boom)
    assert send("T", "M", enabled=True) is False
