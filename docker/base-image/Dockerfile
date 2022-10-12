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

FROM ubuntu:jammy

# Python 3.10 is the default version in Ubuntu 22.04 (Jammy Jellyfish)
ENV PYTHON_VESION 3.10
RUN apt-get update && apt-get install -y \
    rsync \
    curl \
    virtualenv \
    liblzma-dev

# Install common python dependencies.
COPY ./requirements.txt /
RUN pip3 install -r /requirements.txt

# Install google-cloud-cli (named google-cloud-sdk prior to version 371.0.0).
RUN apt-get update && \
    apt-get install -y \
    apt-transport-https \
    ca-certificates \
    gnupg

RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - && \
    apt-get update && \
    apt-get install -y google-cloud-cli
