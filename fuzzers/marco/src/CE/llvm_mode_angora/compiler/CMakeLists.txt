
add_executable(AngoraClang angora_clang.c)
set_target_properties(AngoraClang PROPERTIES OUTPUT_NAME "angora-clang")

add_custom_command(TARGET AngoraClang POST_BUILD
    COMMAND ln -sf "angora-clang" "angora-clang++")
install (TARGETS AngoraClang DESTINATION ${ANGORA_BIN_DIR})
install (FILES ${CMAKE_CURRENT_BINARY_DIR}/angora-clang++ DESTINATION ${ANGORA_BIN_DIR})
