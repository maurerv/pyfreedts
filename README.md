# pyFreeDTS

pyFreeDTS is wrapper for the [FreeDTS C++ project](https://github.com/weria-pezeshkian/FreeDTS).

## Prerequisites

- Python 3.8+
- C++ compiler with C++11 support
- OpenMP (optional)

## Installation

```bash
pip install pyfreedts
```

## Usage

The package provides command-line tools that mirror the original FreeDTS binaries, but are in lower-case to avoid collision.

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

Like FreeDTS, pyFreeDTS is available under a CC-BY-NC-ND 4.0 International license