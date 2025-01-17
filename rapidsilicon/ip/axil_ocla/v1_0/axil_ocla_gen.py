#!/usr/bin/env python3
#
# This file is Copyright (c) 2022 RapidSilicon.
#
# SPDX-License-Identifier: MIT

import os
import sys
import logging
from pathlib import Path
import argparse

from datetime import datetime

from litex_wrapper.axil_ocla_litex_wrapper import AXILITEOCLA

from migen import *

from litex.build.generic_platform import *

from litex.build.osfpga import OSFPGAPlatform

from litex.soc.interconnect.axi import AXILiteInterface


# IOs/Interfaces -----------------------------------------------------------------------------------
def get_axiclknrst_ios():
    return [
        ("i_S_AXI_ACLK",      0, Pins(1)),
        ("i_S_AXI_ARESETN",   0, Pins(1)),
    ]

def get_samplingclknrst_ios():
    return [
        ("i_sample_clk",  0, Pins(1)),
        ("i_rstn",        0, Pins(1)),
    ]    
    
def get_ocla_ios(nprobes,trigger_inputs):
    return [
        ("i_probes",          0, Pins(nprobes)),
        ("i_trigger_input",   0, Pins(trigger_inputs)), 
    ]

# AXI LITE OCLA Wrapper ----------------------------------------------------------------------------------
class AXILITEOCLAWrapper(Module):
    def __init__(self, platform, address_width, data_width, nprobes, trigger_inputs, probe_widht,mem_depth, trigger_inputs_en):
        
        # Clocking ---------------------------------------------------------------------------------
        platform.add_extension(get_axiclknrst_ios())
        self.clock_domains.cd_sys  = ClockDomain()
        self.comb += self.cd_sys.clk.eq(platform.request("i_S_AXI_ACLK"))
        self.comb += self.cd_sys.rst.eq(platform.request("i_S_AXI_ARESETN"))

        # Clocking ---------------------------------------------------------------------------------
        platform.add_extension(get_samplingclknrst_ios())
        self.clock_domains.cd_sys  = ClockDomain("i_sample_clk")
        self.comb += self.cd_sys.clk.eq(platform.request("i_sample_clk"))
        self.clock_domains.cd_sys  = ClockDomain("i_rstn")
        self.comb += self.cd_sys.rst.eq(platform.request("i_rstn"))

        # AXI LITE --------------------------------------------------------------------------------------
        s_axil = AXILiteInterface(
            address_width       = address_width,
            data_width          = data_width
        )
        platform.add_extension(s_axil.get_ios("s_axil"))
        self.comb += s_axil.connect_to_pads(platform.request("s_axil"), mode="slave")

        # AXI-LITE-OCLA ----------------------------------------------------------------------------------
        self.submodules.ocla = ocla =  AXILITEOCLA(platform, 
            s_axil             = s_axil,
            nprobes          = nprobes,
            trigger_inputs   = trigger_inputs,
            probe_widht      = probe_widht,
            mem_depth        = mem_depth,
            trigger_inputs_en   = trigger_inputs_en
            )
        # OCLA Signals --------------------------------------------------------------------------------
        # print (int(nprobes),int(trigger_inputs))
        platform.add_extension(get_ocla_ios(nprobes,trigger_inputs))
        
        # Inputs
        self.comb += ocla.probes_i.eq(platform.request("i_probes"))
        if(trigger_inputs_en == True):
            self.comb += ocla.trigger_input_i.eq(platform.request("i_trigger_input"))
    
# Build --------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="AXI LITE OCLA CORE")

    # Import Common Modules.
    common_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")
    #common_path = os.path.join(os.path.dirname(__file__),"lib")

    sys.path.append(common_path)

    from common import IP_Builder
    # Parameter Dependency dictionary a 2 b 3 c 4  9
    #                Ports     :    Dependency
    dep_dict = {}            

    # IP Builder.
    rs_builder = IP_Builder(device="gemini", ip_name="axil_ocla", language="sverilog")

    logging.info("===================================================")
    logging.info("IP    : %s", rs_builder.ip_name.upper())
    logging.info(("==================================================="))
    
    # Core fix value parameters.
    core_fix_param_group = parser.add_argument_group(title="OCLA IP Core fix parameters")
    core_fix_param_group.add_argument("--mem_depth",             type=int,      default=32,     choices=[32, 64, 128, 256, 512, 1024],   help="OCLA Trace Memory Depth.")
    core_fix_param_group.add_argument("--s_axi_addr_width",      type=int,      default=32,     choices=[8, 16, 32],                     help="OCLA Address Width.")
    core_fix_param_group.add_argument("--s_axi_data_width",      type=int,      default=32,     choices=[32],                            help="OCLA Data Width.")
    
    # Core range value parameters.
    core_range_param_group = parser.add_argument_group(title="OCLA IP Core range parameters")
    core_range_param_group.add_argument("--no_of_probes",           type=int,  default=32, choices=range(1,1025),         help="Number of Probes.")

 # Core bool value macros.
    core_bool_param_group = parser.add_argument_group(title="OCLA IP Core bool parameters")
    core_bool_param_group.add_argument("--value_compare",                         type=bool, default=False,                                   help="To enable Value Compare feature")
    core_range_param_group.add_argument("--value_compare_probe_width",            type=int,  default=1,         choices=range(1, 32),         help="Width of probe for Value Compare. Only applicable when value compare feature is enable")

    core_bool_param_group.add_argument("--trigger_inputs_en",       type=bool, default=False,                                 help="To enable Trigger inputs")
    core_range_param_group.add_argument("--no_of_trigger_inputs",   type=int,  default=1,       choices=range(1,32),          help="Number of Input Triggers.")
    #core_bool_param_group.add_argument("--advance_trigger",     type=bool, default=False,              help="To enable Advance Trigger Mode")
   
   
    # Build Parameters.
    build_group = parser.add_argument_group(title="Build parameters")
    build_group.add_argument("--build",         action="store_true",            help="Build Core")
    build_group.add_argument("--build-dir",     default="./",                   help="Build Directory")
    build_group.add_argument("--build-name",    default="axil_ocla_wrapper",    help="Build Folder Name, Build RTL File Name and Module Name")

    
    # JSON Import/Template
    json_group = parser.add_argument_group(title="JSON Parameters")
    json_group.add_argument("--json",                                           help="Generate Core from JSON File")
    json_group.add_argument("--json-template",  action="store_true",            help="Generate JSON Template")

    args = parser.parse_args()

    details =  {   "IP details": {
    'Name' : 'OCLA',
    'Version' : 'V1_0',
    'Interface' : 'AXI4 Lite ',
    'Description' : 'The On Chip Logic Analyzer (OCLA) core is a customizable logic analyzer that conforms to the AXI4-Lite specifi-cation and is intended for use in applications that necessitate verification or debugging through the monitoring ofinternal signals within a design on FPGAs'}
    }

    
    # Import JSON (Optional) -----------------------------------------------------------------------
    if args.json:
        args = rs_builder.import_args_from_json(parser=parser, json_filename=args.json)
        rs_builder.import_ip_details_json(build_dir=args.build_dir ,details=details , build_name = args.build_name, version = "v1_0")

    summary =  { 
    # "DATA WIDTH": args.data_width,
    "Number of Probes":args.no_of_probes,
    "Buffer size": args.mem_depth,
    # "PIPELINE OUTPUT": args.pip_out
    }
    # Export JSON Template (Optional) --------------------------------------------------------------
    if args.json_template:
        rs_builder.export_json_template(parser=parser, dep_dict=dep_dict, summary=summary)

    # Create LiteX Core ----------------------------------------------------------------------------
    platform   = OSFPGAPlatform( io=[], device="gemini", toolchain="raptor")
    module     = AXILITEOCLAWrapper(platform,
        address_width     = args.s_axi_addr_width,
        data_width        = args.s_axi_data_width,
        nprobes           = args.no_of_probes , 
        trigger_inputs    = args.no_of_trigger_inputs , 
        probe_widht       = args.value_compare_probe_width , 
        mem_depth         = args.mem_depth,
        trigger_inputs_en = args.trigger_inputs_en
    )
    # Arguments ----------------------------------------------------------------------------
    value_compare     = args.value_compare
    # advance_trigger   = args.advance_trigger
    triginpts_en      = args.trigger_inputs_en
    nofprobes         = args.no_of_probes  
    ntrigger_inputs   = args.no_of_trigger_inputs  
    nprobe_widht      = args.value_compare_probe_width 
    memory_depth      = args.mem_depth
    
    # Build Project --------------------------------------------------------------------------------
    if args.build:
        rs_builder.prepare(
            build_dir  = args.build_dir,
            build_name = args.build_name,
            version    = "v1_0"
        )
        rs_builder.copy_files(gen_path=os.path.dirname(__file__))
        rs_builder.generate_tcl()
        rs_builder.generate_wrapper(
            platform   = platform,
            module     = module,
            version = "v1_0"
        )
        
        # IP_ID Parameter
        now = datetime.now()
        my_year         = now.year - 2022
        year            = (bin(my_year)[2:]).zfill(7) # 7-bits  # Removing '0b' prefix = [2:]
        month           = (bin(now.month)[2:]).zfill(4) # 4-bits
        day             = (bin(now.day)[2:]).zfill(5) # 5-bits
        mod_hour        = now.hour % 12 # 12 hours Format
        hour            = (bin(mod_hour)[2:]).zfill(4) # 4-bits
        minute          = (bin(now.minute)[2:]).zfill(6) # 6-bits
        second          = (bin(now.second)[2:]).zfill(6) # 6-bits
        
        # Concatenation for IP_ID Parameter
        ip_id = ("{}{}{}{}{}{}").format(year, day, month, hour, minute, second)
        ip_id = ("32'h{}").format(hex(int(ip_id,2))[2:])
        
        # IP_VERSION parameter
        #               Base  _  Major _ Minor
        ip_version = "00000000_00000000_0000000000000001"
        ip_version = ("32'h{}").format(hex(int(ip_version, 2))[2:])
        
        wrapper = os.path.join(args.build_dir, "rapidsilicon", "ip", "axil_ocla", "v1_0", args.build_name, "src",args.build_name + "_v1_0" + ".sv")
        new_lines = []
        with open (wrapper, "r") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if ("module {}".format(args.build_name)) in line:
                    new_lines.append("module {} #(\n\tparameter IP_TYPE \t\t= \"OCLA\",\n\tparameter IP_VERSION \t= {}, \n\tparameter IP_ID \t\t= {}\n)\n(".format(args.build_name, ip_version, ip_id))
                else:
                    new_lines.append(line)
                
        with open(os.path.join(wrapper), "w") as file:
            file.writelines(new_lines)
        
        build_name = args.build_name.rsplit( ".", 1 )[ 0 ]
        file = os.path.join(args.build_dir, "rapidsilicon/ip/axil_ocla/v1_0", build_name, "sim/axil_ocla_wrapper_tb.sv")
        file = Path(file)
        text = file.read_text()
        text = text.replace("axil_ocla_wrapper", "%s" % build_name)
        file.write_text(text)
        
if __name__ == "__main__":
    main()

