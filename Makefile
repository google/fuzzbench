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

include docker/build.mk

SHELL := /bin/bash
VENV_ACTIVATE := .venv/bin/activate

${VENV_ACTIVATE}:
	rm -rf .venv
	python3 -m venv .venv
	source ${VENV_ACTIVATE} && python3 -m pip install -r requirements.txt

install-dependencies: ${VENV_ACTIVATE}

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
