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

FROM ubuntu:focal

ENV DEBIAN_FRONTEND=noninteractive

# Python 3.10.8 is not the default version in Ubuntu 20.04 (Focal Fossa).
ENV PYTHON_VERSION 3.10.8
# Install dependencies required by Python3 or Pip3.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
    curl \
    xz-utils \
    build-essential \
    zlib1g-dev \
    libssl-dev \
    libffi-dev \
    libsqlite3-dev \
    libbz2-dev \
    liblzma-dev

RUN cd /tmp/ && \
    curl -O https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz && \
    tar -xvf Python-$PYTHON_VERSION.tar.xz > /dev/null && \
    cd Python-$PYTHON_VERSION && \
    ./configure \
        --enable-loadable-sqlite-extensions \
        --enable-optimizations \
        > /dev/null && \
    make -j install > /dev/null && \
    rm -r /tmp/Python-$PYTHON_VERSION.tar.xz /tmp/Python-$PYTHON_VERSION && \
    ln -s /usr/local/bin/python3 /usr/local/bin/python && \
    ln -s /usr/local/bin/pip3 /usr/local/bin/pip

# Install common python dependencies.
COPY ./requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt

# Install dependencies required by google-cloud-cli.
RUN apt-get update && \
    apt-get install -y \
    apt-transport-https \
    ca-certificates \
    rsync \
    gnupg

# Install google-cloud-cli (previously named google-cloud-sdk).
RUN echo "deb https://packages.cloud.google.com/apt cloud-sdk main" \
    | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | apt-key add - && \
    apt-get update && \
    apt-get install -y google-cloud-cli
