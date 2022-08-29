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

FROM gcr.io/oss-fuzz-base/base-clang@sha256:30706816922bf9c141b15ff4a5a44af8c0ec5700d4b46e0572029c15e495d45b AS base-clang
FROM gcr.io/fuzzbench/base-image

RUN apt-get update && apt-get install -y wget && \
    wget https://storage.googleapis.com/oss-fuzz-introspector-testing/focus_map.yaml && \
    apt-get remove --purge -y wget

COPY --from=base-clang /usr/local/bin/llvm-symbolizer /usr/local/bin/