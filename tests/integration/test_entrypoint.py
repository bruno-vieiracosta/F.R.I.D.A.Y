import subprocess
import sys

import pytest

import friday


@pytest.mark.integration
def test_entrypoint_executes_successfully() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "friday"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert f"F.R.I.D.A.Y. {friday.__version__} bootstrap" in result.stdout
