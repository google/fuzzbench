"""Integration code for ddisasm based AFLplusplus fuzzer"""

import os
import shutil
import subprocess
from fuzzers import utils

# This command doesn't work in Dockerfile
subprocess.run([
    'pip3',
    'install',
    'gtirb',
], check=True)

import gtirb


def parse_libs(lib):
    """
        Given a library name, transforms it to be used as linker flag.

        Parameters
        ----------
        lib : str

        Returns
        -------
        result : str

        Examples
        --------
        >>> parse_libs('libpthread.so.0')
        '-lpthread'

    """
    lib_name = lib.split('.', 1)[0]
    if 'lib' in lib_name[:3]:
        result = '-l' + lib_name[3:]
    else:
        raise ValueError('Invalid library name')
    return result


def extract_libs(target_gtirb):
    """
        Given a gtirb file name, returns the libraries that the original binary 
        depends on.

        Parameters
        ----------
        target_gtirb : str

        Returns
        -------
        result : list

        Examples
        --------
        >>> extract_libs('file.gtirb')
        ['-lmagic', '-lc', '-llzma', '-lbz2', '-lz']

    """
    ir = gtirb.IR.load_protobuf(target_gtirb)
    libs = ir.modules[0].aux_data['libraries'].data
    result = []
    for i in libs:
        result.append(parse_libs(i))
    return result


def create_assembler(target_gtirb):
    """
        Given a gtirb file name, returns the shell script required to assemble
        the assembly source file with instrumentation.

        Parameters
        ----------
        target_gtirb : str

        Returns
        -------
        text : str

    """
    tab = '\t'
    text = f"""#!/bin/bash
#
# Run afl-as to assemble with AFL instrumentation.
#
set -ex

SOURCE=$(readlink -f $1); shift
TARGET=$(readlink -f $1); shift

AS_FLAGS=$(echo $TARGET | grep -q 'results/x86\.' && echo "--32" ||echo "")

sed 's/^\.text$/{tab}.text/' -i $SOURCE
sed 's/^\s\{{1,\}}/{tab}/' -i $SOURCE

temp_dir=$(mktemp -d)
pushd $temp_dir
AFL_AS_FORCE_INSTRUMENT=1 AFL_KEEP_ASSEMBLY=1 /src/afl/afl-as $AS_FLAGS $SOURCE
gcc -no-pie a.out $@ -o $TARGET {' '.join(extract_libs(target_gtirb))}

popd
rm -r $temp_dir
    
"""
    return text


def build_uninstrumented_benchmark():
    """
    Block of code to build a binary without instrumentation. Takes and returns
    no values.
    """
    # Setting environment variables.
    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['CFLAGS'] = ' '.join(utils.NO_SANITIZER_COMPAT_CFLAGS)
    cxxflags = [utils.LIBCPLUSPLUS_FLAG] + utils.NO_SANITIZER_COMPAT_CFLAGS
    os.environ['CXXFLAGS'] = ' '.join(cxxflags)
    os.environ['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'
    fuzzing_engine_path = '/usr/lib/libFuzzingEngine.a'
    shutil.copy(os.environ['FUZZER_LIB'], fuzzing_engine_path)
    env = os.environ.copy()

    # Build the benchmark without instrumentation.
    build_script = os.path.join(os.environ['SRC'], 'build.sh')
    subprocess.check_call(
        ['/bin/bash', '-ex', build_script],
        env=env,
    )


def instrument_binary():
    """
    Block of code to instrument a binary without source. Takes and returns no
    values.
    """
    # Name initialisation
    target_binary = os.getenv('FUZZ_TARGET')
    target_gtirb = target_binary + '.gtirb'
    target_assembly = target_binary + '.s'
    instrumented_binary = target_binary + '.dafl'

    # ddisasm pipeline
    subprocess.run([
        'ddisasm',
        os.environ['OUT'] + '/' + target_binary,
        '--ir',
        target_gtirb,
    ],
                   check=True)
    subprocess.run([
        'gtirb-pprinter',
        target_gtirb,
        '--syntax',
        'att',
        '--asm',
        target_assembly,
    ],
                   check=True)

    assembler = '/src/fuzzers/aflplusplus_ddisasm/assemble.sh'
    with open(assembler, 'w') as file:
        file.write(create_assembler(target_gtirb))

    os.chmod(assembler, 0o777)
    subprocess.run([assembler, target_assembly, instrumented_binary],
                   check=True)
    shutil.copy(instrumented_binary, os.environ['OUT'])


def build():
    """
    Build benchmark and copy fuzzer to $OUT.
    """
    build_uninstrumented_benchmark()
    instrument_binary()
    shutil.copy('/src/afl/afl-fuzz', os.environ['OUT'])


def prepare_fuzz_environment(input_corpus):
    """
    Prepare to fuzz with AFL or another AFL-based fuzzer.
    """
    # Tell AFL to not use its terminal UI so we get usable logs.
    os.environ['AFL_NO_UI'] = '1'
    # Skip AFL's CPU frequency check (fails on Docker).
    os.environ['AFL_SKIP_CPUFREQ'] = '1'
    # No need to bind affinity to one core, Docker enforces 1 core usage.
    os.environ['AFL_NO_AFFINITY'] = '1'
    # AFL will abort on startup if the core pattern sends notifications to
    # external programs. We don't care about this.
    os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
    # Don't exit when crashes are found. This can happen when corpus from
    # OSS-Fuzz is used.
    os.environ['AFL_SKIP_CRASHES'] = '1'
    # Shuffle the queue
    os.environ['AFL_SHUFFLE_QUEUE'] = '1'
    # AFL needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def fuzz(input_corpus, output_corpus, target_binary):
    """
    Run fuzzer.

    Arguments:
      input_corpus: Directory containing the initial seed corpus for
                    the benchmark.
      output_corpus: Output directory to place the newly generated corpus
                     from fuzzer run.
      target_binary: Absolute path to the fuzz target binary.
    """

    prepare_fuzz_environment(input_corpus)
    instrumented_binary = target_binary + '.dafl'

    subprocess.call([
        './afl-fuzz', '-i', input_corpus, '-o', output_corpus, '--',
        instrumented_binary, '@@'
    ])
