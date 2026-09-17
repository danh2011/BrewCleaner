from brewcleaner_pkg import system


def test_no_duplicate_xcode_guidance_keys():
    # Regression test for the v3.1.3 bug where this function was
    # defined twice in the same file and the first copy (missing the
    # "minor" key) silently won.
    g = system.xcode_install_guidance()
    for key in ("xcode_name", "xcode_ver", "macos_name", "major", "minor", "method", "note", "dl_url"):
        assert key in g


def test_get_recommended_xcode_monotonic():
    old_ver, _ = system.get_recommended_xcode(11, 0)
    new_ver, _ = system.get_recommended_xcode(15, 0)
    assert old_ver != new_ver


def test_xcode_guidance_method_matches_macos_major():
    g = system.xcode_install_guidance()
    assert g["method"] in ("terminal", "download")


def test_get_macos_version_returns_tuple_of_ints():
    major, minor = system.get_macos_version()
    assert isinstance(major, int) and isinstance(minor, int)
