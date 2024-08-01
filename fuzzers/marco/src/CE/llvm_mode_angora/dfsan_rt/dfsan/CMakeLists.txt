# include_directories(..)

# Runtime library sources and build flags.
set(DFSAN_RTL_SOURCES
  dfsan.cc
  dfsan_custom.cc
  dfsan_interceptors.cc)

set(DFSAN_RTL_HEADERS
  dfsan.h
  dfsan_flags.inc
  dfsan_platform.h)

set(DFSAN_COMMON_CFLAGS ${SANITIZER_COMMON_CFLAGS})

append_rtti_flag(OFF DFSAN_COMMON_CFLAGS)
# Prevent clang from generating libc calls.
append_list_if(COMPILER_RT_HAS_FFREESTANDING_FLAG -ffreestanding DFSAN_COMMON_CFLAGS)

# Static runtime library.
add_compiler_rt_component(dfsan)

foreach(arch ${DFSAN_SUPPORTED_ARCH})
  set(DFSAN_CFLAGS ${DFSAN_COMMON_CFLAGS})
  append_list_if(COMPILER_RT_HAS_FPIE_FLAG -fPIE DFSAN_CFLAGS)
  add_compiler_rt_runtime(dfsan_rt
    STATIC
    ARCHS ${arch}
    SOURCES ${DFSAN_RTL_SOURCES}
            $<TARGET_OBJECTS:RTInterception.${arch}>
            $<TARGET_OBJECTS:RTSanitizerCommon.${arch}>
            $<TARGET_OBJECTS:RTSanitizerCommonLibc.${arch}>
    CFLAGS ${DFSAN_CFLAGS}
    PARENT_TARGET dfsan)
  add_sanitizer_rt_symbols(dfsan_rt
    ARCHS ${arch}
    EXTRA dfsan.syms.extra)
  add_dependencies(dfsan
    dfsan_rt-${arch}-symbols)
  install(FILES ${COMPILER_RT_OUTPUT_DIR}/libdfsan_rt-${arch}.a.syms
    DESTINATION ${COMPILER_RT_LIBRARY_INSTALL_DIR})
endforeach()

set(dfsan_abilist_dir ${COMPILER_RT_OUTPUT_DIR}/share)
set(dfsan_abilist_filename ${dfsan_abilist_dir}/dfsan_abilist.txt)
add_custom_target(dfsan_abilist ALL
  DEPENDS ${dfsan_abilist_filename})
add_custom_command(OUTPUT ${dfsan_abilist_filename}
                   VERBATIM
                   COMMAND
                    ${CMAKE_COMMAND} -E make_directory ${dfsan_abilist_dir}
                   COMMAND
                     cat ${CMAKE_CURRENT_SOURCE_DIR}/done_abilist.txt
                         ${CMAKE_CURRENT_SOURCE_DIR}/libc_ubuntu1404_abilist.txt
                         > ${dfsan_abilist_filename}
                   DEPENDS done_abilist.txt libc_ubuntu1404_abilist.txt)
add_dependencies(dfsan dfsan_abilist)
install(FILES ${dfsan_abilist_filename}
        DESTINATION ${ANGORA_RULE_DIR})

