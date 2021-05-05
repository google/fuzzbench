import os
import shutil
import subprocess

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def build():
    # Set flags to ensure compilation with SymCC
    os.environ['CC'] = "/symcc/build/symcc"
    os.environ['CXX'] = "/symcc/build/sym++"
    os.environ['CFLAGS'] = ""
    os.environ['CXXFLAGS'] = ""
    os.environ['SYMCC_REGULAR_LIBCXX'] = "1"
    os.environ['SYMCC_NO_SYMBOLIC_INPUT'] = "1"
    os.environ['FUZZER_LIB'] = '/libfuzzer-harness.o'

    # Build benchmark
    utils.build_benchmark()

    # Copy over a bunch of the artifacts
    build_directory = os.environ['OUT']
    shutil.copy(
            "/symcc/build//SymRuntime-prefix/src/SymRuntime-build/libSymRuntime.so",
            build_directory)
    shutil.copy(
            "/z3/lib/libz3.so.4.8.7.0",
            os.path.join(build_directory, "libz3.so.4.8"))
    shutil.copy(
            "/symcc/util/min-concolic-exec.sh",
            build_directory)


def fuzz(input_corpus, output_corpus, target_binary):
    os.mkdir("wdir-1")
    
    # Ensure we have a seed
    with open(os.path.join(input_corpus, "symcc-seed1"), "w+") as s1:
        s1.write("A"*100)

    os.environ["THE_OUT_DIR"] = output_corpus

    cmd = []
    cmd.append("./min-concolic-exec.sh")
    cmd.append("-i")
    cmd.append(input_corpus)
    cmd.append("-a")
    cmd.append("./wdir-1")
    cmd.append(target_binary)
    cmd.append("@@")
    
    subprocess.check_call(cmd)
