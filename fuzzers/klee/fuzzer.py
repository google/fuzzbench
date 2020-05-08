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
"""Integration code for AFL fuzzer."""

import shutil
import os
import glob
import struct
import subprocess

from fuzzers import utils


def prepare_build_environment():
    """Set environment variables used to build benchmark."""

    # See https://klee.github.io/tutorials/testing-function/
    cflags = ['-O0', '-Xclang', '-disable-O0-optnone']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['LLVM_CC_NAME'] = 'clang-6.0'
    os.environ['LLVM_CXX_NAME'] = 'clang++-6.0'
    os.environ['LLVM_AR_NAME'] = 'llvm-ar-6.0'
    os.environ['LLVM_LINK_NAME'] = 'llvm-link-6.0'
    os.environ['LLVM_COMPILER'] = 'clang'
    os.environ['CC'] = 'gclang'
    os.environ['CXX'] = 'gclang++'

    os.environ['FUZZER_LIB'] = '/libAFL.a -L/ -lKleeMock -lpthread'


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    out_dir = os.environ['OUT']
    fuzz_target = os.path.join(out_dir, 'fuzz-target')
    getbc_cmd = "get-bc {target}".format(target=fuzz_target)
    if os.system(getbc_cmd) != 0:
        raise ValueError("get-bc failed")


def rmdir(path):
    """"Remove a directory recursively"""
    if os.path.isdir(path):
        shutil.rmtree(path)


def emptydir(path):
    """Empty a directory"""
    rmdir(path)
    os.mkdir(path)


def run(command, hide_output=False, ulimit_cmd=None):
    """Run the command |command|, optionally, run |ulimit_cmd| first."""
    cmd = ' '.join(command)
    print('[run_cmd] {}'.format(cmd))

    output_stream = subprocess.DEVNULL if hide_output else None
    if ulimit_cmd:
        ulimit_command = [ulimit_cmd + ';']
        ulimit_command.extend(command)
        print('[ulimit_command] {}'.format(' '.join(ulimit_command)))
        ret = subprocess.call(' '.join(ulimit_command),
                              stdout=output_stream,
                              stderr=output_stream,
                              shell=True)
    else:
        ret = subprocess.call(command,
                              stdout=output_stream,
                              stderr=output_stream)
    if ret != 0:
        raise ValueError("command failed: {ret} - {cmd}".format(ret=ret,
                                                                cmd=cmd))


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    # Set ulimit. Note: must be changed as this does not take effect
    if os.system("ulimit -s unlimited") != 0:
        raise ValueError("ulimit failed")

    # Convert corpus files to KLEE .ktest format
    out_dir = os.path.dirname(target_binary)
    input_klee = os.path.join(out_dir, "seeds_klee")
    output_klee = os.path.join(out_dir, "output_klee")
    crash_dir = os.path.join(output_corpus, "crashes")
    queue_dir = os.path.join(output_corpus, "queue")
    info_dir = os.path.join(output_corpus, "info")
    emptydir(crash_dir)
    emptydir(queue_dir)
    emptydir(info_dir)
    emptydir(input_klee)
    rmdir(output_klee)

    # We put the file data into the symbolic buffer,
    # and the model_version set to 1 for uc-libc
    symbolic_buffer = "KleeInputBuf"
    model_version = "model_version"
    model = struct.pack('@i', 1)
    ktest_tool = os.path.join(out_dir, "bin/ktest-tool")
    files = glob.glob(os.path.join(input_corpus, "*"))
    n_converted = 0

    print('[run_fuzzer] Converting seed files...')

    for seedfile in files:
        if ".ktest" in seedfile:
            continue

        if not os.path.isfile(seedfile):
            continue

        if os.path.getsize(seedfile) > 4096:
            continue

        seed_in = "{seed}.ktest".format(seed=seedfile)
        seed_out = os.path.join(input_klee, os.path.basename(seed_in))

        # Create file for symblic buffer
        input_file = "{seed}.ktest.{symbolic}".format(seed=seedfile,
                                                      symbolic=symbolic_buffer)
        output_kfile = "{seed}.ktest".format(seed=seedfile)
        shutil.copyfile(seedfile, input_file)
        os.rename(seedfile, input_file)

        # Create file for mode version
        model_input_file = "{seed}.ktest.{symbolic}".format(
            seed=seedfile, symbolic=model_version)
        with open(model_input_file, 'wb') as mfile:
            mfile.write(model)

        # Run conversion tool
        convert_cmd = [
            ktest_tool, 'create', output_kfile, '--args', seed_out, '--objects',
            model_version, symbolic_buffer
        ]

        run(convert_cmd)

        # Move the resulting file to klee corpus dir
        os.rename(seed_in, seed_out)

        n_converted += 1

    print('[run_fuzzer] Converted {converted} seed files'.format(
        converted=n_converted))

    # Run KLEE
    # Option -only-output-states-covering-new makes
    # dumping ktest files faster.
    # New coverage means a new edge.
    # See lib/Core/StatsTracker.cpp:markBranchVisited()

    print('[run_fuzzer] Running target with klee')

    klee_bin = os.path.join(out_dir, "bin/klee")
    target_binary_bc = "{}.bc".format(target_binary)
    seconds = int(int(os.getenv('MAX_TOTAL_TIME', 246060)) * 4 / 5)

    seeds_option = ['-zero-seed-extension', '-seed-dir', input_klee
                   ] if n_converted > 0 else []

    klee_cmd = [
        klee_bin, '--optimize', '-max-solver-time', '30s',
        '-log-timed-out-queries', '--max-time', '{}s'.format(seconds), '-libc',
        'uclibc', '-libcxx', '-posix-runtime',
        '-only-output-states-covering-new', '-output-dir', output_klee
    ]

    if seeds_option:
        klee_cmd.extend(seeds_option)

    klee_cmd += [target_binary_bc]
    run(klee_cmd, ulimit_cmd="ulimit -s unlimited")

    # Convert the output .ktest to binary format
    print('[run_fuzzer] Converting output files...')

    n_converted = 0
    n_crashes = 0

    files = glob.glob(os.path.join(output_klee, "*.ktest"))
    for kfile in files:
        convert_cmd = [
            ktest_tool, 'extract', kfile, '--objects', symbolic_buffer
        ]

        run(convert_cmd)

        # And copy the resulting file in output_corpus
        ktest_fn = os.path.splitext(kfile)[0]
        file_in = '{file}.{symbuf}'.format(file=kfile, symbuf=symbolic_buffer)
        file_out = os.path.join(queue_dir, os.path.basename(ktest_fn))
        os.rename(file_in, file_out)

        # Check if this is a crash
        crash_regex = os.path.join(output_klee,
                                   "{fn}.*.err".format(fn=ktest_fn))
        crashes = glob.glob(crash_regex)
        if len(crashes) == 1:
            crash_out = os.path.join(crash_dir, os.path.basename(ktest_fn))
            shutil.copy(file_out, crash_out)
            info_in = crashes[0]
            info_out = os.path.join(info_dir, os.path.basename(info_in))
            shutil.copy(info_in, info_out)
            n_crashes += 1

        n_converted += 1

    print('[run_fuzzer] Converted {converted} output files'.format(
        converted=n_converted))
    print('[run_fuzzer] Found {crashed} crash files'.format(crashed=n_crashes))

    # For sanity check, we write a file to ensure
    # KLEE was able to terminate and convert all files
    done_file = os.path.join(output_corpus, "DONE")
    with open(done_file, 'w') as file:
        file.write("Converted: {converted}\nBugs: {bugs}".format(
            converted=n_converted, bugs=n_crashes))
