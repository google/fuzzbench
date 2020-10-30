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
"""Integration code for Kirenenko fuzzer"""
import shutil
import os
import glob
import subprocess
import time
import queue as Q
from fuzzers import utils


def is_benchmark(name):
    "check if benchmark matches"
    benchmark = os.getenv('BENCHMARK', None)
    return benchmark is not None and name in benchmark


def build_afl():
    "build afl binary"
    build_directory = os.environ['OUT']
    os.environ['CC'] = '/afl/afl-clang-fast'
    os.environ['CXX'] = '/afl/afl-clang-fast++'
    os.environ['AFL_LLVM_USE_TRACE_PC'] = '1'
    os.environ['AFL_LLVM_DICT2FILE'] = build_directory + '/afl++.dict'
    env = os.environ.copy()
    build_script = os.path.join(os.environ['SRC'], 'build.sh')
    print("build script path is " + build_script)
    subprocess.check_call(['/bin/bash', '-ex', build_script], env=env)


def build():
    "build benchmark"
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'
    os.environ['LIB_FUZZING_ENGINE'] = '/libAFLDriver.a'
    shutil.copy('/libAFLDriver.a', '/usr/lib/libFuzzingEngine.a')
    build_afl()

    # build Kirenenko
    os.environ['CC'] = '/Kirenenko/bin/ko-clang'
    #os.environ['CXX']='/Kirenenko/bin/ko-clang++'
    os.environ['KO_CC'] = 'clang-6.0'
    #os.environ['KO_CXX']='clang++-6.0'
    os.environ['KO_DONT_OPTIMIZE'] = '1'

    os.remove('/usr/lib/libFuzzingEngine.a')
    #build Kirenenko target
    env = os.environ.copy()

    benchmark = os.getenv('BENCHMARK', None)
    build_script = '/buildScript/' + benchmark + '/buildK.sh'
    subprocess.check_call(['/bin/bash', '-ex', build_script], env=env)

    # build Vanilla
    os.environ['CC'] = 'clang-6.0'
    os.environ['CXX'] = 'clang++-6.0'
    env = os.environ.copy()

    build_script = '/buildScript/' + benchmark + '/buildV.sh'
    subprocess.check_call(['/bin/bash', '-ex', build_script], env=env)

    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def sync_edge(output_corpus, index, q):
    "sync cases from edge"
    print("current Edge queue index " + str(index))
    count = 0
    while True:
        has_new = False
        cur = "id:" + str(index + count).zfill(6)
        for item in glob.glob(output_corpus + '/MQfilter/queue/' + cur + '*'):
            print("add " + item)
            has_new = True
            count = count + 1
            q.put(item)
        if not has_new:
            time.sleep(1)
            break
    return count


def sync_afl(output_corpus, index, q):
    "sync cases from afl"
    print("current AFL queue index " + str(index))
    count = 0
    while True:
        has_new = False
        cur = "id:" + str(index + count).zfill(6)
        for item in glob.glob(output_corpus + '/slave/queue/' + cur + '*'):
            print("add " + item)
            has_new = True
            count = count + 1
            q.put(item)
        if not has_new:
            time.sleep(1)
            break
    return count


def fuzz(input_corpus, output_corpus, target_binary):
    "fuzz loop"

    shutil.copy('/grader/afl-fuzz', os.environ['OUT'] + '/aflgrader')
    shutil.copy('/grader/afl-qemu-trace', os.environ['OUT'])
    utils.create_seed_file_for_empty_corpus(input_corpus)

    edge_index = 0
    afl_index = 0
    session_id = 1
    q = Q.Queue()

    redis_cmd = ['redis-server']
    subprocess.Popen(redis_cmd,
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)

    if not os.path.exists("/out/path/_queue/"):
        os.makedirs("/out/path/_queue/")
    if not os.path.exists("/out/path/_crashes/"):
        os.makedirs("/out/path/_crashes/")

    grader_cmd = [
        'timeout', '10h', '/out/aflgrader', '-Q', '-S', 'MQfilter', '-s',
        '/out/kir_src', '-o', '/out/corpus/', '--', target_binary + '_vani',
        '@@'
    ]
    try:
        subprocess.Popen(grader_cmd,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("something wrong")

# run AFL
    afl_cmd = [
        '/out/afl-fuzz', '-i', '/out/seeds', '-o', '/out/corpus', '-S', 'slave',
        '-m', 'none', '-t', '1000+', '-x', '/out/afl++.dict', '--',
        target_binary, '2147483647'
    ]
    try:
        subprocess.Popen(afl_cmd,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("something wrong")


#input seeds
    files = glob.glob(os.path.join(input_corpus, '*'))
    for item2 in files:
        q.put(item2)

    while True:
        afl_index = afl_index + sync_afl(output_corpus, afl_index, q)
        edge_index = edge_index + sync_edge(output_corpus, edge_index, q)
        if q.empty():
            continue
        item = q.get()
        print(item)
        output_dir = '/out/kir_src/kirenenko-out-' + str(session_id) + '/queue'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        os.environ['TAINT_OPTIONS'] = 'taint_file=' + \
                                item + ' output_dir=' + output_dir
        kir_cmd = ["timeout", "1s", target_binary + '_kir', item]
        try:
            subprocess.call(kir_cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            print("something wrong")
        session_id = session_id + 1
