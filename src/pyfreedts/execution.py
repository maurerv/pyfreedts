"""
Execution backends for parameter screens.
"""

import datetime
import subprocess

from sys import exit
from pathlib import Path
from textwrap import dedent
from typing import List, Dict, Any, Optional


class SnakemakeBackend:
    """Snakemake execution backend for parameter screens."""

    def __init__(
        self,
        runs: List[Dict[str, Any]],
        output_dir: Path,
        dts_args: Optional[str] = None,
        backend_args: Optional[str] = None,
        resources : Optional[Dict] = {},
    ):
        """
        Initialize Snakemake backend.

        Args:
            runs: List of run configurations
            output_dir: Output directory path
            dts_args: Arguments to pass to DTS
            backend_args: Arguments to pass to Snakemake
        """
        try:
            subprocess.run(["snakemake", "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            exit("Error: Snakemake not available. Install with: pip install snakemake")

        self.runs = runs
        self.resources =resources
        self.output_dir = output_dir
        self.dts_args = dts_args or ""
        self.backend_args = backend_args or ""
        self.snakefile_path = self._generate_snakefile()

    def _generate_snakefile(self) -> Path:
        """Generate a Snakefile for the parameter screen."""

        filtered_args = self.dts_args.split()
        try:
            # Remove input file and filename
            input_file = filtered_args.index("-in")
            filtered_args.pop(input_file)
            filtered_args.pop(input_file)
        except Exception:
            pass

        n_threads = 1
        try:
            thread_index = filtered_args.index("-nt")
            n_threads = filtered_args[thread_index + 1]
        except Exception:
            pass

        resource_spec = ",".join({f"{k}={v}" for k,v in self.resources.items()})

        filtered_args = " ".join(filtered_args)
        run_ids = [run["run_id"] for run in self.runs]
        snakefile_content = dedent(
            f'''
            # Auto-generated Snakefile for DTS parameter screen
            # Generated on {datetime.datetime.now().isoformat()}

            import json
            from pathlib import Path

            RUNS = {run_ids}
            OUTPUT_DIR = Path("{self.output_dir}")

            rule all:
                input:
                    expand(str(OUTPUT_DIR / "{{run_id}}" / "completed.flag"), run_id=RUNS)

            # Rule to run DTS for each parameter combination
            rule run_dts:
                input:
                    input_file = str(OUTPUT_DIR / "{{run_id}}" / "input.dts"),
                    params_file = str(OUTPUT_DIR / "{{run_id}}" / "params.json")
                output:
                    flag = str(OUTPUT_DIR / "{{run_id}}" / "completed.flag")
                params:
                    run_dir = str(OUTPUT_DIR / "{{run_id}}"),
                    dts_args = {repr(filtered_args)}
                threads: {n_threads}
                resources: {resource_spec}
                shell:
                    """
                    cd {{params.run_dir}}
                    dts -in input.dts {{params.dts_args}}

                    # Hacky solution at best but dts does not indicate failure for
                    # incorrect arguments as of version 2.1
                    if ls *.res 1> /dev/null 2>&1; then
                        echo "DTS completed successfully - found .res file(s)"
                        touch {{output.flag}}
                    else
                        echo "DTS failed - no .res file found" >&2
                        exit 1
                    fi
                    """
            '''
        ).strip()

        snakefile_path = self.output_dir / "Snakefile"
        with open(snakefile_path, "w") as f:
            f.write(snakefile_content)
        return snakefile_path

    def run(self) -> bool:
        """Execute the Snakemake workflow using CLI with streaming output."""
        cmd = ["snakemake", "-s", str(self.snakefile_path)]
        cmd.append(self.backend_args)
        cmd_str = " ".join([str(x) for x in cmd])

        # I really would prefer using the Python API, but this is easier for now
        process = subprocess.Popen(
            cmd_str,
            shell=True,
            cwd=str(self.output_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        for line in iter(process.stdout.readline, ""):
            print(line, end="")
        return process.wait()


BACKENDS = {
    "snakemake": SnakemakeBackend,
}
