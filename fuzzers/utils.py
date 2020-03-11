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
"""Utility functions for running fuzzers."""

import os
import shutil
import subprocess

OSS_FUZZ_LIB_FUZZING_ENGINE_PATH = '/usr/lib/libFuzzingEngine.a'


def build_benchmark(env=None):
    """Build a benchmark using fuzzer library."""
    if not env:
        env = os.environ.copy()

    # Add OSS-Fuzz environment variable for fuzzer library.
    fuzzer_lib = env['FUZZER_LIB']
    env['LIB_FUZZING_ENGINE'] = fuzzer_lib
    if os.path.exists(fuzzer_lib):
        # Make /usr/lib/libFuzzingEngine.a point to our library for OSS-Fuzz
        # so we can build projects that are using -lFuzzingEngine.
        shutil.copy(fuzzer_lib, OSS_FUZZ_LIB_FUZZING_ENGINE_PATH)

    if os.getenv('OSS_FUZZ'):
        build_script = os.path.join(os.environ['SRC'], 'build.sh')
    else:
        build_script = os.path.join('benchmark', 'build.sh')

    print('Building benchmark')
    subprocess.check_call(['/bin/bash', '-ex', build_script], env=env)


def append_flags(env_var, additional_flags, env=None):
    """Append |additional_flags| to those already set in the value of |env_var|
    and assign env_var to the result."""
    if env is None:
        env = os.environ
    flags = env.get(env_var, '').split(' ')
    flags.extend(additional_flags)
    env[env_var] = ' '.join(flags)


# Use these flags when compiling benchmark code without a sanitizer (e.g. when
# using eclipser). This is necessary because many OSS-Fuzz targets cannot
# otherwise be compiled without a sanitizer because they implicitly depend on
# libraries linked into the sanitizer runtime. These flags link against those
# libraries.
NO_SANITIZER_COMPAT_CFLAGS = [
    '-pthread', '-Wl,--no-as-needed', '-Wl,-ldl', '-Wl,-lm',
    '-Wno-unused-command-line-argument'
]
NO_SANITIZER_COMPAT_CXXFLAGS = ['-stdlib=libc++'] + NO_SANITIZER_COMPAT_CFLAGS



def set_no_sanitizer_compilation_flags(env=None):
    """Set compilation flags (CFLAGS and CXXFLAGS) in |env| so that a benchmark
    can be compiled without a sanitizer. If |env| is not provided, the program's
    environment will be used."""
    if env is None:
        env = os.environ
    env['CFLAGS'] = ' '.join(NO_SANITIZER_COMPAT_CFLAGS)
    env['CXXFLAGS'] = ' '.join(NO_SANITIZER_COMPAT_CXXFLAGS)
