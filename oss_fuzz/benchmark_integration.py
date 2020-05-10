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
"""Script for setting up an integration of an OSS-Fuzz benchmark. The script
will create oss-fuzz.yaml as well as copy the files from OSS-Fuzz to build the
benchmark."""
import argparse
import datetime
from distutils import dir_util
import os
import sys

from common import utils

# pylint: disable=import-error,wrong-import-position,ungrouped-imports

# TODO(metzman): Don't rely on OSS-Fuzz code. We don't want to depend on it
# because it can easily break use. Especially becuase:
# 1. We use private methods
# 2. The OSS-Fuzz code depends on absolute imports.
# 3. The OSS-Fuzz code assumes it is run from the OSS-Fuzz directory and can
# accdidentaly break our repo.
OSS_FUZZ_REPO_PATH = os.path.join(utils.ROOT_DIR, 'third_party', 'oss-fuzz',
                                  'infra')
sys.path.append(OSS_FUZZ_REPO_PATH)

import bisector
import build_specified_commit
import helper
import repo_manager

from common import logs
from common import yaml_utils


def copy_dir_contents(src_dir, dst_dir):
    """Copy the contents of |src_dir| into |dst_dir|."""
    # !!! Test new benchmark.
    return dir_util.copy_tree(src_dir, dst_dir)


def copy_oss_fuzz_files(project, commit_date, benchmark_dir):
    """Checkout the right files from OSS-Fuzz to build the benchmark based on
    |project| and |commit_date|. Then copy them to |benchmark_dir|."""
    cwd = os.getcwd()
    oss_fuzz_repo_manager = repo_manager.BaseRepoManager(helper.OSS_FUZZ_DIR)
    try:
        projects_dir = os.path.join(helper.OSS_FUZZ_DIR, 'projects', project)
        os.chdir(helper.OSS_FUZZ_DIR)
        oss_fuzz_commit, _, _ = oss_fuzz_repo_manager.git([
            'log', '--before=' + commit_date.isoformat(), '-n1', '--format=%H',
            projects_dir
        ],
                                                          check_result=True)
        oss_fuzz_commit = oss_fuzz_commit.strip()
        if not oss_fuzz_commit:
            logs.warning('No suitable earlier OSS-Fuzz commit found.')
            return False
        oss_fuzz_repo_manager.git(['checkout', oss_fuzz_commit, projects_dir],
                                  check_result=True)
        copy_dir_contents(projects_dir, benchmark_dir)
        return True
    finally:
        oss_fuzz_repo_manager.git(['reset', '--hard'])
        # !!! MUST BE DONE IN THIS ORDER OR ELSE WE RESET OUR FUZZBENCH REPO.
        os.chdir(cwd)


def get_benchmark_name(project, fuzz_target, benchmark_name=None):
    """Returns the name of the benchmark. Returns |benchmark_name| if is set.
    Otherwise returns a name based on |project| and |fuzz_target|."""
    if benchmark_name is not None:
        return benchmark_name
    return project + '_' + fuzz_target


def replace_base_builder(benchmark_dir, commit_date):
    """Replace the parent image of the Dockerfile in |benchmark_dir|,
    base-builder (latest), with a version of base-builder that is likely to
    build the project as it was on |commit_date| without issue."""
    base_builder_repo = bisector._load_base_builder_repo()  # pylint: disable=protected-access
    if base_builder_repo:
        base_builder_digest = base_builder_repo.find_digest(commit_date)
        logs.info('Using base-builder with digest %s.', base_builder_digest)
        build_specified_commit._replace_base_builder_digest(  # pylint: disable=protected-access
            os.path.join(benchmark_dir, 'Dockerfile'), base_builder_digest)


def create_oss_fuzz_yaml(project, fuzz_target, commit, commit_date,
                         repo_path,
                         benchmark_dir):
    """Create the oss-fuzz.yaml file in |benchmark_dir| based on the values from
    |project|, |fuzz_target|, |commit| and |commit_date|."""
    yaml_filename = os.path.join(benchmark_dir, 'oss-fuzz.yaml')
    config = {
        'project': project,
        'fuzz_target': fuzz_target,
        'commit': commit,
        'commit_date': commit_date,
        'repo_path': repo_path,
    }
    yaml_utils.write(yaml_filename, config)


def integrate_benchmark(project,
                        fuzz_target,
                        commit,
                        commit_date,
                        repo_path,
                        benchmark_name=None):
    """Copies files needed to integrate an OSS-Fuzz benchmark and creates the
    benchmark's oss-fuzz.yaml file."""
    benchmark_name = get_benchmark_name(project, fuzz_target, benchmark_name)
    benchmark_dir = os.path.join(utils.ROOT_DIR, 'benchmarks', benchmark_name)
    # !!! REPLACE WITH RECOMMENDED LIBRARY
    commit_date = datetime.datetime.fromisoformat(commit_date).replace(
        tzinfo=datetime.timezone.utc)
    copy_oss_fuzz_files(project, commit_date, benchmark_dir)
    replace_base_builder(benchmark_dir, commit_date)
    create_oss_fuzz_yaml(project, fuzz_target, commit, commit_date,
                         repo_path,
                         benchmark_dir)


def main():
    """Copies files needed to integrate an OSS-Fuzz benchmark and creates the
    benchmark's oss-fuzz.yaml file."""
    parser = argparse.ArgumentParser(description='Integrate a new benchmark.')
    parser.add_argument('-p',
                        '--project',
                        help='Project of benchmark.',
                        required=True)
    parser.add_argument('-f',
                        '--fuzz-target',
                        help='Fuzz target benchmark.',
                        required=True)
    parser.add_argument('-r',
                        '--repo-path',
                        help='Project repo path in OSS-Fuzz image.',
                        required=True)
    parser.add_argument('-n',
                        '--benchmark-name',
                        help='Benchmark name.',
                        required=False)
    parser.add_argument('-c', '--commit', help='Project commit.')
    parser.add_argument('-d', '--date', help='Date.')
    args = parser.parse_args()
    integrate_benchmark(args.project, args.fuzz_target, args.commit, args.date,
                        args.repo_path,
                        args.benchmark_name)
    return 0


if __name__ == '__main__':
    main()
