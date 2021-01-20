# Copyright 2020 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
################################################################################

FROM gcr.io/oss-fuzz-base/base-builder@sha256:1de3a8f8be448cb9f477ee157df52a1a0e6004a0d3da89b18130c06c97f66f20
RUN apt-get update && apt-get install -y make autoconf automake libtool zlib1g-dev
RUN git clone --depth 1 https://github.com/AcademySoftwareFoundation/openexr openexr
WORKDIR openexr
COPY build.sh *_fuzzer.cc $SRC/
