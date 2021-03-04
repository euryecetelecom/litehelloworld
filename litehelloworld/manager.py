#!/usr/bin/env python3

#
# This file is part of LiteHelloWorld.
#
"""
LiteHelloWorld standalone core manager

LiteHelloWorld aims to be directly used as a python package when the SoC is created using LiteX. However,
for some use cases it could be interesting to generate a standalone verilog file of the core or use it as standalone:
- integration of the core in a SoC using a more traditional flow.
- core development/tests.
- need to version/package the core.
- avoid Migen/LiteX dependencies.
- etc...

The standalone core is generated from a YAML configuration file that allows the user to generate
easily a custom configuration of the core.
"""

import argparse
import os
import yaml

from migen import *

#Litex build tools
from litex.build.generic_platform import *
from litex.build.altera.platform import AlteraPlatform
from litex.build.lattice.platform import LatticePlatform
from litex.build.xilinx.platform import XilinxPlatform
from litex.build.sim import SimPlatform
from litex.build.sim.config import SimConfig

#Litex SoC tools
from litex.soc.interconnect import wishbone
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *

#Debug tools
from litex.soc.cores import uart
from litescope import LiteScopeAnalyzer

#Custom core classes here
from litehelloworld.core.dummy import DummyLitexModel


# IOs ----------------------------------------------------------------------------------------------
#DOC/QUESTION: WHERE CAN WE GET INFOS ON I/O PARAMETERS AND USAGE-DESCRIPTION?
#There seems to be something like: name, logic (0=active high? 1=active low or on rising edge / and falling edge?), pin(s) used / number of pins only if sim, technology*?
#*: optional
# FPGA I/O
_io = [
    ("sys_clock", 0, Pins("K23"), IOStandard("LVCMOS33")),
    ("sys_reset", 1, Pins("N5"),  IOStandard("LVCMOS33")),
    ("input_bus", 1, Pins("T25 U25 U24 V24 T26 U26 V26 W26"), IOStandard("LVCMOS33")),
    ("output_bus", 1, Pins("U23 V23 U22 V21 W25 W24 W23 W22"), IOStandard("LVCMOS33")),
    ("uart_bridge", 0,
        Subsignal("rx", Pins("R26")),
        Subsignal("tx", Pins("R24")),
        IOStandard("LVCMOS33")
    ),
]
# Predefined Litex-Boards I/O
#TODO HERE: LINK TO BOARD PREDEFINED CONNECTORS LIKE PMOD OR GENERIC IOs AND SERIAL FOR THE BRIDGE?
#_io = [
#]
# Simulation I/O
_sim_io = [
    ("sys_clock", 0, Pins(1)),
    ("sys_reset", 1, Pins(1)),
    ("input_bus", 1, Pins(8)),
    ("output_bus", 1, Pins(8)),
    ("uart_bridge", 0,
        Subsignal("rx", Pins(1)),
        Subsignal("tx", Pins(1)),
    ),
]

class GenericCore(SoCMini):
    def __init__(self, platform, core_config):
        # SoC parameters ---------------------------------------------------------------------------
        soc_args = {}
        if "soc" in core_config:
            soc_config = core_config["soc"]
            for arg in soc_config:
                #QUESTION: IS THERE SOME DOCS ON THESE ARGS (*_map)?
                if arg in ("csr_map", "interrupt_map", "mem_map"):
                    getattr(self, arg).update(soc_config[arg])
                else:
                    soc_args[arg] = soc_config[arg]
        # SoCMini ----------------------------------------------------------------------------------
        SoCMini.__init__(self, platform, clk_freq=core_config["clk_freq"], **soc_args)
        # Clock Reset Generator --------------------------------------------------------------------
        self.submodules.crg = CRG(platform.request("sys_clock"), platform.request("sys_reset"))

    def generate_documentation(self, build_name, **kwargs):
        #Infos: https://github.com/enjoy-digital/litex/wiki/SoC-Documentation
        from litex.soc.doc import generate_docs
        generate_docs(self, "documentation".format(build_name),
            project_name = "LiteHelloWorld standalone core",
            author       = "CHANGE ME")
        os.system("sphinx-build -M html documentation/ documentation/_build".format(build_name, build_name))

# Dummy Litex Core --------------------------------------------------------------------------------
class DummyLitexCore(GenericCore):
    def __init__(self, platform, core_config):
        GenericCore.__init__(self, platform, core_config)
        # DummyPhy --------------------------------------------------------------------------------
        self.submodules.dummyphy = DummyLitexModel(
            inputs=platform.request("input_bus"),
            outputs=platform.request("output_bus"),
        )
        # Wishbone slave connexion
        self.add_wb_slave(self.mem_map["dummyphy"], self.dummyphy.bus)
        self.add_memory_region("dummyphy", self.mem_map["dummyphy"], 0x2000, type="io")
        #QUESTION: WHAT MEANS CSR ACRONYM IN THE FRAME OF LITEX?
        #Infos: https://github.com/enjoy-digital/litex/wiki/CSR-Bus
        self.add_csr("dummyphy")
        # UART BRIDGE TO CONTROL WISHBONE BUS ------------------------------------------------------
        # QUESTION: NO PROBLEM TO USE IT IN SIM MODE ALSO? IS THERE A TRICK ALSO TO HAVE A VIRTUAL UART IN SIM MODE LIKE FOR ETH TAP? CF QUESTION ALSO IN MAIN RELATED TO serial2console
        #Infos: https://github.com/enjoy-digital/litex/wiki/Use-Host-Bridge-to-control-debug-a-SoC
        self.submodules.uart_bridge = uart.UARTWishboneBridge(
            pads=platform.request("uart_bridge"),
            clk_freq=core_config["clk_freq"],
            baudrate=115200,
        )
        self.add_wb_master(self.uart_bridge.wishbone)
        # LITESCOPE TO DEBUG CORE INTERNALS --------------------------------------------------------
        #Infos: https://github.com/enjoy-digital/litex/wiki/Use-LiteScope-To-Debug-A-SoC
        analyzer_signals = [
            self.dummyphy.sink,
            self.dummyphy.source,
            self.dummyphy.bus,
        ]
        self.submodules.analyzer = LiteScopeAnalyzer(
            analyzer_signals,
            depth=512,
            clock_domain="sys",
            csr_csv="analyzer.csv"
        )
        self.add_csr("analyzer")

# Build --------------------------------------------------------------------------------------------
def main():
    core_name = "litehelloworld_core"

    # Parameters available -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(description="LiteHelloWorld standalone core manager")
    parser.set_defaults(output_dir="build")
    parser.add_argument("config", help="YAML config file")
    parser.add_argument("--build", action="store_true", help="Generate RTL and gateware bitstream")
    parser.add_argument("--doc", action="store_true", help="Generate documentation")
    parser.add_argument("--flash", action="store_true", help="Flash bitstream")
    parser.add_argument("--generate", action="store_true", help="Generate RTL code")
    parser.add_argument("--load", action="store_true", help="Load bitstream")
    parser.add_argument("--sim", action="store_true", help="Simulate core")
    parser.add_argument("--trace", action="store_true", help="Enable VCD tracing (for sim mode)")
    parser.add_argument("--trace-start", default=0, help="Cycle to start VCD tracing (for sim mode)")
    parser.add_argument("--trace-end", default=-1, help="Cycle to end VCD tracing (for sim mode)")
    parser.add_argument("--opt-level", default="O3", help="Compilation optimization level (for sim mode)")
    args = parser.parse_args()
    core_config = yaml.load(open(args.config).read(), Loader=yaml.Loader)

    # Convert YAML elements to Python/LiteX --------------------------------------------------------
    for k, v in core_config.items():
        replaces = {"False": False, "True": True, "None": None}
        for r in replaces.keys():
            if v == r:
                core_config[k] = replaces[r]
        if k == "clk_freq" or k == "clk_sim":
            core_config[k] = int(float(core_config[k]))

    # Generate core --------------------------------------------------------------------------------
    if args.sim:
        platform = SimPlatform("Simulation", io=_sim_io)
        #QUESTION: MIGHT/NEED BE DIRECTLY ADDED TO io PARAM BEFORE??
        platform.add_extension(_sim_io)
        #QUESTION: OK/NEEDED TO OVERLOAD CLK HERE OR HAS TO BE DIFFERENT CLOCKS OR JUST NOT USED IN SIM MODE?
        core_config["clk_freq"] = core_config["clk_sim"]
    else:
        if core_config["vendor"] == "altera":
            platform = AlteraPlatform(device=core_config["device"], io=[], toolchain=core_config["toolchain"])
        elif core_config["vendor"] == "lattice":
            platform = LatticePlatform(device=core_config["device"], io=[], toolchain=core_config["toolchain"])
        elif core_config["vendor"] == "xilinx":
            platform = XilinxPlatform(device=core_config["device"], io=[], toolchain=core_config["toolchain"])
        else:
            raise ValueError("Unsupported vendor: {}".format(core_config["vendor"]))
        platform.add_extension(_io)

    soc = DummyLitexCore(platform, core_config)

    if args.sim:
        if args.build or args.load or args.flash:
            raise ValueError("Cannot build/load/flash while simulating the core. Please use --sim option alone")
        sim_config = SimConfig(default_clk="sys_clock")
        #QUESTION: IF POSSIBLE TO USE UART BRIDGE, THIS IS HOW TO ADD A VIRTUAL TTY? WHAT WILL BE ITS NAME? BUT THERE IS A SEG FAULT WITH THIS LINE. SOMETHING IS MISSING?
        #sim_config.add_module("serial2console", "uart_bridge", clocks="sys_clock")
        builder = Builder(soc, csr_csv="csr.csv")
        #QUESTION/FIXME: NO TRACE TAKEN (vcd file empty)
        builder.build(
            sim_config=sim_config,
            run = True,
            opt_level = args.opt_level,
            trace = args.trace,
            trace_start = int(args.trace_start),
            trace_end = int(args.trace_end)
        )
    else:
        if args.build:
            #FIXME/QUESTION: WHY FINAL TIMING ANALYSIS TELLS ME 12MHz REQUIRED INSTEAD OF 100MHz? ("Info: Max frequency for clock '$glbnet$sys_clock$TRELLIS_IO_IN': 117.36 MHz (PASS at 12.00 MHz)")
            builder = Builder(soc, csr_csv="csr.csv")
            builder.build(build_name=core_name)
        if args.flash or args.load:
            #TODO/QUESTION: SPECIFIC BOARD INSTANTIATION + PINOUT OR TO BE TAKEN IN ACCOUNT IN PLATFORM INSTANTIATION??
            prog = soc.platform.create_programmer()
            if args.flash:
                prog.flash(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))
            if args.load:
                prog.load(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))
        if args.generate:
            builder = Builder(soc, compile_gateware=False)
            builder.build(build_name=core_name)

    if args.doc:
        soc.generate_documentation(core_name)

if __name__ == "__main__":
    main()
