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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:ccb5bcb44c8d2027a756947ae24cb48f7ce647897f57bbec50b4bcaff1367e44
RUN apt-get update && \
    apt-get install -y autoconf automake libtool bison re2c pkg-config
RUN git clone --depth 1 --branch master https://github.com/php/php-src.git php-src
RUN git clone https://github.com/kkos/oniguruma.git php-src/oniguruma
WORKDIR php-src
COPY build.sh *.options $SRC/
