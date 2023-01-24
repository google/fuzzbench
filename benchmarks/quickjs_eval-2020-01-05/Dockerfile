# Copyright 2019 Google Inc.
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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:fb1a9a49752c9e504687448d1f1a048ec1e062e2e40f7e8a23e86b63ff3dad7c
RUN apt-get update && \
    apt-get install -y autoconf automake libtool bison pkg-config

# This project does not have any release/tag.
RUN git clone \
        --depth 1 \
        --branch master \
        https://github.com/bellard/quickjs \
        quickjs

WORKDIR quickjs
COPY build.sh $SRC/
COPY *.c *.h *.dict $SRC/
