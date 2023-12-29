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
        "wcwidth==0.2.6"
    ]
    for package in packages:
        install(package)


def prepare_build_environment():
    """Set environment variables used to build targets for AFL-based
	fuzzers."""
    os.environ["AFL_CC"] = "gclang"
    os.environ["AFL_CXX"] = "gclang++"

    os.environ["ASAN_OPTIONS"] = "detect_leaks=0"
    os.environ["AFL_USE_ASAN"] = "1"

    os.environ["CC"] = "/fox/afl-clang-fast"
    os.environ["CXX"] = "/fox/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/fox/libAFLDriver.a"
    os.environ["CFLAGS"] = ""
    os.environ["CXXFLAGS"] = ""

    # Fixup a file for mbedtls
    if is_benchmark("mbedtls"):
        file_path = os.path.join(os.getenv("SRC"),
                "mbedtls", "library/CMakeLists.txt")
        assert os.path.isfile(file_path), "The file does not exist"
        # Remove -Wdocumentation to make compilation pass with clang 15.0.7
        subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g' {}".format(file_path)
        subprocess.check_call(subst_cmd, shell = True)

    # Fixup a file for openthread
    if is_benchmark("openthread"):
        mbed_cmake_one = os.path.join(os.getenv("SRC"),
                "openthread/third_party/mbedtls/repo",
                "library/CMakeLists.txt")
        mbed_cmake_two = os.path.join(os.getenv("SRC"),
                "openthread/third_party/mbedtls/repo", "CMakeLists.txt")
        assert os.path.isfile(mbed_cmake_one), "The file does not exist"
        assert os.path.isfile(mbed_cmake_two), "The file does not exist"
        subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g' {}".format(
                mbed_cmake_one)
        subprocess.check_call(subst_cmd, shell = True)
        subst_cmd = r"sed -i 's/\(-Werror\)//g' {}".format(mbed_cmake_two)
        subprocess.check_call(subst_cmd, shell = True)

def build():
    """Build benchmark."""
    is_vanilla = False
    install_all()
    prepare_build_environment()

    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    print("[build 0/2] build target binary")
    src = os.getenv("SRC")
    work = os.getenv("WORK")
    pwd = os.getcwd()

    os.environ["AFL_LLVM_DICT2FILE"] = os.environ["OUT"] + "/keyval.dict"

    # Create personal backups in case
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        try:
            utils.build_benchmark()

            subprocess.check_call([
                "cp", "/dev/shm/br_src_map",
                os.path.join(os.environ["OUT"], "br_src_map")
            ])
            subprocess.check_call([
                "cp", "/dev/shm/strcmp_err_log",
                os.path.join(os.environ["OUT"], "strcmp_err_log")
            ])
            subprocess.check_call([
                "cp", "/dev/shm/instrument_meta_data",
                os.path.join(os.environ["OUT"], "instrument_meta_data")
            ])

            print("[build 1/2] generate metadata")
            # use FUZZ_TARGET env to generate metadata
            env = os.environ.copy()

            fuzz_target = os.path.join(os.environ["OUT"],
                    os.environ["FUZZ_TARGET"])
            subprocess.check_call(["get-bc", fuzz_target], env=env)

            bc_file = fuzz_target + ".bc"
            subprocess.check_call(["llvm-dis-15", bc_file], env=env)

            ll_file = fuzz_target + ".ll"

            os.chdir("/out")
            gen_graph_python = "/fox/gen_graph_dev_no_dot_15.py"
            subprocess.check_call([
                "python3", gen_graph_python, ll_file, fuzz_target,
                "instrument_meta_data"
            ],
                                  env=env)
            os.chdir(pwd)
        except:
            print("[X] Compilation or metadata gen failed..using fallback")
            # Go back to the base dir where the outfiles are being kept
            os.chdir(pwd)
            is_vanilla = True

    if is_vanilla:
        new_env = os.environ.copy()
        new_env["CC"] = "/afl_vanilla/afl-clang-fast"
        new_env["CXX"] = "/afl_vanilla/afl-clang-fast++"
        new_env["FUZZER_LIB"] = "/afl_vanilla/libAFLDriver.a"
        vanilla_build_directory = get_vanilla_build_directory(os.getenv("OUT"))
        os.mkdir(vanilla_build_directory)
        new_env["OUT"] = vanilla_build_directory
        fuzz_target = os.getenv("FUZZ_TARGET")
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(vanilla_build_directory,
                                                  os.path.basename(fuzz_target))
        with utils.restore_directory(src), utils.restore_directory(work):
            utils.build_benchmark(env=new_env)
        shutil.copy(new_env["FUZZ_TARGET"], os.getenv("OUT"))

        # Build the vanilla binary
        new_env["AFL_LLVM_CMPLOG"] = "1"
        cmplog_build_directory = get_cmplog_build_directory(os.getenv("OUT"))
        os.mkdir(cmplog_build_directory)
        new_env["OUT"] = cmplog_build_directory
        fuzz_target = os.getenv("FUZZ_TARGET")
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(cmplog_build_directory,
                                                  os.path.basename(fuzz_target))

        print("Re-building benchmark for CmpLog fuzzing target")
        with utils.restore_directory(src), utils.restore_directory(work):
            utils.build_benchmark(env=new_env)

        # Write a flag file to signal that fox processing failed
        with open(os.path.join(os.getenv("OUT"), "is_vanilla"), "w") as fd:
            pass

    print("[post_build] Copying afl-fuzz to $OUT directory")
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy("/fox/afl-fuzz", os.environ["OUT"])
    shutil.copy("/afl_vanilla/afl-fuzz", os.path.join(os.environ["OUT"],
        "afl-fuzz-vanilla"))


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

    # AFL needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def run_afl_fuzz(input_corpus, output_corpus, target_binary, hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    is_vanilla = False
    dictionary_path = utils.get_dictionary_path(target_binary)
    dictionary_file = "/out/keyval.dict"
    print("[run_afl_fuzz] Running target with afl-fuzz")
    # Check if the fuzzer is to be run in fallback mode or not
    if os.path.exists(os.path.join(os.getenv("OUT"), "is_vanilla")):
        is_vanilla = True
    if not is_vanilla:
        if dictionary_path:
            command = [
                "./afl-fuzz", "-k", "-p", "wd_scheduler", "-i", input_corpus,
                "-o", output_corpus, "-t", "1000+", "-m", "none", "-x",
                dictionary_file, "-x", dictionary_path, "--", target_binary
            ]
        else:
            command = [
                "./afl-fuzz", "-k", "-p", "wd_scheduler", "-i", input_corpus,
                "-o", output_corpus, "-t", "1000+", "-m", "none", "-x",
                dictionary_file, "--", target_binary
            ]
    else:
        # Calculate vanilla binary path from the instrumented target binary.
        # Calculate CmpLog binary path from the instrumented target binary.
        target_binary_directory = os.path.dirname(target_binary)
        vanilla_target_binary_directory = (
            get_vanilla_build_directory(target_binary_directory))
        cmplog_target_binary_directory = (
            get_cmplog_build_directory(target_binary_directory))
        target_binary_name = os.path.basename(target_binary)
        vanilla_target_binary = os.path.join(vanilla_target_binary_directory,
                                        target_binary_name)
        cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)
        if dictionary_path:
            command = [
                "./afl-fuzz-vanilla", "-i", input_corpus, "-o",
                output_corpus, "-t", "1000+", "-m", "none", "-c",
                cmplog_target_binary, "-x", dictionary_file, "-x",
                dictionary_path, "--", vanilla_target_binary
            ]
        else:
            command = [
                "./afl-fuzz-vanilla", "-i", input_corpus, "-o",
                output_corpus, "-t", "1000+", "-m", "none", "-c",
                cmplog_target_binary, "-x", dictionary_file, "--",
                vanilla_target_binary
            ]
    print("[run_afl_fuzz] Running command: " + " ".join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    prepare_fuzz_environment(input_corpus)

    run_afl_fuzz(input_corpus, output_corpus, target_binary)
