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
"""Integration code for pathAFL fuzzer."""

import os
import shutil
import subprocess
from fuzzers import utils


def prepare_build_environment():
    """Set environment variables used to build targets for pathAFL-based
    fuzzers."""
    os.environ['LD_LIBRARY_PATH'] = '/path-afl'
    os.environ['CC'] = '/path-afl/afl-clang-fast'
    os.environ['CXX'] = '/path-afl/afl-clang-fast++'
    current_directory = os.getcwd()
    os.environ["BBIDFILE"] = os.path.join(current_directory, "bbid.txt")
    os.environ["CALLMAPFILE"] = os.path.join(current_directory, "callmap.txt")
    os.environ["CFGFILE"] = os.path.join(current_directory, "cfg.txt")
    os.environ["FUZZER"] = '/path-afl'
    os.environ["AFL_LLVM_CALLER"] = '1'
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    subprocess.run('cat cfg.txt | grep "BasicBlock: " | wc -l > bbnum.txt',
                   shell=True,
                   check=True)
    print(f"/out/{os.getenv('FUZZ_TARGET')}")
    result = subprocess.run([
        "bash", '/path-afl/fuzzing_support/filterCFGandCallmap.sh',
        f"/out/{os.getenv('FUZZ_TARGET')}"
    ],
                            check=False,
                            capture_output=True,
                            text=True)
    print(result.stdout)
    print(result.stderr)
    subprocess.run(
        'cat cfg_filtered.txt | grep \"Function: \" | nl -v 0 | awk \'{print $1, $3, $4, $5, $6, $7, $8, $9}\' > function_list.txt',
        shell=True,
        check=True)
    subprocess.run(
        'g++ -I/path-afl/fuzzing_support /path-afl/fuzzing_support/convert.cpp -o convert',
        shell=True,
        check=True)
    subprocess.run('./convert', shell=True, check=True)

    print('[post_build] Copying afl-fuzz to $OUT directory')

    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/path-afl/libpath_reduction.so', os.environ['OUT'])
    shutil.copy('/path-afl/afl-fuzz', os.environ['OUT'])
    shutil.copy('./top.bin', os.environ['OUT'])
    shutil.copy('/libpython3.8.so.1.0', os.environ['OUT'])
    try:
        src = '/usr/lib/llvm-17/lib'
        dst = os.environ['OUT']
        shutil.copytree(src, dst, dirs_exist_ok=True)
    except KeyError:
        print("Environment variable 'OUT' is not set.")
        assert False
    except FileNotFoundError as e:
        print(f"Source directory not found: {e}")
        assert False
    except PermissionError as e:
        print(f"Permission error: {e}")
        assert False
    except Exception as e:
        print(f"An error occurred: {e}")
        assert False


def prepare_fuzz_environment(input_corpus):
    """Prepare to fuzz with AFL or another AFL-based fuzzer."""
    # Tell AFL to not use its terminal UI so we get usable logs.
    os.environ['AFL_NO_UI'] = '1'
    # Skip AFL's CPU frequency check (fails on Docker).
    os.environ['AFL_SKIP_CPUFREQ'] = '1'
    # No need to bind affinity to one core, Docker enforces 1 core usage.
    os.environ['AFL_NO_AFFINITY'] = '1'
    # AFL will abort on startup if the core pattern sends notifications to
    # external programs. We don't care about this.
    os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
    # Don't exit when crashes are found. This can happen when corpus from
    # OSS-Fuzz is used.
    os.environ['AFL_SKIP_CRASHES'] = '1'
    # Shuffle the queue
    os.environ['AFL_SHUFFLE_QUEUE'] = '1'
    os.environ['CFG_BIN_FILE'] = './top.bin'
    os.environ[
        'LD_LIBRARY_PATH'] = f'./lib:{os.getcwd()}:{os.environ["LD_LIBRARY_PATH"]}'

    # AFL needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def run_afl_fuzz(input_corpus,
                 output_corpus,
                 target_binary,
                 additional_flags=None,
                 hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    print('[run_afl_fuzz] Running target with afl-fuzz')
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
    ]
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    print('[run_afl_fuzz] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    prepare_fuzz_environment(input_corpus)

    os.environ['K'] = '42'

    run_afl_fuzz(input_corpus, output_corpus, target_binary)
