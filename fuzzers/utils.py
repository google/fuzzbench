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

import ast
import configparser
import contextlib
import os
import shutil
import subprocess
import tempfile

# Keep all fuzzers at same optimization level until fuzzer explicitly needs or
# specifies it.
DEFAULT_OPTIMIZATION_LEVEL = '-O3'

OSS_FUZZ_LIB_FUZZING_ENGINE_PATH = '/usr/lib/libFuzzingEngine.a'

FILEPATH = os.path.abspath(__file__)


def compile_wrapper_object(env):
    wrapper_filepath = os.path.join(os.path.dirname(FILEPATH), 'wrapper.c')
    wrapper_obj_filepath = os.path.join('/tmp', 'wrapper.o')
    cc = env['CC']
    cflags = env['CFLAGS'].split(' ')
    print(os.path.exists(wrapper_filepath))
    command = [cc] + cflags
    command += ['-c', wrapper_filepath, '-o', wrapper_obj_filepath]
    subprocess.check_call(command, env=env)
    return wrapper_obj_filepath

def wrap_llvmfuzzertestoneinput(env):
    wrapper_obj_filepath = compile_wrapper_object(env)
    wrap_options = f'{wrapper_obj_filepath} -Wl,-wrap=LLVMFuzzerTestOneInput'
    env['FUZZER_LIB'] = env['FUZZER_LIB'] + ' ' + wrap_options


def build_benchmark(env=None):
    """Build a benchmark using fuzzer library."""
    if not env:
        env = os.environ.copy()

    wrap_llvmfuzzertestoneinput(env)
    # Add OSS-Fuzz environment variable for fuzzer library.
    fuzzer_lib = env['FUZZER_LIB']
    env['LIB_FUZZING_ENGINE'] = fuzzer_lib
    if os.path.exists(fuzzer_lib):
        # Make /usr/lib/libFuzzingEngine.a point to our library for OSS-Fuzz
        # so we can build projects that are using -lFuzzingEngine.
        shutil.copy(fuzzer_lib, OSS_FUZZ_LIB_FUZZING_ENGINE_PATH)

    build_script = os.path.join(os.environ['SRC'], 'build.sh')

    benchmark = os.getenv('BENCHMARK')
    fuzzer = os.getenv('FUZZER')
    print('Building benchmark {benchmark} with fuzzer {fuzzer}'.format(
        benchmark=benchmark, fuzzer=fuzzer))
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


@contextlib.contextmanager
def restore_directory(directory):
    """Helper contextmanager that when created saves a backup of |directory| and
    when closed/exited replaces |directory| with the backup.

    Example usage:

    directory = 'my-directory'
    with restore_directory(directory):
       shutil.rmtree(directory)
    # At this point directory is in the same state where it was before we
    # deleted it.
    """
    # TODO(metzman): Figure out if this is worth it, so far it only allows QSYM
    # to compile bloaty.
    if not directory:
        # Don't do anything if directory is None.
        yield
        return
    # Save cwd so that if it gets deleted we can just switch into the restored
    # version without code that runs after us running into issues.
    initial_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as temp_dir:
        backup = os.path.join(temp_dir, os.path.basename(directory))
        shutil.copytree(directory, backup, symlinks=True)
        yield
        shutil.rmtree(directory)
        shutil.move(backup, directory)
        try:
            os.getcwd()
        except FileNotFoundError:
            os.chdir(initial_cwd)


def get_dictionary_path(target_binary):
    """Return dictionary path for a target binary."""
    if get_env('NO_DICTIONARIES'):
        # Don't use dictionaries if experiment specifies not to.
        return None

    dictionary_path = target_binary + '.dict'
    if os.path.exists(dictionary_path):
        return dictionary_path

    options_file_path = target_binary + '.options'
    if not os.path.exists(options_file_path):
        return None

    config = configparser.ConfigParser()
    with open(options_file_path, 'r') as file_handle:
        try:
            config.read_file(file_handle)
        except configparser.Error:
            raise Exception('Failed to parse fuzzer options file: ' +
                            options_file_path)

    for section in config.sections():
        for key, value in config.items(section):
            if key == 'dict':
                dictionary_path = os.path.join(os.path.dirname(target_binary),
                                               value)
                if not os.path.exists(dictionary_path):
                    raise ValueError('Bad dictionary path in options file: ' +
                                     options_file_path)
                return dictionary_path
    return None


def set_default_optimization_flag(env=None):
    """Set default optimization flag if none is already set."""
    if not env:
        env = os.environ

    for flag_var in ['CFLAGS', 'CXXFLAGS']:
        append_flags(flag_var, [DEFAULT_OPTIMIZATION_LEVEL], env=env)


def initialize_flags(env=None):
    """Set initial flags before fuzzer.build() is called."""
    set_no_sanitizer_compilation_flags(env)
    set_default_optimization_flag(env)

    for flag_var in ['CFLAGS', 'CXXFLAGS']:
        print('{flag_var} = {flag_value}'.format(
            flag_var=flag_var, flag_value=os.getenv(flag_var)))


def get_env(env_var, default_value=None):
    """Return the evaluated value of |env_var| in the environment. This is
    a copy of common.environment.get function as fuzzers can't have source
    dependencies outside of this directory."""
    value_string = os.getenv(env_var)

    # value_string will be None if the variable is not defined.
    if value_string is None:
        return default_value

    try:
        return ast.literal_eval(value_string)
    except Exception:  # pylint: disable=broad-except
        # String fallback.
        return value_string


def create_seed_file_for_empty_corpus(input_corpus):
    """Create a fake seed file in an empty corpus, skip otherwise."""
    if os.listdir(input_corpus):
        # Input corpus has some files, no need of a seed file. Bail out.
        return

    print('Creating a fake seed file in empty corpus directory.')
    default_seed_file = os.path.join(input_corpus, 'default_seed')
    with open(default_seed_file, 'w') as file_handle:
        file_handle.write('hi')
