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

FROM gcr.io/fuzzbench/base-image

# Install and setup clang-11 for AFL/NEUZZ.
RUN apt install -y clang-11 && \
    ln -s /usr/bin/clang-11 /usr/bin/clang && \
    ln -s /usr/bin/clang++-11 /usr/bin/clang++
ENV PATH="/usr/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/lib/clang/11.0.0/lib/linux:${LD_LIBRARY_PATH}"

# Install Python2 and Pip2 on Ubuntu:20.04.
RUN DEBIAN_FRONTEND=noninteractive TZ=Etc/UTC \
        apt-get install -y software-properties-common && \
    apt-get update && \
    add-apt-repository universe && \
    apt-get install -y python-dev && \
    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py && \
    python2 get-pip.py && \
    rm /usr/bin/python && \
    ln -s /usr/bin/python2.7 /usr/bin/python

RUN apt-get update && \
    apt-get install wget -y && \
    python -m pip install --upgrade pip==20.3.4 && \
    python -m pip install tensorflow==1.8.0 && \
    python -m pip install keras==2.2.3

# Use Python3.10 by default.
RUN rm /usr/bin/python3 && \
    ln -s /usr/local/bin/python3 /usr/bin/python3
