# Add path for custom compiler-rt modules.
list(INSERT CMAKE_MODULE_PATH 0 "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

set(COMPILER_RT_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR} CACHE PATH
"Path where built compiler-rt libraries should be stored.")
set(COMPILER_RT_EXEC_OUTPUT_DIR ${CMAKE_CURRENT_BINARY_DIR}/bin CACHE PATH
"Path where built compiler-rt executables should be stored.")
set(COMPILER_RT_SOURCE_DIR "${CMAKE_CURRENT_SOURCE_DIR}")
set(COMPILER_RT_INSTALL_PATH ${CMAKE_INSTALL_PREFIX} CACHE PATH
"Path where built compiler-rt libraries should be installed.")

set(COMPILER_RT_LIBRARY_OUTPUT_DIR ${COMPILER_RT_OUTPUT_DIR})
set(COMPILER_RT_LIBRARY_INSTALL_DIR ${ANGORA_LIB_DIR})


set(ARM64 aarch64)
set(X86_64 x86_64)
set(MIPS64 mips64 mips64el)

if(APPLE)
  set(ARM64 arm64)
  set(X86_64 x86_64 x86_64h)
endif()

set(CAN_TARGET_${X86_64} 1)
set(DFSAN_SUPPORTED_ARCH ${X86_64}) #  ${MIPS64} ${ARM64}
set(SANITIZER_COMMON_SUPPORTED_ARCH ${X86_64}) #  ${MIPS64} ${ARM64}

list(APPEND SANITIZER_COMMON_CFLAGS -O3)
list(APPEND SANITIZER_COMMON_CFLAGS -fPIC)

include(CheckIncludeFile)
check_include_file(rpc/xdr.h HAVE_RPC_XDR_H)
if (NOT HAVE_RPC_XDR_H)
  set(HAVE_RPC_XDR_H 0)
endif()

add_custom_target(compiler-rt ALL)
add_custom_target(install-compiler-rt)
add_custom_target(install-compiler-rt-stripped)

set_property(
  TARGET
    compiler-rt
    install-compiler-rt
    install-compiler-rt-stripped
  PROPERTY
    FOLDER "Compiler-RT Misc"
)

include(AddCompilerRT)
include(SanitizerUtils)

set(CMAKE_CXX_STANDARD 11)

add_subdirectory(sanitizer_common)
add_subdirectory(interception)
add_subdirectory(dfsan)
