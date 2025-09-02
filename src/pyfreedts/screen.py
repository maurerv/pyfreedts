"""
Parameter screen functionality for pyFreeDTS.
"""

import re
import json
import argparse
from itertools import product

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

from .execution import BACKENDS


class ParameterParser:
    """Parse parameter definitions from template files."""

    PARAM_PATTERN = re.compile(r"\{\{(\w+):([^}]+)\}\}")

    @classmethod
    def parse_template(
        cls, template_content: str
    ) -> Tuple[str, Dict[str, List[float]]]:
        """
        Parse a template file and extract parameter definitions.

        Args:
            template_content: Content of the template file

        Returns:
            Tuple of (template_with_placeholders, parameter_definitions)
        """
        parameters = {}

        def replace_param(match):
            param_name = match.group(1)
            param_def = match.group(2)

            # Parse parameter definition
            param_values = cls._parse_parameter_definition(param_def)
            parameters[param_name] = param_values

            # Replace with simple placeholder for later substitution
            return f"{{{param_name}}}"

        template_processed = cls.PARAM_PATTERN.sub(replace_param, template_content)
        return template_processed, parameters

    @classmethod
    def _parse_parameter_definition(cls, param_def: str) -> List[float]:
        """
        Parse a single parameter definition.

        Supports:
        - Range: "start:end:step" -> [start, start+step, ..., end]
        - List: "val1,val2,val3" -> [val1, val2, val3]
        """
        if ":" in param_def:
            # Range definition: start:end:step
            parts = param_def.split(":")
            if len(parts) != 3:
                raise ValueError(
                    f"Range definition must have format 'start:end:step', got: {param_def}"
                )

            try:
                start, end, step = map(float, parts)
            except ValueError:
                raise ValueError(f"Invalid range values in: {param_def}")

            if step <= 0:
                raise ValueError(f"Step size must be positive, got: {step}")

            # Generate range values
            values = []
            current = start
            while current <= end + 1e-10:
                values.append(current)
                current += step
            return values

        elif "," in param_def:
            # List definition: val1,val2,val3
            try:
                return [x.strip() for x in param_def.split(",")]
            except ValueError:
                raise ValueError(f"Invalid list values in: {param_def}")
        else:
            return [param_def.strip()]


class ScreenGenerator:
    """Generate parameter combinations and file structure for screens."""

    def __init__(self, template_file: Path, output_dir: Path):
        self.output_dir = output_dir
        self.template_content = None
        self.parameters = {}

        with open(template_file, "r") as f:
            template_content = f.read()

        self.template_content, self.parameters = ParameterParser.parse_template(
            template_content
        )

        if not self.parameters:
            raise ValueError("No parameters found in template file")

        self.template_file = template_file

    def _generate_parameter_combinations(self) -> List[Dict[str, float]]:
        """Generate all parameter combinations."""
        # Sort parameter names for consistent ordering
        param_names = sorted(self.parameters.keys())
        param_values = [self.parameters[name] for name in param_names]

        combinations = []
        for combo in product(*param_values):
            param_dict = dict(zip(param_names, combo))
            combinations.append(param_dict)

        return combinations

    def _substitute_parameters(self, params: Dict[str, float]) -> str:
        """Substitute parameter values into template."""
        content = self.template_content
        for param_name, value in params.items():
            placeholder = f"{{{param_name}}}"
            content = content.replace(placeholder, str(value))
        return content

    def setup(self):
        """Setup parameter screen directory"""
        combinations = self._generate_parameter_combinations()
        runs = self._create_run_directories(combinations)
        self._create_summary_metadata(runs)

    def _create_run_directories(
        self, combinations: List[Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """Create run directories and metadata."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # This is a simplification for now. We could think about creating directory names
        # as hexdigest of the parameter combination to avoid potential collisions
        total_runs = len(combinations)
        width = min(len(str(total_runs)), 4)

        runs = []
        for i, params in enumerate(combinations, 1):
            run_id = f"run_{i:0{width}d}"
            run_dir = self.output_dir / run_id
            run_dir.mkdir(exist_ok=True)

            input_content = self._substitute_parameters(params)
            input_file = run_dir / "input.dts"
            with open(input_file, "w") as f:
                f.write(input_content)

            params_file = run_dir / "params.json"
            with open(params_file, "w") as f:
                json.dump(params, f, indent=2)

            run_info = {
                "run_id": run_id,
                "run_dir": str(run_dir),
                "parameters": params,
                "input_file": str(input_file),
            }
            runs.append(run_info)

        return runs

    def _create_summary_metadata(self, runs: List[Dict[str, Any]]):
        """Create master summary file."""
        summary = {
            "template_file": str(self.template_file),
            "generated_at": datetime.now().isoformat(),
            "total_runs": len(runs),
            "parameters": sorted(self.parameters.keys()),
            "parameter_ranges": {
                name: {
                    "values": values,
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                }
                for name, values in self.parameters.items()
            },
            "runs": [
                {"run_id": run["run_id"], "parameters": run["parameters"]}
                for run in runs
            ],
        }

        summary_file = self.output_dir / "screen_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)


def _parse_key_value_str(value : str) -> Dict:
    ret = {}
    if value is None:
        return ret
    value = value.strip()
    for item in value.split(','):
        if '=' in item:
            key, value = item.split('=', 1)
            ret[key] = value
    return ret

def main():
    """CLI entry point for DTS parameter screen."""
    parser = argparse.ArgumentParser(
        description="Run DTS parameter screen using template files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-in",
        required=True,
        dest="template_file",
        help="Template input.dts file with parameter definitions",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for screen results",
    )
    parser.add_argument(
        "--backend",
        default="snakemake",
        choices=list(BACKENDS.keys()),
        help="Execution backend to use",
    )
    parser.add_argument(
        "--backend-args",
        type=str,
        default="",
        help="Arguments to pass to the backend in quotes (e.g., '-j 8 --quiet')",
    )
    parser.add_argument(
        "--dts-args",
        type=str,
        default="",
        help="Additional arguments to pass to DTS in quotes (e.g., '-top topology.top')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Test program until workflow execution",
    )
    parser.add_argument(
        "--resources",
        default="",
        help="Resource specifications for cluster execution in KEY=VALUE format (e.g., \"mem_mb=4000,runtime=120\")",
    )

    args = parser.parse_args()
    template_path = Path(args.template_file).absolute()
    output_path = Path(args.output_dir).absolute()

    ScreenGenerator(template_path, output_path).setup()
    summary_file = output_path / "screen_summary.json"
    with open(summary_file, "r") as f:
        summary = json.load(f)

    backend_class = BACKENDS[args.backend]
    executor = backend_class(
        runs=summary["runs"],
        output_dir=output_path,
        dts_args=args.dts_args,
        backend_args=args.backend_args,
        resources=_parse_key_value_str(args.resources)
    )
    if not args.dry_run:
        return executor.run()
