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
"""Script for checking out a commit in an OSS-Fuzz project's repo."""
import os
import sys
import subprocess


def git(git_args, repo_dir):
    """Execute a git command with |git_args| for the repo located in
    |repo_dir|."""
    command = ['git', '-C', repo_dir] + git_args
    return subprocess.run(command, check=True)


def fetch_unshallow(repo_dir):
    """Gets the history of |repo_dir|."""
    shallow_file = os.path.join(repo_dir, '.git', 'shallow')
    if os.path.exists(shallow_file):
        git(['fetch', '--unshallow'], repo_dir)


def checkout_repo_commit(commit, repo_dir):
    """Checkout |commit| in |repo_dir|."""
    fetch_unshallow(repo_dir)
    # TODO(metzman): Figure out if we need to run clean.
    return git(['checkout', '-f', commit], repo_dir)


def main():
    """Check out an OSS-Fuzz project repo."""
    commit = sys.argv[1]
    if not commit:
        print('Not checking out commit.')
        return 0
    # The SRC env var which is the /src directory in the oss-fuzz builder image
    # is passed as the second argument.
    src_dir = sys.argv[2]
    # Search for the correct project repo directory by checking out the commit
    # in all directories under src_dir.
    for dir_entry in os.listdir(src_dir):
        entry_to_check = os.path.join(src_dir, dir_entry)
        if os.path.isdir(entry_to_check):
            try:
                checkout_success = checkout_repo_commit(commit, entry_to_check)
            except subprocess.CalledProcessError:
                continue
            if not checkout_success.returncode:
                return 0
    print("Checkout unsuccessful.")
    return 0


if __name__ == '__main__':
    main()
