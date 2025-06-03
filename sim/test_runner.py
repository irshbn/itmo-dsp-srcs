from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner
from utils import get_dependencies, run

workdir = Path().resolve() / "work"


@pytest.fixture
def setup_runner():

    sources = list(workdir.glob("*.vhdl"))
    runner = get_runner("nvc")

    return runner, sources


class TestCIC:

    top = "cic_decimator"
    pkgs, modules = get_dependencies(top, workdir)

    def test_cic(self, setup_runner):
        run(setup_runner, self.top, self.pkgs, self.modules)
