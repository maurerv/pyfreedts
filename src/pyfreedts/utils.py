"""
Utility functions for pyFreeDTS.
"""

import os
import subprocess
import sys
import importlib.resources
from pathlib import Path


def get_binary_path(binary_name):
    """
    Get the path to the specified binary using Python's package resource system.
    Args:
        binary_name (str): Name of the binary ('DTS', 'CNV', or 'GEN')
    Returns:
        Path: Path to the binary
    """
    try:
        bin_dir = importlib.resources.files("pyfreedts._bin")
        binary_path = bin_dir / binary_name
        if binary_path.exists():
            return binary_path
    except (ImportError, AttributeError, TypeError):
        # Fallback for older Python versions or if the above method fails
        try:
            import pkg_resources

            binary_path = Path(
                pkg_resources.resource_filename("pyfreedts._bin", binary_name)
            )
            if binary_path.exists():
                return binary_path
        except (ImportError, pkg_resources.DistributionNotFound):
            pass

    module_path = Path(__file__).parent
    binary_path = module_path / "_bin" / binary_name
    if not binary_path.exists():
        raise FileNotFoundError(
            f"Binary {binary_name} not found. Make sure the package is properly installed."
        )
    return binary_path


def run_binary(binary_name, args=None):
    """
    Run the specified binary with the given arguments.
    Args:
        binary_name (str): Name of the binary ('DTS', 'CNV', or 'GEN')
        args (list): List of command-line arguments
    Returns:
        int: Return code of the process
    """
    if args is None:
        args = []

    binary_path = get_binary_path(binary_name)
    os.chmod(binary_path, 0o755)
    cmd = [str(binary_path)] + args
    try:
        process = subprocess.run(cmd, check=True)
        return process.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running {binary_name}: {e}", file=sys.stderr)
        return e.returncode
