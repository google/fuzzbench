
find_package(LLVM 6 REQUIRED CONFIG)

if (LLVM_FOUND)
    message(STATUS "LLVM_VERSION_MAJOR: ${LLVM_VERSION_MAJOR}")
    message(STATUS "LLVM_VERSION_MINOR: ${LLVM_VERSION_MINOR}")
    message(STATUS "LLVM_VERSION_PATCH: ${LLVM_VERSION_PATCH}")
else()
    message(FATAL_ERROR "You haven't install LLVM !")
endif()

if (NOT TARGET LLVMPassConfig)
    add_library(LLVMPassConfig INTERFACE IMPORTED)
    set_target_properties(LLVMPassConfig PROPERTIES
        INTERFACE_COMPILE_OPTIONS "-fno-rtti" #-fpic
        INTERFACE_INCLUDE_DIRECTORIES "${LLVM_INCLUDE_DIRS}"
        INTERFACE_LINK_DIRECTORIES "${LLVM_LIBRARY_DIRS}"
        INTERFACE_COMPILE_DEFINITIONS "LLVM_VERSION_MAJOR=${LLVM_VERSION_MAJOR};LLVM_VERSION_MINOR=${LLVM_VERSION_MINOR};"
        # INTERFACE_LINK_OPTIONS "-Wl,-znodelete"
    )
endif()

set (CMAKE_CXX_STANDARD 11)
# fix pass bug: https://github.com/sampsyo/llvm-pass-skeleton/issues/7#issuecomment-401834287
set (CMAKE_MODULE_LINKER_FLAGS "${CMAKE_CXX_LINK_FLAGS} -Wl,-znodelete")
if(APPLE)
    # User teor2345 reports that this is required to make things work on MacOS X.
    set (CMAKE_MODULE_LINK_FLAGS "${CMAKE_CXX_LINK_FLAGS} -Wl,-flat_namespace -Wl,-undefined,suppress")
endif(APPLE)

add_library(UnfoldBranchPass MODULE UnfoldBranchPass.cc)
target_link_libraries(UnfoldBranchPass LLVMPassConfig)
install (TARGETS UnfoldBranchPass DESTINATION ${KIRENENKO_PASS_DIR})

add_library(AngoraPass MODULE AngoraPass.cc)
target_link_libraries(AngoraPass LLVMPassConfig)
install (TARGETS AngoraPass DESTINATION ${KIRENENKO_PASS_DIR})

add_library(DFSanPass MODULE DFSanPass.cc)
target_link_libraries(DFSanPass LLVMPassConfig)
install (TARGETS DFSanPass DESTINATION ${KIRENENKO_PASS_DIR})

add_library(TaintPass MODULE TaintPass.cc)
target_link_libraries(TaintPass LLVMPassConfig)
install (TARGETS TaintPass DESTINATION ${KIRENENKO_PASS_DIR})
