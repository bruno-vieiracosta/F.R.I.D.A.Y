import pytest

import friday


@pytest.mark.unit
def test_version_available() -> None:
    assert friday.__version__ == "0.1.0"
