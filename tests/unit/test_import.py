import pytest


@pytest.mark.unit
def test_package_importable() -> None:
    import friday

    assert friday is not None
