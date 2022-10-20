#!/usr/bin/env python3
#
# This file is Copyright (c) 2022 RapidSilicon.
#
# SPDX-License-Identifier: MIT

import os
import sys
import json
import argparse
import shutil
import logging
import math

from litex_sim.priority_encoder_litex_wrapper import PRIORITYENCODER

from migen import *

from litex.build.generic_platform import *

from litex.build.osfpga import OSFPGAPlatform


# IOs/Interfaces -----------------------------------------------------------------------------------
def get_clkin_ios():
    return [
        ("clk",  0, Pins(1)),
        ("rst",  0, Pins(1))
    ]

def get_other_ios(width):
        return [
            ("input_unencoded",  0, Pins(width)), 
            ("output_valid",     0, Pins(1)), 
            ("output_encoded",   0, Pins(math.ceil(math.log2(width)))), 
            ("output_unencoded", 0, Pins(width)), 
        ]

# PRIORITY_ENCODER Wrapper ----------------------------------------------------------------------------------
class PRIORITYENCODERWrapper(Module):
    def __init__(self, platform, width, lsb_high_priority):
        
        self.clock_domains.cd_sys  = ClockDomain()
        
        # PRIORITY_ENCODER ----------------------------------------------------------------------------------
        self.submodules.priority_encoder = priority_encoder = PRIORITYENCODER(platform,
            width               = width,
            lsb_high_priority   = lsb_high_priority
            )
        
        # IOS 
        platform.add_extension(get_other_ios(width))
        self.comb += priority_encoder.input_unencoded.eq(platform.request("input_unencoded"))
        self.comb += platform.request("output_valid").eq(priority_encoder.output_valid)
        self.comb += platform.request("output_encoded").eq(priority_encoder.output_encoded)
        self.comb += platform.request("output_unencoded").eq(priority_encoder.output_unencoded)
        

# Build --------------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="PRIORITY_ENCODER")

    # Import Common Modules.
    common_path = os.path.join(os.path.dirname(__file__), "..", "..")
    sys.path.append(common_path)

    from common import RapidSiliconIPCatalogBuilder

    # Core Parameters.
    core_group = parser.add_argument_group(title="Core parameters")
    core_group.add_argument("--width",                  default=4,     type=int,        help="Width from 2 to 8")
    core_group.add_argument("--lsb_high_priority",      default=0,     type=int,        help="LSB High Priority 0 or 1")

    # Build Parameters.
    build_group = parser.add_argument_group(title="Build parameters")
    build_group.add_argument("--build",         action="store_true",                    help="Build Core")
    build_group.add_argument("--build-dir",     default="./",                           help="Build Directory")
    build_group.add_argument("--build-name",    default="priority_encoder_wrapper",     help="Build Folder Name, Build RTL File Name and Module Name")

    # JSON Import/Template
    json_group = parser.add_argument_group(title="JSON Parameters")
    json_group.add_argument("--json",                                           help="Generate Core from JSON File")
    json_group.add_argument("--json-template",  action="store_true",            help="Generate JSON Template")

    args = parser.parse_args()

    # Parameter Check -------------------------------------------------------------------------------
    logger = logging.getLogger("Invalid Parameter Value")
    
    # Width
    width_range=range(2,9)
    if args.width not in width_range:
        logger.error("\nEnter a valid 'width' from 2 to 8")
        exit()
        
    # Data Width
    lsb_high_priority_range=range(2)
    if args.lsb_high_priority not in lsb_high_priority_range:
        logger.error("\nEnter a valid 'lsb_high_priority' 0 or 1")
        exit()

    # Import JSON (Optional) -----------------------------------------------------------------------
    if args.json:
        with open(args.json, 'rt') as f:
            t_args = argparse.Namespace()
            t_args.__dict__.update(json.load(f))
            args = parser.parse_args(namespace=t_args)

    # Export JSON Template (Optional) --------------------------------------------------------------
    if args.json_template:
        print(json.dumps(vars(args), indent=4))

    # Create Wrapper -------------------------------------------------------------------------------
    platform = OSFPGAPlatform(io=[], toolchain="raptor", device="gemini")
    module   = PRIORITYENCODERWrapper(platform,
        width             = args.width,
        lsb_high_priority = args.lsb_high_priority,
    )

    # Build Project --------------------------------------------------------------------------------
    if args.build:
        rs_builder = RapidSiliconIPCatalogBuilder(device="gemini", ip_name="priority_encoder")
        rs_builder.prepare(
            build_dir  = args.build_dir,
            build_name = args.build_name,
        )
        rs_builder.copy_files(gen_path=os.path.dirname(__file__))
        rs_builder.generate_tcl()

if __name__ == "__main__":
    main()
