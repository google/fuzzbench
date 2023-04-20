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

# Use a libFuzzer version that supports clang source-based coverage.
# This libfuzzer is 0b5e6b11c358e704384520dc036eddb5da1c68bf with
# https://github.com/google/fuzzbench/blob/cf86138081ec705a47ce0a4bab07b5737292e7e0/fuzzers/coverage/patch.diff
# applied.

RUN wget https://storage.googleapis.com/fuzzbench-artifacts/libfuzzer-coverage.zip -O $LF_PATH && \
    echo "cc78179f6096cae4b799d0cc9436f000cc0be9b1fb59500d16b14b1585d46b61 $LF_PATH" | sha256sum --check --status && \
    mkdir /tmp/libfuzzer && \
    cd /tmp/libfuzzer && \
    unzip $LF_PATH  && \
    bash build.sh && \
    cp libFuzzer.a /usr/lib && \
    rm -rf /tmp/libfuzzer $LF_PATH