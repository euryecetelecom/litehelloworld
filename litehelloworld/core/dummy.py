#
# This file is part of LiteHelloWorld.
#

from migen import *

from litex.soc.interconnect import stream

from litehelloworld.common import *
from litex.soc.interconnect import wishbone

class DummyLitexModel(Module):
    def __init__(self, inputs, outputs):
        #Create inputs and outputs for the core
        self.sink = stream.Endpoint(dummy_phy_data_layout)
        self.source = stream.Endpoint(dummy_phy_data_layout)
        #Assign them to inputs and outputs
        self.comb += [
            self.sink.eq(outputs),
            self.source.eq(inputs),
        ]
        #Copy data from inputs to outputs synchronously with sys_clock
        self.sync += [
            self.sink.eq(self.source),
        ]
        #Create wishbone connexion to gather data from it
        self.bus = wishbone.Interface()
        #QUESTION/FIXME: IS THERE SOME LIB READY TO USE TO MANAGE READ/WRITE ACCESS TO WISHBONE BASED ON MEMORY MAP AND SO ON?
        #Memory section from this doc is outdated? https://github.com/enjoy-digital/litex/wiki/LiteX-for-Hardware-Engineers
        #EXAMPLE COULD BE TO WRITE TO self.sink WHEN DATA IS COMING/READ FROM THE WISHBONE BUS AND TO WRITE TO WISHBONE BUS WHEN SPECIFIC DATA IS COMING FROM self.source


#TODO HERE: DUMMY EXTERNAL HDL CORE INTEGRATION EXAMPLE CLASS