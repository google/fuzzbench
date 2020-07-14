#!/bin/bash -ex
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

# Use this script once to setup a machine for running the fuzzbench service.

# Install a supported python version.
export PYTHON_VERSION=3.7.6

sudo apt-get update -y && sudo apt-get install -y \
  build-essential \
  rsync \
  curl \
  zlib1g-dev \
  libncurses5-dev \
  libgdbm-dev \
  libnss3-dev \
  libssl-dev \
  libreadline-dev \
  libffi-dev \
  virtualenv \
  libbz2-dev \
  liblzma-dev \
  libsqlite3-dev

cd /tmp/ && \
  curl -O https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz && \
  tar -xvf Python-$PYTHON_VERSION.tar.xz && \
  cd Python-$PYTHON_VERSION && \
  ./configure --enable-loadable-sqlite-extensions --enable-optimizations && \
  sudo make -j install && \
  sudo rm -r /tmp/Python-$PYTHON_VERSION.tar.xz /tmp/Python-$PYTHON_VERSION

# Download and run the cloud_sql_proxy.
export cloud_sql_proxy_path=/tmp/cloud_sql_proxy
wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O \
  $cloud_sql_proxy_path
chmod +x $cloud_sql_proxy_path

# This is a hardcoded value that only works for the official fuzzbench service.
$cloud_sql_proxy_path -instances=fuzzbench:us-central1:postgres-experiment-db=tcp:5432 &
