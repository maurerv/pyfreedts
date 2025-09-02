# pyFreeDTS

pyFreeDTS is wrapper for the [FreeDTS C++ project](https://github.com/weria-pezeshkian/FreeDTS) and aims to simplify installing and interfacing with FreeDTS.

## Installation

After ensuring your system satisfies the following requirements

- Python 3.8+
- C++ compiler with C++11 support
- OpenMP (optional)

you can install pyFreeDTS using pip

```bash
pip install pyfreedts
```

## Usage

pyFreeDTS mirrors the original FreeDTS binaries, but changed the spelling to lower-ase to avoid collision

```bash
dts arg1 arg2 ...
cnv arg1 arg2 ...
gen arg1 arg2 ...
```

## Parameter Screening

From version 2.2 onwards, pyFreeDTS simplifies running parameter screens by introducing templated dts files

```
Kappa = {{kappa:25.0:35.0:5.0}} 0 0        # Range: 25.0 to 35.0, step 5.0
Temperature = {{temp:1.0,1.5,2.0}} 0       # List: 1.0, 1.5, 2.0
Method = {{method:MC,MD}} 0                # String list
Set_Steps = 1 {{steps:1000,5000}}          # Integer list
```

A DTS screen based on such a template file can be performed using

```bash
dts_screen \
    -in input_template.dts \
    --output-dir screen_result \
    --dts-args "-top /absolute/path/to/topol.top -seed 12345" \
    --backend-args "-j 4 --keep-going" \
    --dry-run
```
where `--dts-args` are parameters passed to the `dts` executable, and `--backend-args` are parameters passed to the execution backend specified via `--backend`. The default is `snakemake` and can be installed using pip

```bash
pip install snakemake
```

Through snakemake, DTS screens can be run locally and on all commonly available HPC platforms.

> [!TIP]
> The topologies listed in topol.top need to be specified using their absolute path.

Running the pipeline will generate numbered directories in `--output-dir`, each of which contains the result of a DTS run with corresponding params.json. A summary of all parameters and corresponding directories is given by `screen_summary.json` in the specified output directory.

```
screen_result/
├── Snakefile
├── sweep_summary.json
├── run_0001/
│   ├── input.dts
│   ├── params.json
│   ├── dts_*
│   └── completed.flag
└── run_NNNN/
    ├── input.dts
    ├── params.json
    ├── dts_*
    └── completed.flag
```

## For Developers

Clone and install with Poetry:

```bash
git clone https://github.com/maurerv/pyfreedts.git
cd pyfreedts
poetry install
```

Run tests:

```bash
poetry run pytest
```

## License

Like FreeDTS, pyFreeDTS is available under a CC-BY-NC-ND 4.0 International license.
