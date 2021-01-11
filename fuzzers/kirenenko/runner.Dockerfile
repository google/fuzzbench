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

#FROM gcr.io/fuzzbench/base-runner
FROM gcr.io/fuzzbench/base-image

RUN apt-get update 
RUN apt-get -y install git cmake wget libglib2.0-dev autoconf libtool
RUN git clone https://github.com/Z3Prover/z3.git /z3 && \
		cd /z3 && git checkout z3-4.8.7 && mkdir -p build && cd build && \
		cmake .. && make && make install

RUN wget https://download.redis.io/releases/redis-6.0.8.tar.gz?_ga=2.106808267.950746773.1603437795-213833146.1603437795 -O /redis-6.0.8.tar.gz
RUN tar xvf /redis-6.0.8.tar.gz -C /
RUN cd /redis-6.0.8 && make && make install

RUN git clone https://github.com/redis/hiredis.git /hiredis
RUN cd /hiredis && make && make install

RUN git clone https://github.com/jhu066/afl-grader-pro.git /grader
RUN cd /grader && git checkout fuzzbench && make && cd qemu_mode && ./build_qemu_support.sh


ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/out"
ENV AFL_MAP_SIZE=900000
ENV AFL_QUIET=1
ENV PATH="$PATH:/out"
ENV AFL_SKIP_CPUFREQ=1
#ENV AFL_NO_UI=1
ENV AFL_NO_AFFINITY=1
ENV AFL_SKIP_CRASHES=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
RUN ldconfig
#RUN apt-get update -y && \
#	apt-get install -y \
#	google-perftools \
#	llvm-6.0 llvm-6.0-dev llvm-6.0-tools

#RUN apt-get install -y clang-6.0 vim less
#RUN pip3 install psutil
