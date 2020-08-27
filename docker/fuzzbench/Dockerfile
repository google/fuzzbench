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

FROM python:3.7

# Install the docker CLI.
ENV DOCKER_VERSION=19.03.12
RUN wget https://download.docker.com/linux/static/stable/x86_64/docker-${DOCKER_VERSION}.tgz \
 && tar xzvf docker-${DOCKER_VERSION}.tgz --strip 1 -C /usr/local/bin docker/docker \
 && rm -rf docker-${DOCKER_VERSION}.tgz

WORKDIR /fuzzbench

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY alembic.ini alembic.ini
COPY analysis analysis
COPY benchmarks benchmarks
COPY common common
COPY database database
COPY docker docker
COPY experiment/build experiment/build
COPY experiment/*.py experiment/
COPY fuzzbench fuzzbench
COPY fuzzers fuzzers

CMD PYTHONPATH=. python3 -u fuzzbench/run_experiment.py
