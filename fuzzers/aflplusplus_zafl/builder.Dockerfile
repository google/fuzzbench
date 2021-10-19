# Copyright 2021 Google LLC
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

# Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y wget libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates libc-ares-dev

run printf "deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-12 main" |tee /etc/apt/sources.list.d/llvm-toolchain-xenial-12.list && wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key |apt-key add - && apt update


RUN echo $parent_image && apt-get update -y && env DEBIAN_FRONTEND=noninteractive apt install --no-install-recommends -y scons bison flex g++ nasm sharutils gcc-multilib g++-multilib autoconf libelf-dev coreutils makeself postgresql-client libpqxx-dev cmake git unzip wget build-essential python3-dev automake git flex bison libglib2.0-dev libpixman-1-dev python3-setuptools ninja-build tzdata openssl sudo fakeroot file postgresql 
RUN env DEBIAN_FRONTEND=noninteractive apt-get install -y lld-12 llvm-12 llvm-12-dev clang-12 
RUN env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends --reinstall ca-certificates

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 65e63b9cf107ae914630a4fff7381cee150df5fe

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && LLVM_CONFIG=llvm-config \
    PYTHON_INCLUDE=/ make && make install && \
    make -C utils/aflpp_driver && \
    cp utils/aflpp_driver/libAFLDriver.a /



# Get the hash from Zephyr's Gitlab for the projects to force Docker's cache to invalidate
# itself if an update to one of these projects occurs.
# the gitlab API uses project IDs instead of project names, making the URL harder to read.
# decoder ring:  id:27=zipr, id:117=zafl
# These project name->id mappings do not change unless someone deletes/forks/moves the project's repository,
# so they should be long-term stable.
ADD https://git.zephyr-software.com/api/v4/projects/27/repository/branches/master /tmp/zipr.killcache
ADD https://git.zephyr-software.com/api/v4/projects/117/repository/branches/master /tmp/zafl.killcache

ENV USER=root
# checkout and build zipr/zafl, and setup postgres
RUN cd / && \
	git config --global http.sslVerify false && \
 	git clone --recursive --depth 1 https://git.zephyr-software.com/opensrc/zipr.git &&\
	git clone --recursive --depth 1 https://git.zephyr-software.com/opensrc/zafl.git 

RUN 	bash -c 'unset CC ; unset CXX; unset CFLAGS; unset CXXFLAGS; cd /zipr ;  \
	service postgresql start ; \
	while ! pg_isready ; do sleep 1 ; done  ; \
	. set_env_vars ;  \
	scons -j3 ; \
	./postgres_setup.sh  ; \
 	cd /zafl ;  \
	. set_env_vars ;  \
	scons -j3 ; \
	cd / ; \
	rm -rf /zipr/irdb-libs /zipr/SMPStaticAnalyzer /*/.git' ; \
	cp /zafl/libzafl/lib/*so /out
	
RUN cp /afl/afl-fuzz /out
COPY cc.sh /cc.sh
COPY cxx.sh /cxx.sh
COPY zafl_bins.sh /zafl_bins.sh
COPY null.c /tmp
COPY aflpp_driver.c /tmp
RUN clang -c -fPIC /tmp/null.c -o /tmp/null.o; ar crs /out/fakeLibrary.a /tmp/null.o; cp /out/fakeLibrary.a /usr/lib/libFuzzingEngine.a

ENV LD_LIBRARY_PATH=/zafl/libzafl/lib/

# some benchmarks need this file which isn't copied by the default setup.
RUN if [ -f /usr/lib/x86_64-linux-gnu/hdf5/serial/libhdf5.so ] ;then  echo copying libhdf5  ; cp /usr/lib/x86_64-linux-gnu/hdf5/serial/libhdf5.so /out    ; chmod +x /out/libhdf5.so ; ln -s /out/libhdf5.so /out/libhdf5_serial.so.10; fi
RUN if [ -f /usr/lib/x86_64-linux-gnu/libsz.so.2             ] ;then  echo copying ssl      ; cp /usr/lib/x86_64-linux-gnu/libsz.so.2 /out/libsz.so       ; chmod +x /out/libsz.so   ; ln -s /out/libsz.so /out/libsz.so.2; fi
RUN if [ -f /usr/lib/x86_64-linux-gnu/libaec.so.0.0.3        ] ;then  echo copying libaec   ; cp /usr/lib/x86_64-linux-gnu/libaec.so.0.0.3 /out/libaec.so ; chmod +x /out/libaec.so  ; ln -s /out/libaec.so /out/libaec.so.0; fi
RUN if [ -f /usr/lib/x86_64-linux-gnu/libcares.so            ] ;then  echo copying libcares ; cp /usr/lib/x86_64-linux-gnu/libcares.so /out               ; chmod +x /out/libcares.so; ln -s /out/libcares.so /out/libcares.so.2; fi


