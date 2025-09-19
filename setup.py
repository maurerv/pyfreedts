# -*- coding: utf-8 -*-
from setuptools import setup

package_dir = {"": "src"}

packages = ["pyfreedts"]

package_data = {
    "": ["*"],
    "pyfreedts": [
        "_bin/*",
        "_cpp/*",
        "_cpp/dts_convert/*",
        "_cpp/dts_generate/*",
        "_cpp/dts_src/*",
    ],
}

entry_points = {
    "console_scripts": [
        "cnv = pyfreedts.cli:run_cnv",
        "dts = pyfreedts.cli:run_dts",
        "dts_screen = pyfreedts.cli:run_dts_screen",
        "gen = pyfreedts.cli:run_gen",
    ]
}

setup_kwargs = {
    "name": "pyfreedts",
    "version": "2.1.0.post1",
    "description": "Python wrapper for the FreeDTS C++ project",
    "long_description": '# pyFreeDTS\n\npyFreeDTS is wrapper for the [FreeDTS C++ project](https://github.com/weria-pezeshkian/FreeDTS) and aims to simplify installing and interfacing with FreeDTS.\n\n## Installation\n\nAfter ensuring your system satisfies the following requirements\n\n- Python 3.8+\n- C++ compiler with C++11 support\n- OpenMP (optional)\n\nyou can install pyFreeDTS using pip\n\n```bash\npip install pyfreedts\n```\n\n## Usage\n\npyFreeDTS mirrors the original FreeDTS binaries, but changed the spelling to lower-ase to avoid collision\n\n```bash\ndts arg1 arg2 ...\ncnv arg1 arg2 ...\ngen arg1 arg2 ...\n```\n\n## Parameter Screening\n\nFrom version 2.2 onwards, pyFreeDTS simplifies running parameter screens by introducing templated dts files\n\n```\nKappa = {{kappa:25.0:35.0:5.0}} 0 0        # Range: 25.0 to 35.0, step 5.0\nTemperature = {{temp:1.0,1.5,2.0}} 0       # List: 1.0, 1.5, 2.0\nMethod = {{method:MC,MD}} 0                # String list\nSet_Steps = 1 {{steps:1000,5000}}          # Integer list\n```\n\nA DTS screen based on such a template file can be performed using\n\n```bash\ndts_screen \\\n    -in input_template.dts \\\n    --output-dir screen_result \\\n    --dts-args "-top /absolute/path/to/topol.top -seed 12345 -e 100000" \\\n    --backend-args "-j 4 --keep-going" \\\n    --dry-run\n```\nwhere `--dts-args` are parameters passed to the `dts` executable, and `--backend-args` are parameters passed to the execution backend specified via `--backend`. The default is `snakemake` and can be installed using pip\n\n```bash\npip install snakemake\n```\n\nThrough snakemake, DTS screens can be run locally and on all commonly available HPC platforms.\n\n> [!IMPORTANT]\n> The topologies listed in topol.top need to be specified using their absolute path.\n\nRunning the pipeline will generate numbered directories in `--output-dir`, each of which contains the result of a DTS run with corresponding params.json. A summary of all parameters and corresponding directories is given by `screen_summary.json` in the specified output directory.\n\n```\nscreen_result/\n├── Snakefile\n├── sweep_summary.json\n├── run_0001/\n│   ├── input.dts\n│   ├── params.json\n│   ├── dts_*\n│   └── completed.flag\n└── run_NNNN/\n    ├── input.dts\n    ├── params.json\n    ├── dts_*\n    └── completed.flag\n```\n\n> [!IMPORTANT]\n> Every screen needs to run for at least 1000 steps (`-dts-args \'-e 1000\'`), due to an implementation detail in FreeDTS.\n\n## For Developers\n\nClone and install with Poetry:\n\n```bash\ngit clone https://github.com/maurerv/pyfreedts.git\ncd pyfreedts\npoetry install\n```\n\nRun tests:\n\n```bash\npoetry run pytest\n```\n\n## License\n\nLike FreeDTS, pyFreeDTS is available under a CC-BY-NC-ND 4.0 International license.\n',
    "author": "Valentin Maurer",
    "author_email": "valentin.maurer@embl-hamburg.de",
    "maintainer": "None",
    "maintainer_email": "None",
    "url": "None",
    "package_dir": package_dir,
    "packages": packages,
    "package_data": package_data,
    "entry_points": entry_points,
    "python_requires": ">=3.8,<4.0",
}
from build import *

build(setup_kwargs)

setup(**setup_kwargs)
