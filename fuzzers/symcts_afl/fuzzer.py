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
''' Uses the SymCC-AFL hybrid from SymCC. '''

import os
import time
import shutil
import threading
import subprocess

from fuzzers import utils
from fuzzers.symcts import fuzzer as symcts_fuzzer

def build():
    return symcts_fuzzer.build()

def fuzz(input_corpus, output_corpus, target_binary):
    """
    Launches a master and a secondary instance of AFL, as well as
    the symcts instance.
    """
    return symcts_fuzzer.fuzz(input_corpus, output_corpus, target_binary, with_afl=True)
