# pyFreeDTS

pyFreeDTS is wrapper for the [FreeDTS C++ project](https://github.com/weria-pezeshkian/FreeDTS) and aims to simplify installing and interfacing with FreeDTS.

## Installation

After ensuring your system satisfies the following requirements

- Python 3.8+
- C++ compiler with C++11 support
- OpenMP (optional),

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

## For Developers

Clone and install with Poetry:

```bash
git clone https://github.com/yourusername/pyfreedts.git
cd pyfreedts
poetry install
```

Run tests:

```bash
poetry run pytest
```

## License

Like FreeDTS, pyFreeDTS is available under a CC-BY-NC-ND 4.0 International license.
