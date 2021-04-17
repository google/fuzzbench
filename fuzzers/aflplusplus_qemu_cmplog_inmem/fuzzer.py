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

import os
import subprocess

from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def build():
    """Build benchmark."""
    aflplusplus_fuzzer.build('qemu')


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    # Get LLVMFuzzerTestOneInput address.
    nm_proc = subprocess.run([
        'sh', '-c',
        'nm \'' + target_binary + '\' | grep \'T LLVMFuzzerTestOneInput\''
    ],
                             stdout=subprocess.PIPE,
                             check=True)
    target_func = "0x" + nm_proc.stdout.split()[0].decode("utf-8")
    print('[fuzz] LLVMFuzzerTestOneInput() address =', target_func)

    # Fuzzer option for qemu_mode.
    flags = ['-Q', '-c0']

    os.environ['AFL_QEMU_PERSISTENT_ADDR'] = target_func
    os.environ['AFL_ENTRYPOINT'] = target_func
    os.environ['AFL_QEMU_PERSISTENT_HOOK'] = "/out/aflpp_qemu_driver_hook.so"
    os.environ['AFL_QEMU_PERSISTENT_CNT'] = "100000"
    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=flags)
