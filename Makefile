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

#include docker/build.mk
include docker/generated.mk

SHELL := /bin/bash
VENV_ACTIVATE := .venv/bin/activate

${VENV_ACTIVATE}: requirements.txt
	python3 -m venv .venv
	source ${VENV_ACTIVATE} && python3 -m pip install -r requirements.txt

install-dependencies: ${VENV_ACTIVATE}

docker/generated.mk: docker/generate_makefile.py $(wildcard fuzzers/*/variants.yaml) ${VENV_ACTIVATE}
	source ${VENV_ACTIVATE} && PYTHONPATH=. python3 $< > $@

presubmit: install-dependencies
	source ${VENV_ACTIVATE} && python3 presubmit.py

format: install-dependencies
	source ${VENV_ACTIVATE} && python3 presubmit.py format

licensecheck: install-dependencies
	source ${VENV_ACTIVATE} && python3 presubmit.py licensecheck

lint: install-dependencies
	source ${VENV_ACTIVATE} && python3 presubmit.py lint

typecheck: install-dependencies
	source ${VENV_ACTIVATE} && python3 presubmit.py typecheck

docs-serve:
	cd docs && bundle exec jekyll serve --livereload

clear-cache:
	docker stop $$(docker ps -a -q) 2>/dev/null ; \
	docker rm -vf $$(docker ps -a -q) 2>/dev/null ; \
	docker rmi -f $$(docker images -a -q) 2>/dev/null ; \
	docker volume rm $$(docker volume ls -q) 2>/dev/null ; true
