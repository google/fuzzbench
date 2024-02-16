# BandFuzz
# Author: Wenxuan (wenxuan.shi@northwestern.edu, shiwx.org)

import os
import shutil
import subprocess

def build():
    env = os.environ.copy()
    src_folder = env['SRC']
    out_folder = os.path.join(env['OUT'], 'target')
    build_script = os.path.join(src_folder, 'build.sh')
    benchmark = os.getenv('BENCHMARK')
    fuzzer = os.getenv('FUZZER')

    # Run bf-cc to build the benchmark
    print(f'Building benchmark {benchmark} with fuzzer {fuzzer}!')
    subprocess.check_call(['chmod', '+x', build_script])
    subprocess.check_call(['cp', '/bf/compilers.yaml', "."])
    subprocess.check_call(['/bf/bin/bf-cc', '-i', src_folder, '-o', out_folder, build_script], env=env)

    # Copy fuzzers to the out folder
    subprocess.check_call(['cp', '-r', '/bf/fuzzers', env['OUT']])

    # Copy necessary runtime files to the out folder
    subprocess.check_call(['mkdir', '-p', os.path.join(env['OUT'], 'llvm')])
    subprocess.check_call(['cp', '-r', '/bf/llvm/llvm-12/bin', os.path.join(env['OUT'], 'llvm', 'bin')])
    subprocess.check_call(['cp', '-r', '/bf/llvm/llvm-12/lib', os.path.join(env['OUT'], 'llvm', 'lib')])
    subprocess.check_call(['cp', '/bf/bin/bf', env['OUT']])
    subprocess.check_call(['cp', '/bf/config_gen.py', env['OUT']])

    # Copy one target binary to the out folder
    # otherwise fuzzbench will complain, because of common/fuzzer_utils.py: get_fuzz_target_binary (line 77)
    source_dir = os.path.join(env['OUT'], 'target', 'aflpp')
    dest_dir = env['OUT']
    for item in os.listdir(source_dir):
        s = os.path.join(source_dir, item)
        d = os.path.join(dest_dir, item)

        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def fuzz(input_corpus, output_corpus, target_binary):
    target_binary_base = os.path.basename(target_binary)
    target_folder = os.path.dirname(target_binary)
    target_binary_name = os.path.join(target_folder, "target", target_binary_base)

    # Generate config file
    with open("config.yaml", "w") as file:
        config_gen_script = os.path.join(target_folder,'config_gen.py')
        subprocess.check_call(['chmod', '+x', config_gen_script])
        subprocess.check_call([config_gen_script, '-i', input_corpus, '-o', output_corpus, '--', target_binary_name], env=os.environ.copy(), stdout=file)

    # Generate empty seed file if no seed file is provided
    if os.listdir(input_corpus):
        pass
    else:
        print('Creating a fake seed file in empty corpus directory.')
        default_seed_file = os.path.join(input_corpus, 'default_seed')
        with open(default_seed_file, 'w', encoding='utf-8') as file_handle:
            file_handle.write('hi')
    
    # add /out/llvm/lib to ldconfig
    with open('/etc/ld.so.conf.d/bandfuzz.conf', 'w') as file:
        file.write('/out/llvm/lib\n')
    subprocess.check_call(['ldconfig'])
    
    subprocess.check_call(['./bf', '--lazy=30'])
