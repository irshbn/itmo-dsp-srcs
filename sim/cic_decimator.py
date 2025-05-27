import pandas as pd
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer, RisingEdge


datadir = Path(__file__).resolve().parent.parent / "data"
df = pd.read_csv(datadir / "input1.csv", comment="#")
ser = df.iloc[:, 0]


async def init(dut):
    dut.aresetn.value = 0
    dut.s_axis_tvalid.value = 0
    dut.s_axis_tdata.value = 0
    dut.m_axis_tready.value = 0

    await Timer(100, "ns")

    dut.aresetn.value = 1

    return


@cocotb.test
async def test_cic(dut):
    cocotb.start_soon(Clock(dut.aclk, 10, "ns").start())

    await init(dut)

    dut.s_axis_tvalid.value = 1
    dut.m_axis_tready.value = 1

    for val in ser:
        dut.s_axis_tdata.value = int(val > 0)
        await RisingEdge(dut.aclk)
