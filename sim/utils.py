import sys
from pathlib import Path
from cocotb_tools.runner import Runner


def get_dependencies(top: str, workdir: Path):
    filepath = workdir / (top + ".vhdl")
    f = open(filepath)
    lines = f.readlines()

    pkgmarks = ["use", "pkg"]
    entmarks = [":", "entity"]

    pkgs = []
    modules = []

    for line in lines:
        if all(x in line for x in pkgmarks):
            segs = line.split(".")
            for seg in segs:
                if "pkg" in seg:
                    pkgs.append(seg)
        elif all(x in line for x in entmarks):
            segs = line.split(".")
            entseg = segs[-1]
            modules.append(entseg.split("(")[0])

    return pkgs, modules


def wfm_namegen(top, test):
    return f"--wave={top}_{test}.fst"


def sort_srcs(srcs: list[Path], topname: str, pkgs: list[str], modules: list[str]):
    first = []
    mid = []
    last = []

    for src in srcs:
        for pkg in pkgs:
            if src.stem == pkg:
                first.append(src)

        for module in modules:
            if src.stem == module:
                mid.append(src)

        if src.stem == topname:
            last.append(src)

    return first + mid + last


def run(
    setup: tuple[Runner, list[Path]],
    topname: str,
    pkgs: list[str],
    modules: list[str],
    **kwargs,
):
    runner, sources = setup
    sources = sort_srcs(sources, topname, pkgs, modules)
    testname = sys._getframe(1).f_code.co_name
    runner.build(hdl_library="work", sources=sources, hdl_toplevel=topname, always=True)
    runner.test(
        hdl_toplevel=topname,
        hdl_toplevel_library="work",
        test_module=topname,
        plusargs=[wfm_namegen(topname, testname)],
        test_filter=testname,
        **kwargs,
    )
