
add_executable(KOClang ko_clang.c)
set_target_properties(KOClang PROPERTIES OUTPUT_NAME "ko-clang")

add_custom_command(TARGET KOClang POST_BUILD
    COMMAND ln -sf "ko-clang" "ko-clang++")
install (TARGETS KOClang DESTINATION ${KIRENENKO_BIN_DIR})
install (FILES ${CMAKE_CURRENT_BINARY_DIR}/ko-clang++ DESTINATION ${KIRENENKO_BIN_DIR})
