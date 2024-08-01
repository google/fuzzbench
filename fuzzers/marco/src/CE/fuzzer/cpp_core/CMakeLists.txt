cmake_minimum_required(VERSION 3.5.1)

project(rgd C CXX)

## set up test
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -O3 -stdlib=libc++ -std=c++11 -fPIC -L/usr/local/lib")


include_directories(${LLVM_INCLUDE_DIRS} "/out/include")
add_definitions(${LLVM_DEFINITIONS})

INCLUDE(FindProtobuf)
FIND_PACKAGE(Protobuf REQUIRED)
ADD_SUBDIRECTORY(proto)

include_directories(${PROTOBUF_INCLUDE_DIR})
include_directories("${CMAKE_CURRENT_BINARY_DIR}")

MESSAGE( STATUS, "Protobuf lib is ${PROTOBUF_LIBRARY}")
MESSAGE( STATUS, "Protobuf libs is ${PROTOBUF_LIBRARIES}")
MESSAGE( STATUS, "rgd_proto_srcs is ${rgd_proto_srcs}")

add_library(gd
  STATIC
  proto
  ${PROTO_SRCS} 
  ${PROTO_HDRS}
  interface.cc
  util.cc
  #z3solver.cc  
  ${rgd_proto_srcs}
)

target_link_libraries(gd
  ${PROTOBUF_LIBRARY}
  protobuf
  tcmalloc
  z3
  pthread)
