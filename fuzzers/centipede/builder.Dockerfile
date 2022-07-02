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

ENV BAZEL_GPG_LINK='https://bazel.build/bazel-release.pub.gpg'
ENV BAZEL_GPG_FILE='/etc/apt/trusted.gpg.d/bazel.gpg'
ENV BAZEL_APT_LINK='https://storage.googleapis.com/bazel-apt'
ENV BAZEL_APT_LIST='/etc/apt/sources.list.d/bazel.list'
ENV CENTIPEDE_GITHUB='https://github.com/google/centipede.git'
ENV CENTIPEDE_SRC='/src/centipede/'
ENV CENTIPEDE_CONFIG='build \
  --client_env=CC=clang \
  --cxxopt=-std=c++17 \
  --cxxopt=-stdlib=libc++ \
  --linkopt=-lc++'

# Install deps of centipede, clone&build centipede
RUN apt update && \
  apt install -y apt-transport-https && \
  curl -fsSL "${BAZEL_GPG_LINK}" \
    | gpg --dearmor > "${BAZEL_GPG_FILE}" && \
  echo "deb [arch=amd64] ${BAZEL_APT_LINK} stable jdk1.8" \
    | tee "${BAZEL_APT_LIST}" && \
  apt update && \
  apt install -y \
    vim \
    bazel && \
  git clone \
    --depth 1 \
    --branch main \
    --single-branch \
    "${CENTIPEDE_GITHUB}" "${CENTIPEDE_SRC}" && \
  echo "${CENTIPEDE_CONFIG}" > ~/.bazelrc && \
  (cd "${CENTIPEDE_SRC}" && \
  bazel build -c opt :all) && \
  cp "${CENTIPEDE_SRC}/bazel-bin/centipede" "/out/centipede"
