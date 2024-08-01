# run compile.sh

# install (FILES "build_fast/lib/libc++.a" DESTINATION "${KIRENENKO_LIB_DIR}/libcxx_fast")
# install (FILES "build_fast/lib/libc++abi.a" DESTINATION "${KIRENENKO_LIB_DIR}/libcxx_fast" RENAME "libc++abifast.a")
# install (FILES "build_track/lib/libc++.a" DESTINATION "${KIRENENKO_LIB_DIR}/libcxx_track")
# install (FILES "build_track/lib/libc++abi.a" DESTINATION "${KIRENENKO_LIB_DIR}/libcxx_track" RENAME "libc++abitrack.a")
install (FILES "build_taint/lib/libc++.a" DESTINATION "${KIRENENKO_LIB_DIR}")
install (FILES "build_taint/lib/libc++abi.a" DESTINATION "${KIRENENKO_LIB_DIR}")
