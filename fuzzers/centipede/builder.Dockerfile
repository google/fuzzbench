# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG parent_image
FROM $parent_image

# Add C++15.
ADD https://commondatastorage.googleapis.com/chromium-browser-clang/Linux_x64/clang-llvmorg-15-init-1995-g5bec1ea7-1.tgz /
RUN mkdir /clang && \
    tar zxvf /clang-llvmorg-15-init-1995-g5bec1ea7-1.tgz -C /clang

# Install deps of centipede, clone&build centipede.
RUN apt update && \
  apt install -y apt-transport-https && \
  curl -fsSL 'https://bazel.build/bazel-release.pub.gpg' \
    | gpg --dearmor > '/etc/apt/trusted.gpg.d/bazel.gpg' && \
  echo 'deb [arch=amd64] ' \
    'https://storage.googleapis.com/bazel-apt stable jdk1.8' \
    | tee '/etc/apt/sources.list.d/bazel.list' && \
  apt update && \
  apt install -y \
    vim \
    libssl-dev \
    bazel && \
  git clone \
    --depth 1 \
    --branch main \
    --single-branch \
    'https://github.com/google/centipede.git' '/src/centipede/' && \
  echo 'build --client_env=CC=clang --cxxopt=-std=c++17 ' \
    '--cxxopt=-stdlib=libc++ --linkopt=-lc++' >> ~/.bazelrc && \
  (cd '/src/centipede/' && \
  bazel build -c opt :all) && \
  cp '/src/centipede/bazel-bin/centipede' '/out/centipede' && \
  CENTIPEDE_FLAGS=`cat /src/centipede/clang-flags.txt`

ENV CFLAGS="$CFLAGS $CENTIPEDE_FLAGS"
ENV CXXFLAGS="$CXXFLAGS $CENTIPEDE_FLAGS"
