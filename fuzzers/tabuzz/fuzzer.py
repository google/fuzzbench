"""Integration code for TABUZZ (AFL++ Custom Mutator)."""
import os
import shutil
import subprocess
from fuzzers import utils

def build():
    os.environ['CC'] = '/aflplusplus/afl-cc'
    os.environ['CXX'] = '/aflplusplus/afl-cc'
    os.environ['FUZZER_LIB'] = '/fuzzer_lib.a'
    utils.build_benchmark()
    shutil.copy('/aflplusplus/afl-fuzz', os.environ['OUT'])
    shutil.copy('/tabuzz/tabuzz_mutator.so', os.environ['OUT'])

def fuzz(input_corpus, output_corpus, target_binary):
    os.environ['AFL_NO_UI'] = '1'
    os.environ['AFL_SKIP_CPUFREQ'] = '1'
    os.environ['AFL_NO_AFFINITY'] = '1'
    os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
    os.environ['AFL_CUSTOM_MUTATOR_LIBRARY'] = '/out/tabuzz_mutator.so'
    os.environ['AFL_CUSTOM_MUTATOR_ONLY'] = '1'

    command = [
        '/out/afl-fuzz',
        '-i', input_corpus,
        '-o', output_corpus,
        '-m', 'none',
        '-t', '1000+',
        '--',
        target_binary,
        '2147483647',
    ]
    print('[fuzz] Running: ' + ' '.join(command))
    subprocess.run(command, check=False)
