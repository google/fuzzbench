# Copyright 2019 Evan Miller
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

FROM gcr.io/oss-fuzz-base/base-builder@sha256:644b720c4138c48258d3b6083125b4caada241540844d2a0daf94f284410f408
MAINTAINER emmiller@gmail.com
RUN apt-get update && apt-get install -y make autoconf automake gettext libtool zip zlib1g-dev pkg-config

RUN git clone https://github.com/WizardMac/ReadStat readstat
WORKDIR readstat
COPY build.sh $SRC/
ADD BBtargets.txt $OUT/
