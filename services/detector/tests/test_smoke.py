from sentinel_detector import __version__


def test_version_is_set() -> None:
    assert __version__
    parts = __version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts), __version__
