
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

## default taint models for IO and memory allocation.
add_library(DFSanIO STATIC io_func.c stdalloc.c)
install (TARGETS DFSanIO DESTINATION ${ANGORA_LIB_DIR})

## custom model
add_library(ZlibRt STATIC zlib_func.c)
install (TARGETS ZlibRt DESTINATION ${ANGORA_LIB_DIR})
install (FILES "zlib_abilist.txt" DESTINATION ${ANGORA_RULE_DIR})
