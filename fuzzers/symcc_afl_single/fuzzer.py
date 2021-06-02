# Copyright 2021 Google LLC
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
''' Uses the SymCC-AFL hybrid from SymCC, although this only
    launches a single AFL instance rather than two. '''

from fuzzers.symcc_afl import fuzzer as symcc_afl_fuzzer


def build():
    """ Build an AFL version and SymCC version of the benchmark """
    symcc_afl_fuzzer.build()


def fuzz(input_corpus, output_corpus, target_binary):
    """ Launch a SymCC with a single AFL instance. """
    symcc_afl_fuzzer.fuzz(input_corpus, output_corpus, target_binary, True)
