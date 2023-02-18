# Copyright 2020 Google LLC
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

ENV LF_PATH /tmp/libfuzzer.zip

# libFuzzer from branch llvmorg-15.0.3 with minor changes to build script.
RUN wget https://storage.googleapis.com/fuzzbench-artifacts/libfuzzer.zip -O $LF_PATH && \
    echo "ed761c02a98a16adf6bb9966bf9a3ffd6794367a29dd29d4944a5aae5dba3c90 $LF_PATH" | sha256sum --check --status && \
    mkdir /tmp/libfuzzer && \
    cd /tmp/libfuzzer && \
    unzip $LF_PATH  && \
    bash build.sh && \
    cp libFuzzer.a /usr/lib
