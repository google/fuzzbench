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

ENV CENTIPEDE_SRC=/src/centipede

# Remove the Centipede from OSS-Fuzz base-builder and rebuild centipede.
RUN rm -rf "$CENTIPEDE_SRC" && \
  git clone -n \
    https://github.com/google/centipede.git "$CENTIPEDE_SRC" && \
  echo 'build --client_env=CC=clang --cxxopt=-std=c++17 ' \
    '--cxxopt=-stdlib=libc++ --linkopt=-lc++' >> ~/.bazelrc && \
  (cd "$CENTIPEDE_SRC" && \
    git checkout 2a2c78a2c161d99f5962b9710bce61feb00acc3d && \
    ./install_dependencies_debian.sh && \
    bazel build -c opt :all) && \
  cp "$CENTIPEDE_SRC/bazel-bin/centipede" '/out/centipede'

RUN /clang/bin/clang "$CENTIPEDE_SRC/weak_sancov_stubs.cc" -c -o /lib/weak.o
