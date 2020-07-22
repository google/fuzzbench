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
# TODO(tanq16): Remove dependancy on this script to checkout commit.
# (Integrator can manually edit Dockerfile to checkout).
import os
import sys
import subprocess


def git(git_args, repo_dir):
    """
    Execute a git command with |git_args| for the repo located in |repo_dir|.
    Returns:
      True if successful.
      Raises subprocess.CalledError if unsuccessful.
    """
    command = ['git'] + git_args
    return subprocess.check_call(command, cwd=repo_dir) == 0


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
    if len(sys.argv) != 3:
        print("Usage: %s <commit> <src_dir>" % sys.argv[0])
        return 1
    commit = sys.argv[1]
    src_dir = sys.argv[2]
    if not commit:
        print('Not checking out commit.')
        return 0
    # Infer the project repo directory in the oss-fuzz builder image by
    # iteratively checking out the commit (provided by integrator) in src_dir.
    for _, directories, _ in os.walk(src_dir):
        for directory in directories:
            entry_to_check = os.path.join(src_dir, directory)
            try:
                checkout_success = checkout_repo_commit(commit, entry_to_check)
            except subprocess.CalledProcessError:
                continue
            if checkout_success:
                return 0
    print("Checkout unsuccessful.")
    return 1


if __name__ == '__main__':
    main()
