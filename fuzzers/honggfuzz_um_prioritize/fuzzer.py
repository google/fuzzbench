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
"""Integration code for honggfuzz fuzzer."""

import glob
import os
from pathlib import Path
import random
import shutil
import filecmp
from subprocess import CalledProcessError
import time
import math
import signal
from contextlib import contextmanager

from fuzzers.honggfuzz import fuzzer as honggfuzz_fuzzer
from fuzzers import utils


class TimeoutException(Exception):
    """"Exception thrown when timeouts occur"""


TOTAL_FUZZING_TIME_DEFAULT = 82800  # 23 hours
TOTAL_BUILD_TIME = 43200  # 12 hours
FUZZ_PROP = 0.5
DEFAULT_MUTANT_TIMEOUT = 300
PRIORITIZE_MULTIPLIER = 5
GRACE_TIME = 3600  # 1 hour in seconds
MAX_MUTANTS = 200000
MAX_PRIORITIZE = 30


@contextmanager
def time_limit(seconds):
    """Method to define a time limit before throwing exception"""

    def signal_handler(signum, frame):
        raise TimeoutException("Timed out!")

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


def build():  # pylint: disable=too-many-locals,too-many-statements,too-many-branches
    """Build benchmark."""
    start_time = time.time()

    out = os.getenv("OUT")
    src = os.getenv("SRC")
    work = os.getenv("WORK")
    storage_dir = "/storage"
    os.mkdir(storage_dir)
    mutate_dir = f"{storage_dir}/mutant_files"
    os.mkdir(mutate_dir)
    mutate_bins = f"{storage_dir}/mutant_bins"
    os.mkdir(mutate_bins)
    mutate_scripts = f"{storage_dir}/mutant_scripts"
    os.mkdir(mutate_scripts)
    orig_out = f"{storage_dir}/orig_out"
    os.mkdir(orig_out)

    orig_fuzz_target = os.getenv("FUZZ_TARGET")
    with utils.restore_directory(src), utils.restore_directory(work):
        honggfuzz_fuzzer.build()
        shutil.copy(f"{out}/{orig_fuzz_target}",
                    f"{mutate_bins}/{orig_fuzz_target}")
        os.system(f"cp -r {out}/* {orig_out}/")
    benchmark = os.getenv("BENCHMARK")
    total_fuzzing_time = int(
        os.getenv('MAX_TOTAL_TIME', str(TOTAL_FUZZING_TIME_DEFAULT)))

    source_extensions = [".c", ".cc", ".cpp"]
    num_mutants = math.ceil(
        (total_fuzzing_time * FUZZ_PROP) / DEFAULT_MUTANT_TIMEOUT)
    # Use heuristic to try to find benchmark directory, otherwise look for all
    # files in the current directory.
    subdirs = [
        name for name in os.listdir(src)
        if os.path.isdir(os.path.join(src, name))
    ]
    benchmark_src_dir = src
    for directory in subdirs:
        if directory in benchmark:
            benchmark_src_dir = os.path.join(src, directory)
            break

    source_files = []
    for extension in source_extensions:
        source_files += glob.glob(f"{benchmark_src_dir}/**/*{extension}",
                                  recursive=True)
    random.shuffle(source_files)

    mutants_map = {}
    num_mutants = 0
    for source_file in source_files:
        source_dir = os.path.dirname(source_file).split(src, 1)[1]
        Path(f"{mutate_dir}/{source_dir}").mkdir(parents=True, exist_ok=True)
        os.system(f"mutate {source_file} --mutantDir \
            {mutate_dir}/{source_dir} --noCheck > /dev/null")
        source_base = os.path.basename(source_file).split(".")[0]
        mutants_glob = glob.glob(
            f"{mutate_dir}/{source_dir}/{source_base}.mutant.*")
        mutants = [
            f"{source_dir}/{mutant.split('/')[-1]}"[1:]
            for mutant in mutants_glob
        ]
        num_mutants += len(mutants)
        mutants_map[source_file] = mutants
        if num_mutants > MAX_MUTANTS:
            break

    prioritize_map = {}
    num_prioritized = min(
        math.ceil((num_mutants * PRIORITIZE_MULTIPLIER) / len(mutants_map)),
        MAX_PRIORITIZE)
    for source_file in mutants_map:
        mutants = mutants_map[source_file]
        with open(f"{mutate_dir}/mutants.txt", "w", encoding="utf_8") as f_name:
            f_name.writelines(f"{l}\n" for l in mutants)
        os.system(f"prioritize_mutants {mutate_dir}/mutants.txt \
            {mutate_dir}/prioritize_mutants_sorted.txt {num_prioritized}\
             --noSDPriority --sourceDir {src} --mutantDir {mutate_dir}")
        prioritized_list = []
        with open(f"{mutate_dir}/prioritize_mutants_sorted.txt",
                  "r",
                  encoding="utf_8") as f_name:
            prioritized_list = f_name.read().splitlines()
            prioritize_map[source_file] = prioritized_list

    prioritized_keys = list(prioritize_map.keys())
    random.shuffle(prioritized_keys)
    order = []
    ind = 0
    finished = False

    while not finished:
        finished = True
        for key in prioritized_keys:
            if ind < len(prioritize_map[key]):
                finished = False
                order.append((key, ind))
        ind += 1
    curr_time = time.time()

    # Add grace time for final build at end
    remaining_time = int(TOTAL_BUILD_TIME - (start_time - curr_time) -
                         GRACE_TIME)
    try:
        with time_limit(remaining_time):
            num_non_buggy = 1
            ind = 0
            while ind < len(order):
                with utils.restore_directory(src), utils.restore_directory(
                        work):
                    key, line = order[ind]
                    mutant = prioritize_map[key][line]
                    print(mutant)
                    suffix = "." + mutant.split(".")[-1]
                    mpart = ".mutant." + mutant.split(".mutant.")[1]
                    source_file = f"{src}/{mutant.replace(mpart, suffix)}"
                    print(source_file)
                    print(f"{mutate_dir}/{mutant}")
                    os.system(f"cp {source_file} {mutate_dir}/orig")
                    os.system(f"cp {mutate_dir}/{mutant} {source_file}")
                    try:
                        new_fuzz_target = f"{os.getenv('FUZZ_TARGET')}"\
                            f".{num_non_buggy}"

                        os.system(f"rm -rf {out}/*")
                        honggfuzz_fuzzer.build()
                        if not filecmp.cmp(f'{mutate_bins}/{orig_fuzz_target}',
                                           f'{out}/{orig_fuzz_target}',
                                           shallow=False):
                            print(f"{out}/{orig_fuzz_target}",
                                  f"{mutate_bins}/{new_fuzz_target}")
                            shutil.copy(f"{out}/{orig_fuzz_target}",
                                        f"{mutate_bins}/{new_fuzz_target}")
                            num_non_buggy += 1
                            print(f"FOUND NOT EQUAL {num_non_buggy}, \
                                    ind: {ind}")
                        else:
                            print(f"EQUAL {num_non_buggy}, ind: {ind}")
                    except RuntimeError:
                        pass
                    except CalledProcessError:
                        pass
                    os.system(f"cp {mutate_dir}/orig {source_file}")
                ind += 1
    except TimeoutException:
        pass

    os.system(f"rm -rf {out}/*")
    os.system(f"cp -r {orig_out}/* {out}/")
    os.system(f"cp {mutate_bins}/* {out}/")


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    total_fuzzing_time = int(
        os.getenv('MAX_TOTAL_TIME', str(TOTAL_FUZZING_TIME_DEFAULT)))
    total_mutant_time = int(FUZZ_PROP * total_fuzzing_time)

    mutants = glob.glob(f"{target_binary}.*")
    random.shuffle(mutants)
    timeout = max(DEFAULT_MUTANT_TIMEOUT,
                  int(total_mutant_time / max(len(mutants), 1)))
    num_mutants = min(math.ceil(total_mutant_time / timeout), len(mutants))

    input_corpus_dir = "/storage/input_corpus"
    os.makedirs(input_corpus_dir, exist_ok=True)

    for mutant in mutants[:num_mutants]:
        os.system(f"cp -r {input_corpus_dir}/* {input_corpus}/*")
        with utils.restore_directory(input_corpus), utils.restore_directory(
                output_corpus):
            try:
                with time_limit(timeout):
                    honggfuzz_fuzzer.fuzz(input_corpus, output_corpus, mutant)
            except TimeoutException:
                pass
            except CalledProcessError:
                pass
            os.system(f"cp -r {output_corpus}/* {input_corpus_dir}/*")

    os.system(f"cp -r {input_corpus_dir}/* {input_corpus}/*")
    honggfuzz_fuzzer.fuzz(input_corpus, output_corpus, target_binary)
