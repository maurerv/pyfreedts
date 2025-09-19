"""
Build script for FreeDTS.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pybind11
from pybind11.setup_helpers import Pybind11Extension, build_ext


here = Path(__file__).resolve().parent

SOURCE_DIR = here / "src" / "pyfreedts" / "_cpp" / "dts_src"
CONVERT_DIR = here / "src" / "pyfreedts" / "_cpp" / "dts_convert"
GENERATE_DIR = here / "src" / "pyfreedts" / "_cpp" / "dts_generate"
BIN_DIR = here / "src" / "pyfreedts" / "_bin"


def check_openmp_support(compiler):
    print(f"Checking for OpenMP support with {compiler}...")

    test_file = Path("/tmp/test_openmp.cpp")
    test_file.write_text("#include <omp.h>\nint main() { return 0; }")

    try:
        ret = subprocess.run(
            [compiler, "-fopenmp", str(test_file), "-o", "/dev/null"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if ret.returncode != 0:
            raise OSError(ret.stderr)

        print("OpenMP support detected.")
        return True
    except (subprocess.SubprocessError, OSError):
        print("OpenMP support not detected.")
        return False
    finally:
        if test_file.exists():
            test_file.unlink()


def select_compiler():
    """Select an appropriate C++ compiler."""
    compiler_options = [
        "g++-14",
        "g++-13",
        "g++-12",
        "g++-11",
        "g++-10",
        "g++",
        "clang++-15",
        "clang++-14",
        "clang++-13",
        "clang++",
    ]

    for compiler in compiler_options:
        try:
            result = subprocess.run(
                [compiler, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode == 0:
                print(f"Using compiler: {compiler}")
                print(f"Version: {result.stdout.decode('utf-8').split(chr(10))[0]}")
                return compiler
        except (FileNotFoundError, subprocess.SubprocessError):
            continue

    raise RuntimeError("No suitable C++ compiler found. Please install g++ or clang++.")


def compile_module(source_dir, output_name, compiler, compiler_flags, use_openmp):
    print(f"Compiling {output_name} from directory: {source_dir}")

    os.makedirs(BIN_DIR, exist_ok=True)
    original_dir = os.getcwd()
    os.chdir(source_dir)

    try:
        cpp_files = [f for f in os.listdir(".") if f.endswith(".cpp")]

        if not cpp_files:
            print(f"No cpp files found in {source_dir}")
            return

        openmp_flag = "-fopenmp" if use_openmp else ""
        for cpp_file in cpp_files:
            cmd = [compiler, "-c"]
            cmd.extend(compiler_flags.split())
            if openmp_flag:
                cmd.extend(openmp_flag.split())
            cmd.append(cpp_file)

            print(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

        obj_files = [f for f in os.listdir(".") if f.endswith(".o")]
        output_path = BIN_DIR / output_name

        cmd = [compiler]
        if openmp_flag:
            cmd.extend(openmp_flag.split())
        cmd.extend(["-o", str(output_path)])
        cmd.extend(obj_files)

        print(f"Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        os.chmod(output_path, 0o755)
        print(f"{output_name} compiled successfully and placed in {BIN_DIR}")

    finally:
        os.chdir(original_dir)


def find_cpp_files(directory):
    """Recursively find all .cpp files in a directory."""
    cpp_files = []
    directory = Path(directory)

    if not directory.exists():
        print(f"Warning: Directory {directory} does not exist")
        return cpp_files

    for cpp_file in directory.rglob("*.cpp"):
        cpp_files.append(str(cpp_file))
        print(f"Found C++ source: {cpp_file.relative_to(directory)}")

    return cpp_files


def build(setup_kwargs):
    # Compile standalone modules
    compiler = select_compiler()
    compiler_flags = "-O3 -std=c++11"
    use_openmp = check_openmp_support(compiler)

    if os.path.exists(BIN_DIR):
        shutil.rmtree(BIN_DIR)
    os.makedirs(BIN_DIR, exist_ok=True)

    compile_module(SOURCE_DIR, "DTS", compiler, compiler_flags, use_openmp)
    compile_module(CONVERT_DIR, "CNV", compiler, compiler_flags, use_openmp)
    compile_module(GENERATE_DIR, "GEN", compiler, compiler_flags, use_openmp)

    # Compile bindings
    source_files = find_cpp_files(SOURCE_DIR)
    if not source_files:
        print("Warning: No C++ source files found. Skipping Python bindings.")
        return None

    ext_modules = [
        Pybind11Extension(
            "pyfreedts._core",
            [
                str(here / "src" / "bindings.cpp"),
                *source_files,
            ],
            include_dirs=[
                str(SOURCE_DIR),
                pybind11.get_include(),
            ],
            language="c++",
            define_macros=[
                ("VERSION_INFO", '"dev"'),
            ],
            extra_compile_args=["-O3", "-std=c++11"],
        ),
    ]

    setup_kwargs.update(
        {
            "ext_modules": ext_modules,
            "cmdclass": {"build_ext": build_ext},
            "zip_safe": False,
        }
    )


if __name__ == "__main__":
    build({})
