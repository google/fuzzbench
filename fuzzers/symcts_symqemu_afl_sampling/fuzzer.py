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
from os.path import join, exists, basename, dirname, abspath, realpath
import time
import shutil
import threading
import subprocess
import shutil
import contextlib

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


@contextlib.contextmanager
def with_lukas_afl():
    os.symlink('/afl-lukas', '/afl', target_is_directory=True)
    os.symlink('/libAFLDriver-lukas.a',
               '/libAFLDriver.a',
               target_is_directory=False)

    shutil.copyfile('/afl-base/afl-fuzz', '/afl/afl-fuzz')
    yield

    os.unlink('/afl')
    os.unlink('/libAFLDriver.a')


@contextlib.contextmanager
def link_base_afl(delete=True):
    os.symlink('/afl-base', '/afl', target_is_directory=True)
    os.symlink('/libAFLDriver-base.a',
               '/libAFLDriver.a',
               target_is_directory=False)

    yield

    if delete:
        os.unlink('/afl')
        os.unlink('/libAFLDriver.a')


@contextlib.contextmanager
def restore_env():
    old_env = os.environ.copy()
    yield
    os.environ = old_env


def build_vanilla(build_out, src, work):
    new_env = os.environ.copy()
    new_env['OUT'] = build_out
    new_env['FUZZER_LIB'] = '/out/instrumented/aflpp_driver.o'

    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)


def build_symcc(build_out, src, work):
    new_env = os.environ.copy()

    new_env['CC'] = '/symcc/build/symcc'
    new_env['CXX'] = '/symcc/build/sym++'
    new_env['CXXFLAGS'] = new_env['CXXFLAGS'].replace('-stlib=libc++', '')
    new_env['CXXFLAGS'] += ' -ldl -lm'
    # new_env['SYMCC_EXTRA_CFLAGS'] = '-l:libc_symcc_preload.a'
    # new_env['SYMCC_EXTRA_CXXFLAGS'] = '-l:libc_symcc_preload.a'
    new_env['SYMCC_EXTRA_CFLAGS'] = '-g'
    new_env['SYMCC_EXTRA_LDFLAGS'] = '-L /libs_symcc/ -l:libc_symcc_preload.a'
    new_env['FUZZER_LIB'] = '/libfuzzer-main.o'
    new_env['OUT'] = build_out
    new_env['LIBRARY_PATH'] = new_env.get('LIBRARY_PATH',
                                          '') + ':/libs_symcc/:/libs/'

    new_env['CXXFLAGS'] += ' -fno-sanitize=all '
    new_env['CFLAGS'] += ' -fno-sanitize=all '
    new_env[
        'SYMCC_RUNTIME_DIR'] = '/libs_symcc/'  # SymCC should look for the runtime in the same directory so our copying works
    new_env['LD_LIBRARY_PATH'] = new_env.get('LD_LIBRARY_PATH',
                                             '') + ':/libs_symcc/:/libs/'

    # Setting this environment variable instructs SymCC to use the
    # libcxx library compiled with SymCC instrumentation.
    new_env['SYMCC_LIBCXX_PATH'] = '/libcxx_native_build'

    # Instructs SymCC to consider no symbolic inputs at runtime. This is needed
    # if, for example, some tests are run during compilation of the benchmark.
    new_env['SYMCC_NO_SYMBOLIC_INPUT'] = '1'
    new_env[
        'SYMCC_DISABLE_WRITING'] = '1'  # needed for the symcts runtime to run during tests (missing shmem env vars)

    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)


def get_afl_base_out_dir(build_out) -> str:
    d = os.path.join(build_out, 'instrumented/afl_base')
    # if not exists(d):
    #     os.makedirs(d)
    return d


def get_afl_lukas_out_dir(build_out) -> str:
    d = os.path.join(build_out, 'instrumented/afl_lukas')
    # if not exists(d):
    #     os.makedirs(d)
    return d


def get_symcts_out_dir(build_out) -> str:
    d = os.path.join(build_out, 'instrumented/symcts')
    # if not exists(d):
    #     os.makedirs(d)
    return d


def build():
    shutil.rmtree('/afl/')

    src = os.getenv('SRC')
    work = os.getenv('WORK')
    build_directory = os.getenv('OUT')

    afl_build_out = get_afl_base_out_dir(build_directory)
    afl_lukas_build_out = get_afl_lukas_out_dir(build_directory)
    symcts_build_out = get_symcts_out_dir(build_directory)

    print('Step 1: Building a vanilla version of the benchmark')
    with restore_env():
        build_vanilla(build_directory, src, work)

    print('Step 2: Building with AFL')
    with restore_env():
        with link_base_afl():
            os.environ['OUT'] = afl_build_out
            with utils.restore_directory(src), utils.restore_directory(work):
                # This uses /libAFLDriver.c
                aflplusplus_fuzzer.build('cmplog', 'tracepc', 'dict2file')

    print('Step 2a: Building with AFL (no cmplog) with afl-lukas')
    with restore_env():
        with with_lukas_afl():
            os.system('ls -al / | grep afl')
            os.environ['OUT'] = afl_lukas_build_out
            with utils.restore_directory(src), utils.restore_directory(work):
                aflplusplus_fuzzer.build('tracepc')

    print('Step 3: Completed AFL build')
    # Copy over AFL artifacts needed by SymCC.
    shutil.copy('/afl-base/afl-fuzz', build_directory)
    shutil.copy('/afl-base/afl-showmap', build_directory)

    # Build the SymCC-instrumented target.
    print('Step 4: Building the benchmark with SymCC')
    # Set flags to ensure compilation with SymCC.
    with restore_env():
        build_symcc(symcts_build_out, src, work)


def launch_afl_thread(input_corpus, output_corpus, target_binary,
                      additional_flags):
    """ Simple wrapper for running AFL. """
    afl_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                  args=(input_corpus, output_corpus,
                                        target_binary, additional_flags))
    afl_thread.start()
    return afl_thread


def fuzz(input_corpus, output_corpus, target_binary, with_afl=False):
    """
    Launches an instance of AFL, as well as symcts.
    """

    build_directory = os.getenv('OUT')

    afl_build_out = get_afl_base_out_dir(build_directory)
    afl_lukas_build_out = get_afl_lukas_out_dir(build_directory)
    symcts_build_out = get_symcts_out_dir(build_directory)

    vanilla_target_binary = target_binary
    out_dir = os.path.dirname(target_binary)
    target_binary_name = os.path.basename(target_binary)

    symcts_target_binary = join(symcts_build_out, target_binary_name)
    cmplog_target_binary = join(afl_build_out, 'cmplog', target_binary_name)
    afl_target_binary = join(afl_build_out, target_binary_name)
    afl_lukas_target_binary = join(afl_lukas_build_out, target_binary_name)

    potential_autodict_dir = join(afl_build_out, 'afl++.dict')

    fuzzer = os.environ['FUZZER']

    os.environ['AFL_DISABLE_TRIM'] = '1'

    if 'afl' in fuzzer:

        os.environ['AFL_SKIP_CPUFREQ'] = '1'
        os.environ['AFL_NO_AFFINITY'] = '1'
        os.environ['AFL_NO_UI'] = '1'
        os.environ['AFL_MAP_SIZE'] = '256000'
        os.environ['ASAN_OPTIONS'] = ':detect_leaks=0:abort_on_error=1:symbolize=0'

        flag_cmplog = ['-c', cmplog_target_binary]
        flag_dict = ['-x', potential_autodict_dir] if os.path.exists(potential_autodict_dir) else []
        # sync_flag_master = ['-F', str(Path(output_corpus) / 'symcts' / 'queue')] if 'symcts' in fuzzer else []

        # Start a master and secondary instance of AFL.
        # We need both because of the way SymCC works.
        print('[run_fuzzer] Running %s' % fuzzer)
        afl_fuzzer.prepare_fuzz_environment(input_corpus)

        # Keep  /afl pointing to /afl-base forever..
        with link_base_afl(delete=False):
            pass

        # launch_afl_thread(input_corpus, output_corpus, target_binary,
        #                   flag_cmplog + flag_dict + ['-M', 'afl-main'])
        # time.sleep(2)
        # launch_afl_thread(input_corpus, output_corpus, target_binary,
        #                   flag_cmplog + flag_dict + ['-S', 'havoc'])
        # time.sleep(2)

        launch_afl_thread(input_corpus, output_corpus, afl_target_binary,
                          ['-d'] + flag_dict + flag_cmplog)

    if 'symcts' in fuzzer:  #  for afl_companion, we'd like to only start afl
        symcts_bin = '/out/symcts/symcts'
        if 'sampling' in fuzzer:
            symcts_bin += '-sampling'
        if 'afl' in fuzzer:
            symcts_bin += '-from_other'

        cmd = [
            '/out/run_with_multilog.sh', os.path.join(output_corpus, '.log_symcts'),
            symcts_bin, '-i', input_corpus, '-s', output_corpus, '-n', 'symcts',
            '--symqemu',
            join(out_dir, 'symqemu-x86_64'), '--afl-coverage-target',
            afl_lukas_target_binary, '--vanilla-target', vanilla_target_binary,
            '--symcc-target', symcts_target_binary, '--concolic-execution-mode',
            'symqemu' if 'symqemu' in fuzzer else 'symcc', '--'
        ]

        # Start an instance of SyMCTS.
        # We need to ensure it uses the symbolic version of libc++.
        print('Starting the SyMCTS binary')
        new_environ = os.environ.copy()
        new_environ['LD_LIBRARY_PATH'] = str(get_symcts_out_dir(out_dir))
        new_environ['SYMCTS_INHERIT_STDERR'] = '1'
        new_environ['SYMCTS_INHERIT_STDOUT'] = '1'

        new_environ[
            'RUST_LOG'] = 'generate_mutations_sampled=INFO,symcts_scheduler=INFO'

        print('############ RUNNING: ', ' '.join(cmd))
        os.system('ls -al ' + input_corpus)

        with subprocess.Popen(cmd, env=new_environ):
            pass
