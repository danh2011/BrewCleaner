from brewcleaner_pkg.disk import format_bytes


def test_format_bytes_units():
    assert format_bytes(500) == "500 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MB"
    assert format_bytes(3 * 1024 * 1024 * 1024) == "3.0 GB"
