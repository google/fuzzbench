#!/usr/bin/env python3
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
"""Utilities for dealing with git diffs."""
import os
import subprocess
from typing import List


def get_changed_files(commit_name: str = 'origin...') -> List[str]:
    """Return a list of absolute paths of files changed in this git branch."""
    uncommitted_diff_command = ['git', 'diff', '--name-only', 'HEAD']
    output = subprocess.check_output(
        uncommitted_diff_command).decode().splitlines()
    uncommitted_changed_files = set(
        os.path.abspath(path) for path in output if os.path.isfile(path))

    committed_diff_command = ['git', 'diff', '--name-only', commit_name]
    try:
        output = subprocess.check_output(
            committed_diff_command).decode().splitlines()
        committed_changed_files = set(
            os.path.abspath(path) for path in output if os.path.isfile(path))
        return list(committed_changed_files.union(uncommitted_changed_files))
    except subprocess.CalledProcessError:
        # This probably won't happen to anyone. It can happen if your copy
        # of the repo wasn't cloned so give instructions on how to handle.
        pass
    raise Exception((
        '"%s" failed.\n'
        'Please run "git fetch origin master && '
        'git symbolic-ref refs/remotes/origin/HEAD refs/remotes/origin/master" '
        'and try again.\n'
        'Please file an issue if this doesn\'t fix things.') %
                    ' '.join(committed_diff_command))
