#!/usr/bin/env python3
"""Generate the native Raspberry Pi ARM64 host + ILP32 guest build."""
import sys
import argparse
from pathlib import Path
from types import SimpleNamespace
from tools.ninja_syntax import Writer
from tools.linux_build import generate_linux_build
from tools.pi_build import generate_pi_build
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--optimization',choices=['O2','O3'],default='O3')
args=parser.parse_args()
sln = SimpleNamespace(pi_optimization=args.optimization,build_dir=Path("build"), linux_cc="clang", compiler_launcher=None,
    port_release=True, port_lto="off", port_portable=True, port_pgo="off",
    port_pgo_profile=None, android_ndk="/usr", android_guest_cc="clang")
with open("build-pi.ninja", "w") as out:
    n=Writer(out)
    n.variable("python", sys.executable)
    generate_linux_build(n,sln)
    generate_pi_build(n,sln)
    n.default("pi")
