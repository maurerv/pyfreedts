"""
Command-line interface for pyFreeDTS.
"""

import sys

from .utils import run_binary

__all__ = ["run_dts", "run_cnv", "run_gen"]


def run_dts():
    """Entry point for the DTS command."""
    sys.exit(run_binary("DTS", sys.argv[1:]))


def run_cnv():
    """Entry point for the CNV command."""
    sys.exit(run_binary("CNV", sys.argv[1:]))


def run_gen():
    """Entry point for the GEN command."""
    sys.exit(run_binary("GEN", sys.argv[1:]))
