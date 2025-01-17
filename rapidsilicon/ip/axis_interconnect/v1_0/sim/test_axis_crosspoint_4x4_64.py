#!/usr/bin/env python
"""

Copyright (c) 2014-2018 Alex Forencich

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

from myhdl import *
import os

import axis_ep
import math

module = 'axis_crosspoint'
testbench = 'test_%s_4x4_64' % module

srcs = []

srcs.append("../src/*.v")
srcs.append("%s.v" % testbench)

src = ' '.join(srcs)

build_cmd = "iverilog -o %s.vvp %s" % (testbench, src)

def bench():

    # Parameters
    S_COUNT = 4
    M_COUNT = 4
    DATA_WIDTH = 64
    KEEP_ENABLE = (DATA_WIDTH>8)
    KEEP_WIDTH = (DATA_WIDTH/8)
    LAST_ENABLE = 1
    ID_ENABLE = 1
    ID_WIDTH = 8
    DEST_ENABLE = 1
    DEST_WIDTH = 8
    USER_ENABLE = 1
    USER_WIDTH = 1

    # Inputs
    clk = Signal(bool(0))
    rst = Signal(bool(0))
    current_test = Signal(intbv(0)[8:])

    s_axis_tdata_list = [Signal(intbv(0)[DATA_WIDTH:]) for i in range(S_COUNT)]
    s_axis_tkeep_list = [Signal(intbv(1)[KEEP_WIDTH:]) for i in range(S_COUNT)]
    s_axis_tvalid_list = [Signal(bool(0)) for i in range(S_COUNT)]
    s_axis_tlast_list = [Signal(bool(0)) for i in range(S_COUNT)]
    s_axis_tid_list = [Signal(intbv(0)[ID_WIDTH:]) for i in range(S_COUNT)]
    s_axis_tdest_list = [Signal(intbv(0)[DEST_WIDTH:]) for i in range(S_COUNT)]
    s_axis_tuser_list = [Signal(intbv(0)[USER_WIDTH:]) for i in range(S_COUNT)]

    s_axis_tdata = ConcatSignal(*reversed(s_axis_tdata_list))
    s_axis_tkeep = ConcatSignal(*reversed(s_axis_tkeep_list))
    s_axis_tvalid = ConcatSignal(*reversed(s_axis_tvalid_list))
    s_axis_tlast = ConcatSignal(*reversed(s_axis_tlast_list))
    s_axis_tid = ConcatSignal(*reversed(s_axis_tid_list))
    s_axis_tdest = ConcatSignal(*reversed(s_axis_tdest_list))
    s_axis_tuser = ConcatSignal(*reversed(s_axis_tuser_list))

    select_list = [Signal(intbv(0)[math.ceil(math.log(S_COUNT, 2)):]) for i in range(M_COUNT)]

    select = ConcatSignal(*reversed(select_list))

    # Outputs
    m_axis_tdata = Signal(intbv(0)[M_COUNT*DATA_WIDTH:])
    m_axis_tkeep = Signal(intbv(0xf)[M_COUNT*KEEP_WIDTH:])
    m_axis_tvalid = Signal(intbv(0)[M_COUNT:])
    m_axis_tlast = Signal(intbv(0)[M_COUNT:])
    m_axis_tid = Signal(intbv(0)[M_COUNT*ID_WIDTH:])
    m_axis_tdest = Signal(intbv(0)[M_COUNT*DEST_WIDTH:])
    m_axis_tuser = Signal(intbv(0)[M_COUNT*USER_WIDTH:])

    m_axis_tdata_list = [m_axis_tdata((i+1)*DATA_WIDTH, i*DATA_WIDTH) for i in range(M_COUNT)]
    m_axis_tkeep_list = [m_axis_tkeep((i+1)*KEEP_WIDTH, i*KEEP_WIDTH) for i in range(M_COUNT)]
    m_axis_tvalid_list = [m_axis_tvalid(i) for i in range(M_COUNT)]
    m_axis_tlast_list = [m_axis_tlast(i) for i in range(M_COUNT)]
    m_axis_tid_list = [m_axis_tid((i+1)*ID_WIDTH, i*ID_WIDTH) for i in range(M_COUNT)]
    m_axis_tdest_list = [m_axis_tdest((i+1)*DEST_WIDTH, i*DEST_WIDTH) for i in range(M_COUNT)]
    m_axis_tuser_list = [m_axis_tuser((i+1)*USER_WIDTH, i*USER_WIDTH) for i in range(M_COUNT)]

    # sources and sinks
    source_pause_list = []
    source_list = []
    source_logic_list = []
    sink_pause_list = []
    sink_list = []
    sink_logic_list = []

    for k in range(S_COUNT):
        s = axis_ep.AXIStreamSource()
        p = Signal(bool(0))

        source_list.append(s)
        source_pause_list.append(p)

        source_logic_list.append(s.create_logic(
            clk,
            rst,
            tdata=s_axis_tdata_list[k],
            tkeep=s_axis_tkeep_list[k],
            tvalid=s_axis_tvalid_list[k],
            tlast=s_axis_tlast_list[k],
            tid=s_axis_tid_list[k],
            tdest=s_axis_tdest_list[k],
            tuser=s_axis_tuser_list[k],
            pause=p,
            name='source_%d' % k
        ))

    for k in range(M_COUNT):
        s = axis_ep.AXIStreamSink()
        p = Signal(bool(0))

        sink_list.append(s)
        sink_pause_list.append(p)

        sink_logic_list.append(s.create_logic(
            clk,
            rst,
            tdata=m_axis_tdata_list[k],
            tkeep=m_axis_tkeep_list[k],
            tvalid=m_axis_tvalid_list[k],
            tlast=m_axis_tlast_list[k],
            tid=m_axis_tid_list[k],
            tdest=m_axis_tdest_list[k],
            tuser=m_axis_tuser_list[k],
            pause=p,
            name='sink_%d' % k
        ))

    # DUT
    if os.system(build_cmd):
        raise Exception("Error running build command")

    dut = Cosimulation(
        "vvp -m ./myhdl %s.vvp -lxt2" % testbench,
        clk=clk,
        rst=rst,
        current_test=current_test,

        s_axis_tdata=s_axis_tdata,
        s_axis_tkeep=s_axis_tkeep,
        s_axis_tvalid=s_axis_tvalid,
        s_axis_tlast=s_axis_tlast,
        s_axis_tid=s_axis_tid,
        s_axis_tdest=s_axis_tdest,
        s_axis_tuser=s_axis_tuser,

        m_axis_tdata=m_axis_tdata,
        m_axis_tkeep=m_axis_tkeep,
        m_axis_tvalid=m_axis_tvalid,
        m_axis_tlast=m_axis_tlast,
        m_axis_tid=m_axis_tid,
        m_axis_tdest=m_axis_tdest,
        m_axis_tuser=m_axis_tuser,

        select=select
    )

    @always(delay(4))
    def clkgen():
        clk.next = not clk

    @instance
    def check():
        yield delay(100)
        yield clk.posedge
        rst.next = 1
        yield clk.posedge
        rst.next = 0
        yield clk.posedge
        yield delay(100)
        yield clk.posedge

        yield clk.posedge

        yield clk.posedge
        print("test 1: 0123 -> 0123")
        current_test.next = 1

        select_list[0].next = 0
        select_list[1].next = 1
        select_list[2].next = 2
        select_list[3].next = 3

        test_frame0 = axis_ep.AXIStreamFrame(b'\x01\x00\x00\xFF\x01\x02\x03\x04', id=0, dest=0)
        test_frame1 = axis_ep.AXIStreamFrame(b'\x01\x01\x01\xFF\x01\x02\x03\x04', id=1, dest=1)
        test_frame2 = axis_ep.AXIStreamFrame(b'\x01\x02\x02\xFF\x01\x02\x03\x04', id=2, dest=2)
        test_frame3 = axis_ep.AXIStreamFrame(b'\x01\x03\x03\xFF\x01\x02\x03\x04', id=3, dest=3)
        source_list[0].send(test_frame0)
        source_list[1].send(test_frame1)
        source_list[2].send(test_frame2)
        source_list[3].send(test_frame3)

        yield sink_list[0].wait()
        rx_frame0 = sink_list[0].recv()

        assert rx_frame0 == test_frame0

        yield sink_list[1].wait()
        rx_frame1 = sink_list[1].recv()

        assert rx_frame1 == test_frame1

        yield sink_list[2].wait()
        rx_frame2 = sink_list[2].recv()

        assert rx_frame2 == test_frame2

        yield sink_list[3].wait()
        rx_frame3 = sink_list[3].recv()

        assert rx_frame3 == test_frame3

        yield delay(100)

        yield clk.posedge
        print("test 2: 0123 -> 3210")
        current_test.next = 2

        select_list[0].next = 3
        select_list[1].next = 2
        select_list[2].next = 1
        select_list[3].next = 0

        test_frame0 = axis_ep.AXIStreamFrame(b'\x02\x00\x03\xFF\x01\x02\x03\x04', id=0, dest=3)
        test_frame1 = axis_ep.AXIStreamFrame(b'\x02\x01\x02\xFF\x01\x02\x03\x04', id=1, dest=2)
        test_frame2 = axis_ep.AXIStreamFrame(b'\x02\x02\x01\xFF\x01\x02\x03\x04', id=2, dest=1)
        test_frame3 = axis_ep.AXIStreamFrame(b'\x02\x03\x00\xFF\x01\x02\x03\x04', id=3, dest=0)
        source_list[0].send(test_frame0)
        source_list[1].send(test_frame1)
        source_list[2].send(test_frame2)
        source_list[3].send(test_frame3)

        yield sink_list[0].wait()
        rx_frame0 = sink_list[0].recv()

        assert rx_frame0 == test_frame3

        yield sink_list[1].wait()
        rx_frame1 = sink_list[1].recv()

        assert rx_frame1 == test_frame2

        yield sink_list[2].wait()
        rx_frame2 = sink_list[2].recv()

        assert rx_frame2 == test_frame1

        yield sink_list[3].wait()
        rx_frame3 = sink_list[3].recv()

        assert rx_frame3 == test_frame0

        yield delay(100)

        yield clk.posedge
        print("test 3: 0000 -> 0123")
        current_test.next = 3

        select_list[0].next = 0
        select_list[1].next = 0
        select_list[2].next = 0
        select_list[3].next = 0

        test_frame0 = axis_ep.AXIStreamFrame(b'\x03\x00\xFF\xFF\x01\x02\x03\x04', id=0, dest=0)
        source_list[0].send(test_frame0)

        yield sink_list[0].wait()
        rx_frame0 = sink_list[0].recv()

        assert rx_frame0 == test_frame0

        yield sink_list[1].wait()
        rx_frame1 = sink_list[1].recv()

        assert rx_frame1 == test_frame0

        yield sink_list[2].wait()
        rx_frame2 = sink_list[2].recv()

        assert rx_frame2 == test_frame0

        yield sink_list[3].wait()
        rx_frame3 = sink_list[3].recv()

        assert rx_frame3 == test_frame0

        yield delay(100)

        raise StopSimulation

    return instances()

def test_bench():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sim = Simulation(bench())
    sim.run()

if __name__ == '__main__':
    print("Running test...")
    test_bench()
