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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:1b6a6993690fa947df74ceabbf6a1f89a46d7e4277492addcd45a8525e34be5a
RUN apt-get update && apt-get install -y build-essential ruby bison ninja-build \
    cmake zlib1g-dev libbz2-dev liblzma-dev
RUN git clone --depth 1 https://github.com/mruby/mruby mruby
RUN git clone --depth 1 https://github.com/bshastry/mruby_seeds.git mruby_seeds
WORKDIR mruby
COPY build.sh *.c *.options *.dict $SRC/
