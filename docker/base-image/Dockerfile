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

# Install google-cloud-sdk and Python3.
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y apt-transport-https python3-pip python3-dev curl ca-certificates gnupg

RUN echo "deb https://packages.cloud.google.com/apt cloud-sdk main" \
    | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list && \
    curl https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | apt-key add - && \
    apt-get update -y && \
    apt-get install -y google-cloud-sdk

# Install common python dependencies.
COPY ./requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt