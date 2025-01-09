# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# ...

import os
import shutil
import subprocess
import sys

from fuzzers import utils

def is_benchmark(name):
    """Check if the benchmark contains the string |name|."""
    benchmark = os.getenv("BENCHMARK", None)
    return benchmark is not None and name in benchmark


def install(package):
    """Install a Python package with pip."""
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])


def install_all():
    """Install all required Python dependencies."""
    packages = [
        "asttokens==2.2.1", "backcall==0.2.0", "decorator==5.1.1",
        "executing==1.2.0", "greenstalk==2.0.2", "ipdb==0.13.13",
        "ipython==8.12.2", "jedi==0.18.2", "networkit==10.1", "numpy==1.24.4",
        "parso==0.8.3", "pexpect==4.8.0", "pickleshare==0.7.5",
        "prompt-toolkit==3.0.39", "psutil==5.9.5", "ptyprocess==0.7.0",
        "pure-eval==0.2.2", "Pygments==2.15.1", "PyYAML==5.3.1",
        "scipy==1.10.1", "six==1.16.0", "stack-data==0.6.2", "tabulate==0.9.0",
        "tomli==2.0.1", "traitlets==5.9.0", "typing-extensions==4.7.1",
        "wcwidth==0.2.6",
        # 额外需求
        "pyelftools==0.30"
    ]
    for p in packages:
        install(p)


def prepare_build_environment():
    if is_benchmark("mbedtls"):
        file_path = os.path.join(os.getenv("SRC"), "mbedtls", "library", "CMakeLists.txt")
        if os.path.isfile(file_path):
            subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g' " + file_path
            subprocess.check_call(subst_cmd, shell=True)

    if is_benchmark("openthread"):
        mbed_cmake_one = os.path.join(
            os.getenv("SRC"),
            "openthread", "third_party", "mbedtls", "repo",
            "library", "CMakeLists.txt")
        mbed_cmake_two = os.path.join(
            os.getenv("SRC"),
            "openthread", "third_party", "mbedtls", "repo",
            "CMakeLists.txt")
        if os.path.isfile(mbed_cmake_one):
            subst_cmd = r"sed -i 's/\(-Wdocumentation\)//g' " + mbed_cmake_one
            subprocess.check_call(subst_cmd, shell=True)
        if os.path.isfile(mbed_cmake_two):
            subst_cmd = r"sed -i 's/\(-Werror\)//g' " + mbed_cmake_two
            subprocess.check_call(subst_cmd, shell=True)


def get_hfuzz1_build_directory(target_directory):
    return os.path.join(target_directory, "hfuzz1")


def get_hfuzz2_build_directory(target_directory):
    """Return path to hfuzz2 build directory."""
    return os.path.join(target_directory, "hfuzz2")


def get_vanilla_build_directory(target_directory):
    """Return path to vanilla build directory."""
    return os.path.join(target_directory, "vanilla")


def get_cmplog_build_directory(target_directory):
    """Return path to cmplog build directory."""
    return os.path.join(target_directory, "cmplog")

def get_hfuzz3_build_directory(target_directory):
    return os.path.join(target_directory, "hfuzz3");

def get_libafl_build_directory(target_directory):
    """Return path to libafl build directory."""
    return os.path.join(target_directory, "libafl")

def build_hfuzz1_binary():
    print("[build_hfuzz1_binary] Building hfuzz1 instrumentation.")
    is_build_failed = False

    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    src = os.getenv("SRC")
    work = os.getenv("WORK")
    fuzz_target = os.getenv("FUZZ_TARGET")
    out_dir = os.getenv("OUT")
    pwd = os.getcwd()

    old_cc = os.environ.get("CC")
    old_cxx = os.environ.get("CXX")
    old_lib = os.environ.get("FUZZER_LIB")

    os.environ["CC"] = "/hfuzz1/afl-clang-fast"
    os.environ["CXX"] = "/hfuzz1/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/hfuzz1/libAFLDriver.a"

    os.environ["AFL_LLVM_DICT2FILE"] = os.path.join(out_dir, "keyval.dict")
    os.environ["AFL_LLVM_DICT2FILE_NO_MAIN"] = "1"

    hfuzz1_dir = get_hfuzz1_build_directory(out_dir)
    if not os.path.exists(hfuzz1_dir):
        os.mkdir(hfuzz1_dir)

    with utils.restore_directory(src), utils.restore_directory(work):
        new_env = os.environ.copy()
        new_env["OUT"] = hfuzz1_dir
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(hfuzz1_dir, os.path.basename(fuzz_target))

        try:
            utils.build_benchmark(env=new_env)

            # 拷贝中间件信息
            for f in ["br_src_map", "strcmp_err_log", "instrument_meta_data"]:
                tmp_path = os.path.join("/dev/shm", f)
                if os.path.exists(tmp_path):
                    shutil.copy(tmp_path, os.path.join(hfuzz1_dir, f))

            HFUZZ1_FILES = [
                "br_node_id_2_cmp_type",
                "border_edges",
                "max_border_edge_id",
                "max_br_dist_edge_id",
                "border_edges_cache"
            ]
            for f in HFUZZ1_FILES:
                hfuzz1_file_path = os.path.join("/dev/shm", f)
                if os.path.exists(hfuzz1_file_path):
                    shutil.copy(hfuzz1_file_path, os.path.join(hfuzz1_dir, f))

            # 切换到 hfuzz1_dir 调用 gen_graph_no_gllvm_15.py
            graph_script = "/hfuzz1/gen_graph_no_gllvm_15.py"
            old_dir = os.getcwd()
            try:
                os.chdir(hfuzz1_dir)
                final_fuzz_bin = new_env["FUZZ_TARGET"]
                subprocess.check_call([
                    "python3", graph_script, final_fuzz_bin, "instrument_meta_data"
                ])
            finally:
                os.chdir(old_dir)

        except subprocess.CalledProcessError:
            print("[build_hfuzz1_binary] Failed, skip.")
            is_build_failed = True
        finally:
            os.chdir(pwd)
            if old_cc is not None:
                os.environ["CC"] = old_cc
            if old_cxx is not None:
                os.environ["CXX"] = old_cxx
            if old_lib is not None:
                os.environ["FUZZER_LIB"] = old_lib

    # 如果编译成功，把 hfuzz1_dir 下的 fuzz_target 拷贝回 out_dir
    if (not is_build_failed) and fuzz_target:
        built_bin = os.path.join(hfuzz1_dir, os.path.basename(fuzz_target))
        if os.path.exists(built_bin):
            shutil.copy(built_bin, os.path.join(out_dir, "hfuzz1_" + os.path.basename(fuzz_target)))

        # 同时也把 HFUZZ1_FILES 复制到 /out (如果它们在 hfuzz1_dir 里)
        HFUZZ1_FILES = [
            "br_node_id_2_cmp_type",
            "border_edges",
            "max_border_edge_id",
            "max_br_dist_edge_id",
            "border_edges_cache"
        ]
        for f in HFUZZ1_FILES:
            in_build_dir = os.path.join(hfuzz1_dir, f)
            if os.path.exists(in_build_dir):
                shutil.copy(in_build_dir, os.path.join(out_dir, f))

    return (not is_build_failed)


def build_hfuzz2_binary():
    """
    Build HFuzz2-instrumented binary：
      1) 清理 /dev/shm/*
      2) 切换 CC/CXX/FUZZER_LIB => /hfuzz2
      3) 创建 hfuzz2 目录
      4) 调用 build_benchmark
      5) 执行 gen_graph_no_gllvm_15.py (切换到 hfuzz2_dir)
      6) 若成功，把产物复制回 /out
      7) 把 HFuzz2 生成的 hfuzz2_br_node_id_2_cmp_type 等文件也复制到 /out
    """
    print("[build_hfuzz2_binary] Building HFuzz2 instrumentation.")
    is_build_failed = False

    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    src = os.getenv("SRC")
    work = os.getenv("WORK")
    fuzz_target = os.getenv("FUZZ_TARGET")
    out_dir = os.getenv("OUT")
    pwd = os.getcwd()

    old_cc = os.environ.get("CC")
    old_cxx = os.environ.get("CXX")
    old_lib = os.environ.get("FUZZER_LIB")

    os.environ["CC"] = "/hfuzz2/afl-clang-fast"
    os.environ["CXX"] = "/hfuzz2/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/hfuzz2/libAFLDriver.a"

    os.environ["AFL_LLVM_DICT2FILE"] = os.path.join(out_dir, "keyval.dict")
    os.environ["AFL_LLVM_DICT2FILE_NO_MAIN"] = "1"

    hfuzz2_dir = get_hfuzz2_build_directory(out_dir)
    if not os.path.exists(hfuzz2_dir):
        os.mkdir(hfuzz2_dir)

    with utils.restore_directory(src), utils.restore_directory(work):
        new_env = os.environ.copy()
        new_env["OUT"] = hfuzz2_dir
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(hfuzz2_dir, os.path.basename(fuzz_target))

        try:
            utils.build_benchmark(env=new_env)

            for f in ["br_src_map", "strcmp_err_log", "instrument_meta_data"]:
                tmp_path = os.path.join("/dev/shm", f)
                if os.path.exists(tmp_path):
                    shutil.copy(tmp_path, os.path.join(hfuzz2_dir, f))

            graph_script = "/hfuzz2/gen_graph_no_gllvm_15.py"
            old_dir = os.getcwd()
            try:
                os.chdir(hfuzz2_dir)
                final_fuzz_bin = new_env["FUZZ_TARGET"]
                subprocess.check_call(["python3", graph_script,
                                       final_fuzz_bin, "instrument_meta_data"])
            finally:
                os.chdir(old_dir)

        except subprocess.CalledProcessError:
            print("[build_hfuzz2_binary] Failed, skip.")
            is_build_failed = True
        finally:
            os.chdir(pwd)
            if old_cc is not None:
                os.environ["CC"] = old_cc
            if old_cxx is not None:
                os.environ["CXX"] = old_cxx
            if old_lib is not None:
                os.environ["FUZZER_LIB"] = old_lib

    if (not is_build_failed) and fuzz_target:
        built_bin = os.path.join(hfuzz2_dir, os.path.basename(fuzz_target))
        if os.path.exists(built_bin):
            shutil.copy(built_bin, os.path.join(out_dir, "hfuzz2_" + os.path.basename(fuzz_target)))

        # 同时也将 HFUZZ2_FILES 复制到 /out
        HFUZZ2_FILES = [
            "hfuzz2_br_node_id_2_cmp_type",
            "hfuzz2_border_edges",
            "hfuzz2_max_border_edge_id",
            "hfuzz2_max_br_dist_edge_id",
            "hfuzz2_border_edges_cache"
        ]
        for f in HFUZZ2_FILES:
            in_build_dir = os.path.join(hfuzz2_dir, f)
            if os.path.exists(in_build_dir):
                shutil.copy(in_build_dir, os.path.join(out_dir, f))

    return (not is_build_failed)


def build_vanilla_binary():
    print("[build_vanilla_binary] Building vanilla instrumentation.")
    is_build_failed = False

    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    src = os.getenv("SRC")
    work = os.getenv("WORK")
    fuzz_target = os.getenv("FUZZ_TARGET")
    out_dir = os.getenv("OUT")
    pwd = os.getcwd()

    old_cc = os.environ.get("CC")
    old_cxx = os.environ.get("CXX")
    old_lib = os.environ.get("FUZZER_LIB")

    os.environ["CC"] = "/afl_vanilla/afl-clang-fast"
    os.environ["CXX"] = "/afl_vanilla/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/afl_vanilla/libAFLDriver.a"

    vanilla_dir = get_vanilla_build_directory(out_dir)
    if not os.path.exists(vanilla_dir):
        os.mkdir(vanilla_dir)

    with utils.restore_directory(src), utils.restore_directory(work):
        new_env = os.environ.copy()
        new_env["OUT"] = vanilla_dir
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(vanilla_dir, os.path.basename(fuzz_target))

        try:
            utils.build_benchmark(env=new_env)
        except subprocess.CalledProcessError:
            print("[build_vanilla_binary] Failed, skip.")
            is_build_failed = True
        finally:
            os.chdir(pwd)
            if old_cc is not None:
                os.environ["CC"] = old_cc
            if old_cxx is not None:
                os.environ["CXX"] = old_cxx
            if old_lib is not None:
                os.environ["FUZZER_LIB"] = old_lib

    if (not is_build_failed) and fuzz_target:
        built_bin = os.path.join(vanilla_dir, os.path.basename(fuzz_target))
        if os.path.exists(built_bin):
            shutil.copy(built_bin, os.path.join(out_dir, os.path.basename(fuzz_target)))

    return (not is_build_failed)


def build_cmplog_binary():
    print("[build_cmplog_binary] Building cmplog instrumentation.")
    is_build_failed = False

    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    src = os.getenv("SRC")
    work = os.getenv("WORK")
    fuzz_target = os.getenv("FUZZ_TARGET")
    out_dir = os.getenv("OUT")
    pwd = os.getcwd()

    old_cc = os.environ.get("CC")
    old_cxx = os.environ.get("CXX")
    old_lib = os.environ.get("FUZZER_LIB")
    old_cmp = os.environ.get("AFL_LLVM_CMPLOG")

    os.environ["CC"] = "/afl_vanilla/afl-clang-fast"
    os.environ["CXX"] = "/afl_vanilla/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/afl_vanilla/libAFLDriver.a"
    os.environ["AFL_LLVM_CMPLOG"] = "1"

    cmplog_dir = get_cmplog_build_directory(out_dir)
    if not os.path.exists(cmplog_dir):
        os.mkdir(cmplog_dir)

    with utils.restore_directory(src), utils.restore_directory(work):
        new_env = os.environ.copy()
        new_env["OUT"] = cmplog_dir
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(cmplog_dir, os.path.basename(fuzz_target))

        try:
            utils.build_benchmark(env=new_env)
        except subprocess.CalledProcessError:
            print("[build_cmplog_binary] Failed, skip.")
            is_build_failed = True
        finally:
            os.chdir(pwd)
            if old_cc is not None:
                os.environ["CC"] = old_cc
            if old_cxx is not None:
                os.environ["CXX"] = old_cxx
            if old_lib is not None:
                os.environ["FUZZER_LIB"] = old_lib
            if old_cmp is not None:
                os.environ["AFL_LLVM_CMPLOG"] = old_cmp
            else:
                os.environ.pop("AFL_LLVM_CMPLOG", None)

    if (not is_build_failed) and fuzz_target:
        built_bin = os.path.join(cmplog_dir, os.path.basename(fuzz_target))
        if os.path.exists(built_bin):
            shutil.copy(
                built_bin,
                os.path.join(out_dir, "cmplog_" + os.path.basename(fuzz_target))
            )

    return (not is_build_failed)

def build_hfuzz3_binary():

    is_build_failed = False
    print("[build_hfuzz3_binary] Building hfuzz3 instrumentation.")

    out_dir = os.getenv("OUT")
    pwd = os.getcwd()
    # src = os.path.join(out_dir, "hfuzz3_target_bin")
    src = os.getenv("SRC")
    work = os.getenv("WORK")

    fuzz_target = os.getenv("FUZZ_TARGET")

    old_cc = os.environ.get("CC")
    old_cxx = os.environ.get("CXX")
    old_cflags = os.environ.get("CFLAGS")
    old_cxxflags = os.environ.get("CXXFLAGS")
    old_lib = os.environ.get("FUZZER_LIB")
    old_cmp = os.environ.get("AFL_LLVM_CMPLOG")


    os.environ["CC"] = "/hfuzz3/afl-clang-fast"
    os.environ["CXX"] = "/hfuzz3/afl-clang-fast++"
    os.environ["FUZZER_LIB"] = "/afl_vanilla/libAFLDriver.a"
    # macros = "-DAFL_CFG_PATH=\\\"hfuzz3_sandcov_cfg\\\""
    # os.environ["CFLAGS"] = macros
    # os.environ["CXXFLAGS"] = macros

    hfuzz3_dir = get_hfuzz3_build_directory(out_dir)

    if not os.path.exists(hfuzz3_dir):
        os.mkdir(hfuzz3_dir)

    with utils.restore_directory(src), utils.restore_directory(work):
        new_env = os.environ.copy()
        new_env["OUT"] = hfuzz3_dir

        if fuzz_target is None:
            raise RuntimeError(f"FUZZ_TARGET is not set")
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(hfuzz3_dir, os.path.basename(fuzz_target))
    
    # dst = os.path.join(out_dir, 'hfuzz3_' + os.path.basename(fuzz_target))

    # if os.path.exists(src):
    #     os.system(f"link {src} {dst}")
    #     return True 
    # else:
    #     return False
    
        try:
            utils.build_benchmark(env=new_env)

            # for f in ["gen_graph.py", "hfuzz3_sancov_cfg"]:
            #     tmp_path = os.path.join("/hfuzz3", f)
            #     if os.path.exists(tmp_path):
            #         shutil.copy(tmp_path, os.path.join(hfuzz3_dir, f))

            
            graph_script = "/hfuzz3/gen_graph.py"
            old_dir = os.getcwd()
            try:
                os.chdir(hfuzz3_dir)
                final_fuzz_bin = new_env["FUZZ_TARGET"]
                subprocess.check_call(["python3", graph_script,
                                       final_fuzz_bin])
            finally:
                os.chdir(old_dir)
        except subprocess.CalledProcessError:
            print("[build_hfuzz3_binary] Failed, skip.")
            is_build_failed = True
        finally:
            os.chdir(pwd)
            if old_cc is not None:
                os.environ["CC"] = old_cc
            if old_cxx is not None:
                os.environ["CXX"] = old_cxx
            # if old_cflags is not None：
            #     os.environ["CFLAGS"] = old_cflags
            # if old_cxxflags is not None:
            #     os.environ["CXXFLAGS"] = old_cxxflags;
            if old_lib is not None:
                os.environ["FUZZER_LIB"] = old_lib

    if (not is_build_failed) and fuzz_target:
        built_bin = os.path.join(hfuzz3_dir, os.path.basename(fuzz_target))
        if os.path.exists(built_bin):
            shutil.copy(
                built_bin,
                os.path.join(out_dir, "hfuzz3_" + os.path.basename(fuzz_target))
            )

    return (not is_build_failed)

# def build_libafl_binary():
#     print("[build_libafl_binary] Building libafl instrumentation.")
#     out_dir = os.getenv("OUT")
#     src = os.path.join(out_dir, "libafl_target_bin")
#     fuzz_target = os.getenv("FUZZ_TARGET")
#     dst = os.path.join(out_dir, 'libafl_' + os.path.basename(fuzz_target))

#     if os.path.exists(src):
#         os.system(f"link {src} {dst}")
#         return True 
#     else:
#         return False
    
def build_libafl_binary():
    print("[build_libafl_binary] Building libafl instrumentation.")
    is_build_failed = False

    subprocess.check_call(["rm", "-f", "/dev/shm/*"])

    src = os.getenv("SRC")
    work = os.getenv("WORK")
    fuzz_target = os.getenv("FUZZ_TARGET")
    out_dir = os.getenv("OUT")
    pwd = os.getcwd()

    old_cc = os.environ.get("CC")
    old_cxx = os.environ.get("CXX")
    old_lib = os.environ.get("FUZZER_LIB")


    """Build benchmark."""
    os.environ['CC'] = ('/libafl/fuzzers/fuzzbench/fuzzbench'
                        '/target/release-fuzzbench/libafl_cc')
    os.environ['CXX'] = ('/libafl/fuzzers/fuzzbench/fuzzbench'
                         '/target/release-fuzzbench/libafl_cxx')

    os.environ['ASAN_OPTIONS'] = 'abort_on_error=0:allocator_may_return_null=1'
    os.environ['UBSAN_OPTIONS'] = 'abort_on_error=0'

    cflags = ['--libafl']
    cxxflags = ['--libafl', '--std=c++14']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cxxflags)
    utils.append_flags('LDFLAGS', cflags)

    os.environ['FUZZER_LIB'] = '/stub_rt.a'

    libafl_dir = get_libafl_build_directory(out_dir)
    if not os.path.exists(libafl_dir):
        os.mkdir(libafl_dir)

    with utils.restore_directory(src), utils.restore_directory(work):
        new_env = os.environ.copy()
        new_env["OUT"] = libafl_dir
        if fuzz_target:
            new_env["FUZZ_TARGET"] = os.path.join(libafl_dir, os.path.basename(fuzz_target))

        try:
            utils.build_benchmark(env=new_env)

        except subprocess.CalledProcessError:
            print("[build_libafl_binary] Failed, skip.")
            is_build_failed = True
        finally:
            os.chdir(pwd)
            if old_cc is not None:
                os.environ["CC"] = old_cc
            if old_cxx is not None:
                os.environ["CXX"] = old_cxx
            if old_lib is not None:
                os.environ["FUZZER_LIB"] = old_lib

    if (not is_build_failed) and fuzz_target:
        built_bin = os.path.join(libafl_dir, os.path.basename(fuzz_target))
        if os.path.exists(built_bin):
            shutil.copy(built_bin, os.path.join(out_dir, "libafl_" + os.path.basename(fuzz_target)))

    return (not is_build_failed)

def build():
    """
    在 OSS-Fuzz 中被调用的主要构建入口。
    按顺序编译：hfuzz1、hfuzz2、vanilla、cmplog，
    并复制相应的 fuzzer 主程序到 /out。
    """
    install_all()
    prepare_build_environment()

    built_hfuzz1     = build_hfuzz1_binary()
    built_hfuzz2  = build_hfuzz2_binary()
    built_vanilla = build_vanilla_binary()
    built_cmplog  = build_cmplog_binary()
    built_hfuzz3 = build_hfuzz3_binary()
    build_libafl = build_libafl_binary()


    # 复制 fuzzer 主程序。如果没编译成功, 也许不会用到, 但这里先都拷或者做检查
    if os.path.exists("/hfuzz1/afl-fuzz"):
        shutil.copy("/hfuzz1/afl-fuzz", os.path.join(os.environ["OUT"], "hfuzz1_4.30c_hybrid_start"))
    if os.path.exists("/hfuzz2/afl-fuzz"):
        shutil.copy("/hfuzz2/afl-fuzz", os.path.join(os.environ["OUT"], "hfuzz2_4.30c_hybrid_start"))
    if os.path.exists("/afl_vanilla/afl-fuzz"):
        shutil.copy("/afl_vanilla/afl-fuzz", os.path.join(os.environ["OUT"], "afl-fuzz-vanilla"))
        shutil.copy("/afl_vanilla/afl-fuzz", os.path.join(os.environ["OUT"], "cmplog_4.30c_hybrid_start"))
    # @yrd the fuzzer is compiled in $OUT. The fuzzer is $OUT/libafl_fuzzer.
    # if os.path.exists("/PATH/to/libafl-fuzzer"):
    #     shutil.copy("/path/to/libafl-fuzzer", os.path.join(os.environ["OUT"], "libafl_fuzzer"))
    """
    if os.path.exists("/hfuzz3/main"):
        shutil.copy("/hfuzz3/main", os.path.join(os.environ["OUT"], "hfuzz3_4.30c_hybrid_start"))
    """
    # if os.path.exists("/hfuzz3/gen_graph.py"):
    #     shutil.copy("/hfuzz3/gen_graph.py", os.path.join(os.environ["OUT"], "gen_graph.py"))
    if os.path.exists("/hfuzz3/afl-fuzz"):
        # shutil.copy("/hfuzz3/afl-fuzz", os.path.join(os.environ["OUT"], "hfuzz3_fuzzer"))
        shutil.copy("/hfuzz3/afl-fuzz", os.path.join(os.environ["OUT"], "hfuzz3_4.30c_hybrid_start"))


    # ensemble_runner.py
    if os.path.exists("/hfuzz2/ensemble_runner.py"):
        shutil.copy("/hfuzz2/ensemble_runner.py", os.environ["OUT"])

    print("[build] Build results:")
    print("  HFUZZ1     :", "OK" if built_hfuzz1 else "FAIL")
    print("  HFuzz2  :", "OK" if built_hfuzz2 else "FAIL")
    print("  Vanilla :", "OK" if built_vanilla else "FAIL")
    print("  CmpLog  :", "OK" if built_cmplog else "FAIL")
    print("  LibAFL  :", "OK" if build_libafl else "FAIL")
    print("  HFuzz3:", "OK" if built_hfuzz3 else "FAIL")

    if not any([built_hfuzz1, built_hfuzz2, built_vanilla, built_cmplog, build_libafl]):
        with open(os.path.join(os.getenv("OUT"), "is_vanilla"), "w") as f:
            f.write("all_failed")
        print("[build] All instrumentation failed.")


def prepare_fuzz_environment(input_corpus):
    """准备fuzz环境，比如设置AFL_NO_UI, AFL_AUTORESUME等。"""
    os.environ["AFL_NO_UI"] = "1"
    os.environ["AFL_SKIP_CPUFREQ"] = "1"
    os.environ["AFL_NO_AFFINITY"] = "1"
    os.environ["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = "1"
    os.environ["AFL_SKIP_CRASHES"] = "1"
    os.environ["AFL_SHUFFLE_QUEUE"] = "1"
    os.environ["AFL_FAST_CAL"] = "1"
    os.environ["AFL_DISABLE_TRIM"] = "1"
    os.environ["AFL_CMPLOG_ONLY_NEW"] = "1"
    os.environ["AFL_AUTORESUME"] = "1"

    utils.create_seed_file_for_empty_corpus(input_corpus)

# def run_libafl_fuzz(input_corpus, output_corpus, target_binary):
#     out_dir = os.getenv("OUT")
#     target_binary = target_binary
#     subprocess.run(
#         f"{os.path.join(out_dir, target_binary)} --cores 1 --input {input_corpus} --output {output_corpus}",
#         shell=True
#     )

def run_afl_fuzz(input_corpus, output_corpus, target_binary, hide_output=False):
    dictionary_path = utils.get_dictionary_path(target_binary)
    out_dir = os.getenv("OUT")

    van_bin = os.path.join(out_dir, "afl-fuzz-vanilla")

    hfuzz1_built_path = os.path.join(out_dir, "hfuzz1_" + os.path.basename(target_binary))
    hfuzz2_built_path = os.path.join(out_dir, "hfuzz2_" + os.path.basename(target_binary))
    cmplog_built_path = os.path.join(out_dir, "cmplog_" + os.path.basename(target_binary))
    libafl_build_path = os.path.join(out_dir, "libafl_" + os.path.basename(target_binary))
    hfuzz3_build_path = os.path.join(out_dir, "hfuzz3_" + os.path.basename(target_binary))

    has_any_ensemble = any([os.path.exists(hfuzz1_built_path),
                            os.path.exists(hfuzz2_built_path),
                            os.path.exists(cmplog_built_path),
                            os.path.exists(libafl_build_path),
                            os.path.exists(hfuzz3_build_path)])
    if has_any_ensemble:
        cmd = [
            "python", "ensemble_runner.py",
            "-i", input_corpus, "-o", output_corpus,
            "-b", target_binary
        ]
        
        if os.path.exists(hfuzz1_built_path):
            cmd += ["--hfuzz1_target_binary", hfuzz1_built_path]
        
        if os.path.exists(hfuzz2_built_path):
            cmd += ["--hfuzz2_target_binary", hfuzz2_built_path]
        
        if os.path.exists(cmplog_built_path):
            cmd += ["--cmplog_target_binary", cmplog_built_path]
            

        if os.path.exists(libafl_build_path):
            cmd += ["--libafl_target_binary", libafl_build_path]
         

        if os.path.exists(hfuzz3_build_path):
            cmd += ["--hfuzz3_target_binary", hfuzz3_build_path]

        if dictionary_path:
            cmd += ["-x", os.path.join("/out", "keyval.dict"), dictionary_path]

        print("[run_afl_fuzz] Ensemble command:", " ".join(cmd))
        output_stream = subprocess.DEVNULL if hide_output else None
        subprocess.check_call(cmd, stdout=output_stream, stderr=output_stream)
    else:
        if os.path.exists(van_bin):
            cmd = [
                van_bin,
                "-i", input_corpus,
                "-o", output_corpus,
                "-t", "1000+",
                "-m", "none",
                "--",
                target_binary
            ]
            if dictionary_path:
                cmd += ["-x", os.path.join("/out", "keyval.dict"), "-x", dictionary_path]

            print("[run_afl_fuzz] Vanilla command:", " ".join(cmd))
            output_stream = subprocess.DEVNULL if hide_output else None
            subprocess.check_call(cmd, stdout=output_stream, stderr=output_stream)
        else:
            print("[run_afl_fuzz] No valid fuzzer found, aborting.")


def fuzz(input_corpus, output_corpus, target_binary):
    """
    在 OSS-Fuzz 中实际执行fuzz的入口。
    """
    prepare_fuzz_environment(input_corpus)
    run_afl_fuzz(input_corpus, output_corpus, target_binary)
