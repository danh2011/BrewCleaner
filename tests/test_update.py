import pytest

from brewcleaner_pkg import update


@pytest.mark.parametrize("a,b,expected", [
    ("3.1.3", "3.1.2", False),
    ("3.1.2", "3.1.3", True),
    ("4.0.0", "3.1.3", False),
    ("3.1.3", "4.0.0", True),
    ("3.1.10", "3.1.9", False),  # numeric, not lexicographic
])
def test_ver_tuple_ordering(a, b, expected):
    assert (update._ver_tuple(a) < update._ver_tuple(b)) == expected


def test_ver_tuple_handles_garbage():
    assert update._ver_tuple("not-a-version") == (0,)


def test_download_and_apply_rejects_truncated_data(monkeypatch, tmp_path):
    class FakeResp:
        headers = {"Content-Length": "10"}
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1):
            if not hasattr(self, "_done"):
                self._done = True
                return b"short"
            return b""

    monkeypatch.setattr(update.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    target = tmp_path / "brewcleaner.py"
    target.write_text("# original")
    with pytest.raises(ValueError, match="truncated"):
        update.download_and_apply(update.UpdateInfo(version="9.9.9", url="https://example.invalid/x.py"),
                                    str(target))
    # original file must be untouched
    assert target.read_text() == "# original"


def test_download_and_apply_rejects_version_mismatch(monkeypatch, tmp_path):
    fake_code = "APP_VERSION = \"1.2.3\"\n" + ("x = 1\n" * 500)

    class FakeResp:
        headers = {"Content-Length": str(len(fake_code))}
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self, n=-1):
            if not hasattr(self, "_done"):
                self._done = True
                return fake_code.encode()
            return b""

    monkeypatch.setattr(update.urllib.request, "urlopen", lambda *a, **k: FakeResp())
    monkeypatch.setattr(update, "_fetch_checksum", lambda url: None)
    target = tmp_path / "brewcleaner.py"
    target.write_text("# original")
    with pytest.raises(ValueError, match="version string"):
        update.download_and_apply(update.UpdateInfo(version="9.9.9", url="https://example.invalid/x.py"),
                                    str(target))
    assert target.read_text() == "# original"
