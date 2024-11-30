# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Integration code for FOX fuzzer."""

import os
import shutil
import subprocess
import sys

from fuzzers import utils


def is_benchmark(name):
    """Check if the benchmark contains the string |name|"""
    benchmark = os.getenv("BENCHMARK", None)
    return benchmark is not None and name in benchmark


def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, "cmplog")


def get_vanilla_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, "vanilla")


def install(package):
    """Install Dependencies"""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def install_all():
    """Dependencies"""
    # packages = ["decorator==5.1.1", "ipdb==0.13.13", "ipython==8.12.2",
    # "networkit==10.1", "numpy==1.24.4","pickleshare==0.7.5", "scipy==1.10.1",
    # "tomli==2.0.1"]
    packages = [
        "asttokens==2.2.1", "backcall==0.2.0", "decorator==5.1.1",
        "executing==1.2.0", "greenstalk==2.0.2", "ipdb==0.13.13",
        "ipython==8.12.2", "jedi==0.18.2", "networkit==10.1", "numpy==1.24.4",
        "parso==0.8.3", "pexpect==4.8.0", "pickleshare==0.7.5",
        "prompt-toolkit==3.0.39", "psutil==5.9.5", "ptyprocess==0.7.0",
        "pure-eval==0.2.2", "Pygments==2.15.1", "PyYAML==5.3.1",
        "scipy==1.10.1", "six==1.16.0", "stack-data==0.6.2", "tabulate==0.9.0",
        "tomli==2.0.1", "traitlets==5.9.0", "typing-extensions==4.7.1",
        "wcwidth==0.2.6", "pyelftools==0.30"
    ]
    for package in packages:
        install(package)


def prepare_build_environment():
    """Set environment variables used to build targets for AFL-based
	fuzzers."""

    os.environ["CC"] = "/fox/afl-clang-fast"
    os.environ["CXX"] = "/fox/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/fox/libAFLDriver.a"

    # Fixup a file for mbedtls
    if is_benchmark("mbedtls"):
        file_path = os.path.join(os.getenv("SRC"), "mbedtls",
                                 "library/CMakeLists.txt")
        assert os.path.isfile(file_path), "The file does not exist"
        # Remove -Wdocumentation to make compilation pass with clang 15.0.7
        # subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g' {}".format(file_path)
        subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g'" + " " + file_path
        subprocess.check_call(subst_cmd, shell=True)

    # Fixup a file for openthread
    if is_benchmark("openthread"):
        mbed_cmake_one = os.path.join(os.getenv("SRC"),
                                      "openthread/third_party/mbedtls/repo",
                                      "library/CMakeLists.txt")
        mbed_cmake_two = os.path.join(os.getenv("SRC"),
                                      "openthread/third_party/mbedtls/repo",
                                      "CMakeLists.txt")
        assert os.path.isfile(mbed_cmake_one), "The file does not exist"
        assert os.path.isfile(mbed_cmake_two), "The file does not exist"
        subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g'" + " " + mbed_cmake_one
        subprocess.check_call(subst_cmd, shell=True)
        subst_cmd = r"sed -i 's/\(-Werror\)//g'" + " " + mbed_cmake_two
        subprocess.check_call(subst_cmd, shell=True)


def build_fox_binary():
    """Build fox binary"""

    is_vanilla = False
    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    print("[build 0/2] build target binary")
    src = os.getenv("SRC")
    work = os.getenv("WORK")
    pwd = os.getcwd()

    os.environ["AFL_LLVM_DICT2FILE"] = os.environ["OUT"] + "/keyval.dict"
    os.environ["AFL_LLVM_DICT2FILE_NO_MAIN"] = "1" 

    # Create personal backups in case
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        try:
            utils.build_benchmark()
            
            subprocess.check_call([
                "cp", "/dev/shm/instrument_meta_data",
                os.path.join(os.environ["OUT"], "instrument_meta_data")
            ])

            print("[build 1/2] generate metadata")
            # use FUZZ_TARGET env to generate metadata
            env = os.environ.copy()

            fuzz_target = os.path.join(os.environ["OUT"],
                                       os.environ["FUZZ_TARGET"])

            os.chdir("/out")
            gen_graph_python = "/fox/gen_graph_no_gllvm_15.py"
            subprocess.check_call([
                "python3", gen_graph_python, fuzz_target,
                "instrument_meta_data"
            ],
                                  env=env)
            os.chdir(pwd)
        except subprocess.CalledProcessError:
            print("[X] Compilation or metadata gen failed..using fallback")
            # Go back to the base dir where the outfiles are being kept
            os.chdir(pwd)
            is_vanilla = True
            return is_vanilla

    return is_vanilla

def build():
    """Build benchmark."""
    install_all()
    prepare_build_environment()
    build_fox_binary()

    print("[post_build] Copying afl-fuzz to $OUT directory")
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy("/fox/afl-fuzz", os.environ["OUT"])

def prepare_fuzz_environment(input_corpus):
    """Prepare to fuzz with AFL or another AFL-based fuzzer."""
    # Tell AFL to not use its terminal UI so we get usable logs.
    os.environ["AFL_NO_UI"] = "1"
    # Skip AFL's CPU frequency check (fails on Docker).
    os.environ["AFL_SKIP_CPUFREQ"] = "1"
    # No need to bind affinity to one core, Docker enforces 1 core usage.
    os.environ["AFL_NO_AFFINITY"] = "1"
    # AFL will abort on startup if the core pattern sends notifications to
    # external programs. We don't care about this.
    os.environ["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = "1"
    # Don't exit when crashes are found. This can happen when corpus from
    # OSS-Fuzz is used.
    os.environ["AFL_SKIP_CRASHES"] = "1"
    # Shuffle the queue
    os.environ["AFL_SHUFFLE_QUEUE"] = "1"

    #XXX: Added from aflplusplus
    os.environ["AFL_FAST_CAL"] = "1"
    os.environ["AFL_DISABLE_TRIM"] = "1"
    os.environ["AFL_CMPLOG_ONLY_NEW"] = "1"

    # Allows resuming from an already fuzzed outdir (needed for fox hybrid mode)
    os.environ["AFL_AUTORESUME"] = "1"

    # AFL needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def run_afl_fuzz(input_corpus, output_corpus, target_binary, hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    dictionary_path = utils.get_dictionary_path(target_binary)
    print("[run_afl_fuzz] Running target with afl-fuzz")

    if dictionary_path:
        command = [
            './afl-fuzz',
            '-i',
            input_corpus,
            '-o',
            output_corpus,
            # Use no memory limit as ASAN doesn't play nicely with one.
            '-m',
            'none',
            '-t',
            '1000+',  # Use same default 1 sec timeout, but add '+' to skip hangs.
            "-x", 
            "/out/keyval.dict",
            dictionary_path 
        ]
            
    else:
        command = [
            './afl-fuzz',
            '-i',
            input_corpus,
            '-o',
            output_corpus,
            # Use no memory limit as ASAN doesn't play nicely with one.
            '-m',
            'none',
            '-t',
            '1000+',  # Use same default 1 sec timeout, but add '+' to skip hangs.
            "-x", 
            "/out/keyval.dict" 
        ]
        
    print("[run_afl_fuzz] Running command: " + " ".join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    prepare_fuzz_environment(input_corpus)
    run_afl_fuzz(input_corpus, output_corpus, target_binary)
