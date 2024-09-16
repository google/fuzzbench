cmake_minimum_required(VERSION 3.4)

project(kirenenko_llvm_mode VERSION 1.2.2 LANGUAGES C CXX ASM)

include_directories(include)
include_directories(dfsan_rt)

set(KIRENENKO_BIN_DIR ".")
set(KIRENENKO_LIB_DIR "lib")
set(KIRENENKO_RULE_DIR "rules")
set(KIRENENKO_PASS_DIR "pass")

add_subdirectory(compiler)
add_subdirectory(pass)
add_subdirectory(rules)
add_subdirectory(libcxx)
add_subdirectory(external_lib)
add_subdirectory(dfsan_rt)
