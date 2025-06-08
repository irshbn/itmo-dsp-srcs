r"""
--------------------------------------------------------------------------------
--       ___  _________  _____ ______   ________     
--      |\  \|\___   ___\\   _ \  _   \|\   __  \    
--      \ \  \|___ \  \_\ \  \\\__\ \  \ \  \|\  \   
--       \ \  \   \ \  \ \ \  \\|__| \  \ \  \\\  \  
--        \ \  \   \ \  \ \ \  \    \ \  \ \  \\\  \ 
--         \ \__\   \ \__\ \ \__\    \ \__\ \_______\
--          \|__|    \|__|  \|__|     \|__|\|_______|
--      
--------------------------------------------------------------------------------
--! @copyright CERN-OHL-W-2.0
--
-- You may use, distribute and modify this code under the terms of the
-- CERN OHL v2 Weakly Reciprocal license. 
--
-- You should have received a copy of the CERN OHL v2 Weakly Reciprocal license
-- with this file. If not, please visit: https://cern-ohl.web.cern.ch/home
--------------------------------------------------------------------------------
--! @date June 8, 2025
--! @author Yaroslav Shubin <irshubin@itmo.ru>
--------------------------------------------------------------------------------
--! @brief Test runner module providing multi-generic testing 
--------------------------------------------------------------------------------
"""

from itertools import product
from math import ceil, log2
from pathlib import Path
from typing import List, Tuple

import allure
import pytest
from cocotb_tools.runner import get_runner

projdir = Path(__file__).resolve().parent.parent
workdir = projdir / "work"
simdir = projdir / "sim"
builddir = projdir / "sim_build"
work = list((projdir / "work").glob("*.vhdl"))

runner = get_runner("nvc")
runner._preserve_case = []

cic_generic_ranges = {
    "cic_order": range(1, 8),
    "comb_taps": range(1, 3),
    "dec_ratio": range(2, 66, 3),
}
cic_generic_combos = list(product(*[cic_generic_ranges[k] for k in cic_generic_ranges]))


@pytest.fixture(autouse=True, scope="function")
def purge_results(request):
    """Unlink auto-generated *.result.xml file to declutter build dir"""
    fname = request.function.__name__
    yield
    srcs = list(builddir.glob(f"{fname}*.result.xml"))
    for src in srcs:
        src.unlink()


@allure.epic("Digital signal processing")
@allure.feature("CIC decimation filter")
class TestCIC:
    """Wrapper class for CIC filter tests"""

    arch = {
        "top": "cic_decimator",
        "pkgs": [],
        "comps": [],
    }

    @property
    def sources(self) -> List[Path]:
        """VHDL source and dependencies filepath getter

        Returns:
            List[Path]: Source file and dependencies paths
        """
        srcs = (
            [file for file in work if self.arch["top"] in file.stem]
            + [file for pkg in self.arch["pkgs"] for file in work if pkg in file.stem]
            + [
                file
                for comp in self.arch["comps"]
                for file in work
                if comp in file.stem
            ]
        )
        return srcs

    @property
    def build_kwargs(self) -> Tuple:
        """Build arguments getter

        Returns:
            Tuple: Common build arguments for cocotb-runner
        """
        return {
            "hdl_library": "work",
            "sources": self.sources,
            "hdl_toplevel": self.arch["top"],
            "build_dir": projdir / "sim_build",
        }

    @property
    def test_kwargs(self) -> Tuple:
        """Test arguments getter

        Returns:
            Tuple: Common test arguments for cocotb-runner
        """
        return {
            "test_module": "cic_decimator",
            "hdl_toplevel": self.arch["top"],
            "hdl_toplevel_library": "work",
            "build_dir": projdir / "sim_build",
            "test_dir": projdir / "sim_build",
        }

    @allure.story("Impulse response")
    @pytest.mark.parametrize(
        "cic_order,comb_taps,dec_ratio", cic_generic_combos, ids=(lambda val: val)
    )
    def test_impulse(self, cic_order, comb_taps, dec_ratio):
        """Parametrised impulse response test runner

        Args:
            cic_order (int): CIC order
            comb_taps (int): Differential comb delay
            dec_ratio (int): Decimation ratio
        """
        generics = {
            "cic_order": cic_order,
            "comb_taps": comb_taps,
            "dec_ratio": dec_ratio,
            "compensate": False,
            "s_axis_data_width": 1,
            "m_axis_data_width": 2 + cic_order * ceil(log2(comb_taps * dec_ratio)),
        }
        with allure.step("Build"):
            runner.build(**self.build_kwargs, always=True, parameters=generics)
        with allure.step("Test"):
            runner.test(
                **self.test_kwargs, test_filter="test_impulse", parameters=generics
            )

    @allure.story("Step resonse")
    @pytest.mark.parametrize(
        "cic_order,comb_taps,dec_ratio", cic_generic_combos, ids=(lambda val: val)
    )
    def test_step(self, cic_order, comb_taps, dec_ratio):
        """Parametrised step response test runner

        Args:
            cic_order (int): CIC order
            comb_taps (int): Differential comb delay
            dec_ratio (int): Decimation ratio
        """
        generics = {
            "cic_order": cic_order,
            "comb_taps": comb_taps,
            "dec_ratio": dec_ratio,
            "compensate": False,
            "s_axis_data_width": 1,
            "m_axis_data_width": 2 + cic_order * ceil(log2(comb_taps * dec_ratio)),
        }
        with allure.step("Build"):
            runner.build(**self.build_kwargs, always=True, parameters=generics)
        with allure.step("Test"):
            runner.test(
                **self.test_kwargs, test_filter="test_step", parameters=generics
            )

    @allure.story("PDM bitstream")
    def test_pdm(self):
        """PDM test runner with fixed, close-to-real-world filter parameters"""
        generics = {
            "cic_order": 3,
            "comb_taps": 2,
            "dec_ratio": 64,
            "compensate": False,
            "s_axis_data_width": 2,
            "m_axis_data_width": 2 + 3 * ceil(log2(2 * 64)),
        }
        allure.dynamic.parameter("cic_order", generics["cic_order"])
        allure.dynamic.parameter("comb_taps", generics["comb_taps"])
        allure.dynamic.parameter("dec_ratio", generics["dec_ratio"])

        with allure.step("Build"):
            runner.build(**self.build_kwargs, always=True, parameters=generics)
        with allure.step("Test"):
            runner.test(
                **self.test_kwargs,
                test_filter="test_pdm",
                parameters=generics,
                waves=True,
            )
