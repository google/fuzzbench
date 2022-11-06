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
"""Integration code for AFLplusplus fuzzer."""

# This optimized afl++ variant should always be run together with
# "aflplusplus" to show the difference - a default configured afl++ vs.
# a hand-crafted optimized one. afl++ is configured not to enable the good
# stuff by default to be as close to vanilla afl as possible.
# But this means that the good stuff is hidden away in this benchmark
# otherwise.

import os
from fuzzers.aflplusplus_muttfuzz import fuzzutil
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    aflplusplus_fuzzer.build()


def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'cmplog')


def check_skip_det_compatible(additional_flags):
    """ Checks if additional flags are compatible with '-d' option"""
    # AFL refuses to take in '-d' with '-M' or '-S' options for parallel mode.
    # (cf. https://github.com/google/AFL/blob/8da80951/afl-fuzz.c#L7477)
    if '-M' in additional_flags or '-S' in additional_flags:
        return False
    return True


def restore_out(input_corpus, output_corpus, crashes_storage):
    """Restores output dir and copies crashes after mutant is done running"""
    os.system(f"rm -rf {input_corpus}/*")
    os.system(
        f"cp {output_corpus}/default/crashes/crashes.*/id* {crashes_storage}/")
    os.system(
        f"cp {output_corpus}/default/crashes/crashes.*/id* {input_corpus}/")
    os.system(f"cp {output_corpus}/default/queue/* {input_corpus}/")
    os.system(f"rm -rf {output_corpus}/*")


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    os.environ['AFL_SKIP_CRASHES'] = "1"
    os.environ['AFL_AUTORESUME'] = "1"
    print(f"{input_corpus} {output_corpus} {target_binary}")

    crashes_storage = "/storage"
    os.makedirs(crashes_storage, exist_ok=True)

    aflplusplus_fuzz_fn = lambda: aflplusplus_fuzzer.fuzz(
        input_corpus, output_corpus, target_binary)

    budget = 86_400
    fraction_mutant = 0.5
    time_per_mutant = 300
    initial_budget = 1_800
    post_mutant_fn = lambda: restore_out(input_corpus, output_corpus,
                                         crashes_storage)
    fuzzutil.fuzz_with_mutants_via_function(aflplusplus_fuzz_fn,
                                            target_binary,
                                            budget,
                                            time_per_mutant,
                                            fraction_mutant,
                                            initial_fn=aflplusplus_fuzz_fn,
                                            initial_budget=initial_budget,
                                            post_initial_fn=post_mutant_fn,
                                            post_mutant_fn=post_mutant_fn)
