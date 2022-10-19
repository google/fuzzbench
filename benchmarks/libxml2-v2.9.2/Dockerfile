# Copyright 2020 Google LLC
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
    apt-get upgrade -y ca-certificates && \
    apt-get install -y \
    make \
    wget \
    autoconf \
    automake \
    libtool \
    libglib2.0-dev

RUN git clone https://gitlab.gnome.org/GNOME/libxml2.git

RUN wget -qO $OUT/xml.dict \
    https://raw.githubusercontent.com/google/AFL/debe27037b9444bbf090a0ffbd5d24889bb887ae/dictionaries/xml.dict
COPY target.cc build.sh $SRC/
