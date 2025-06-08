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
--! @brief Testbench suite of impulse & step response and pdm tests 
--------------------------------------------------------------------------------
"""

from math import factorial
from pathlib import Path

import cocotb
import cocotb.regression
import cocotb.simulator
import pandas as pd
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from matplotlib import pyplot as plt

datadir = Path(__file__).resolve().parent.parent / "data"
df = pd.read_csv(datadir / "input1.csv", comment="#")
ser = df.iloc[:, 0]


async def get_params(dut):
    """Evaluate filter parameters based on signal properties"""

    m = len(dut.integrators) - 1
    n = (len(dut.comb_dl) - 1) / m - 1

    while dut.dec_cnt.value != 0:
        await dut.dec_cnt.value_change

    await dut.dec_cnt.value_change

    r = int(dut.dec_cnt.value) + 1

    return m, n, r


async def init(dut):
    """Initialize DUT and hold it in reset for 100 ns"""

    dut.aresetn.value = 0
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.m_axis_tready.value = 0

    cocotb.start_soon(Clock(dut.aclk, 10, "ns").start())

    await Timer(100, "ns")

    dut.aresetn.value = 1

    await RisingEdge(dut.aclk)

    return


@cocotb.test
async def test_impulse(dut):
    """Measure CIC filter impulse response"""

    await init(dut)

    dut.s_axis_tdata.value = 1
    dut.s_axis_tvalid.value = 1
    dut.m_axis_tready.value = 1

    await RisingEdge(dut.aclk)

    dut.s_axis_tdata.value = 0

    params_thread = cocotb.start_soon(get_params(dut))

    out = []

    for _ in range(15):
        await RisingEdge(dut.m_axis_tvalid)
        out.append(int(dut.m_axis_tdata.value))

    m, n, r = await params_thread

    expval = factorial(m + r - 1) / factorial(r) / factorial(m - 1) - m * int(n == 1)

    assert out[1] == expval, f"Expected {expval}, got {out[1]}"
    assert out[-1] == 0, f"Expected zero, got {out[-1]}"


@cocotb.test
async def test_step(dut):
    """Measure CIC filter step response"""

    await init(dut)

    dut.s_axis_tdata.value = 1
    dut.s_axis_tvalid.value = 1
    dut.m_axis_tready.value = 1

    out = []

    for _ in range(15):
        await RisingEdge(dut.m_axis_tvalid)
        out.append(dut.m_axis_tdata.value.to_signed())

    m, n, r = await get_params(dut)

    expval = factorial(m + r) / factorial(r) / factorial(m) - m * int(n == 1)

    assert out[1] == expval, f"Expected {expval}, got {out[1]}"
    assert out[-1] == (r * n) ** m, f"Expected {(r * n) ** m}, got {out[-1]}"


async def drive_pdm(dut, data):
    """Drive pdm signal from file onto filter input"""

    for val in data:
        dut.s_axis_tdata.value = 1 if val > 0 else -1
        await RisingEdge(dut.aclk)


@cocotb.test
async def test_pdm(dut):
    """Test CIC filter against a pulse-density modulated sine bistream"""
    await init(dut)

    dut.s_axis_tvalid.value = 1
    dut.m_axis_tready.value = 1

    driver_thread = cocotb.start_soon(drive_pdm(dut, ser))

    out = []

    while not driver_thread.done():
        await RisingEdge(dut.m_axis_tvalid)
        out.append(dut.m_axis_tdata.value.to_signed())

    m, n, r = await get_params(dut)

    pd.Series(out).to_csv(datadir / "output1.csv", index=False)

    plt.subplot(211)
    plt.plot(ser)
    plt.gca().set_xlabel("Sample")
    plt.gca().set_ylabel("Amplitude")
    plt.subplot(212)
    plt.plot(out)
    plt.gca().set_xlabel("Sample")
    plt.gca().set_ylabel("Amplitude")
    plt.tight_layout()
    plt.savefig(datadir / "io1.jpg")
