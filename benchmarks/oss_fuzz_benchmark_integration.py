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
will create benchmark.yaml as well as copy the files from OSS-Fuzz to build the
benchmark."""
import argparse
import datetime
from distutils import spawn
from distutils import dir_util
import os
import sys
import subprocess
import json
import bisect

from common import utils
from common import benchmark_utils
from common import logs
from common import new_process
from common import yaml_utils

OSS_FUZZ_DIR = os.path.join(utils.ROOT_DIR, 'third_party', 'oss-fuzz')
OSS_FUZZ_REPO_PATH = os.path.join(OSS_FUZZ_DIR, 'infra')
OSS_FUZZ_IMAGE_UPGRADE_DATE = datetime.datetime(
    year=2021, month=8, day=25, tzinfo=datetime.timezone.utc)


class GitRepoManager:
    """Git repo manager."""

    def __init__(self, repo_dir):
        self.repo_dir = repo_dir

    def git(self, cmd):
        """Runs a git command.

        Args:
          cmd: The git command as a list to be run.

        Returns:
          new_process.ProcessResult
        """
        return new_process.execute(['git'] + cmd, cwd=self.repo_dir)


class BaseBuilderDockerRepo:
    """Repo of base-builder images."""

    def __init__(self):
        self.timestamps = []
        self.digests = []

    def add_digest(self, timestamp, digest):
        """Add a digest."""
        self.timestamps.append(timestamp)
        self.digests.append(digest)

    def find_digest(self, timestamp):
        """Finds the latest image before the given timestamp."""
        index = bisect.bisect_right(self.timestamps, timestamp)
        if index > 0:
            return self.digests[index - 1]
        raise ValueError('Failed to find suitable base-builder.')


def copy_oss_fuzz_files(project, commit_date, benchmark_dir):
    """Checks out the right files from OSS-Fuzz to build the benchmark based on
    |project| and |commit_date|. Then copies them to |benchmark_dir|."""
    if not os.path.exists(os.path.join(OSS_FUZZ_DIR, '.git')):
        logs.error(
            '%s is not a git repo. Try running: git submodule update --init',
            OSS_FUZZ_DIR)
        raise RuntimeError('%s is not a git repo.' % OSS_FUZZ_DIR)
    oss_fuzz_repo_manager = GitRepoManager(OSS_FUZZ_DIR)
    projects_dir = os.path.join(OSS_FUZZ_DIR, 'projects', project)
    try:
        # Find an OSS-Fuzz commit that can be used to build the benchmark.
        _, oss_fuzz_commit, _ = oss_fuzz_repo_manager.git([
            'log', '--before=' + commit_date.isoformat(), '-n1', '--format=%H',
            projects_dir
        ])
        oss_fuzz_commit = oss_fuzz_commit.strip()
        if not oss_fuzz_commit:
            logs.warning('No suitable earlier OSS-Fuzz commit found.')
            return False
        oss_fuzz_repo_manager.git(['checkout', oss_fuzz_commit, projects_dir])
        dir_util.copy_tree(projects_dir, benchmark_dir)
        os.remove(os.path.join(benchmark_dir, 'project.yaml'))
        return True
    finally:
        oss_fuzz_repo_manager.git(['reset', '--hard'])


def get_benchmark_name(project, fuzz_target, benchmark_name=None):
    """Returns the name of the benchmark. Returns |benchmark_name| if is set.
    Otherwise returns a name based on |project| and |fuzz_target|."""
    return benchmark_name if benchmark_name else project + '_' + fuzz_target


def _load_base_builder_docker_repo():
    """Gets base-image digests. Returns the docker rep."""
    gcloud_path = spawn.find_executable('gcloud')
    if not gcloud_path:
        logs.warning('gcloud not found in PATH.')
        return None

    _, result, _ = new_process.execute([
        gcloud_path,
        'container',
        'images',
        'list-tags',
        'gcr.io/oss-fuzz-base/base-builder',
        '--format=json',
        '--sort-by=timestamp',
    ])
    result = json.loads(result)

    repo = BaseBuilderDockerRepo()
    for image in result:
        timestamp = datetime.datetime.fromisoformat(
            image['timestamp']['datetime']).astimezone(datetime.timezone.utc)
        repo.add_digest(timestamp, image['digest'])

    return repo


def _replace_base_builder_digest(dockerfile_path, digest):
    """Replaces the base-builder digest in a Dockerfile."""
    with open(dockerfile_path) as handle:
        lines = handle.readlines()

    new_lines = []
    for line in lines:
        if line.strip().startswith('FROM'):
            line = 'FROM gcr.io/oss-fuzz-base/base-builder@' + digest + '\n'

        new_lines.append(line)

    with open(dockerfile_path, 'w') as handle:
        handle.write(''.join(new_lines))


def replace_base_builder(benchmark_dir, commit_date):
    """Replaces the parent image of the Dockerfile in |benchmark_dir|,
    base-builder (latest), with a version of base-builder that is likely to
    build the project as it was on |commit_date| without issue."""
    base_builder_repo = _load_base_builder_docker_repo()
    if base_builder_repo:
        base_builder_digest = base_builder_repo.find_digest(commit_date)
        logs.info('Using base-builder with digest %s.', base_builder_digest)
        _replace_base_builder_digest(
            os.path.join(benchmark_dir, 'Dockerfile'), base_builder_digest)


def create_oss_fuzz_yaml(project, fuzz_target, commit, commit_date,
                         benchmark_dir):
    """Creates the benchmark.yaml file in |benchmark_dir| based on the values
    from |project|, |fuzz_target|, |commit| and |commit_date|."""
    yaml_filename = os.path.join(benchmark_dir, 'benchmark.yaml')
    config = {
        'project': project,
        'fuzz_target': fuzz_target,
        'commit': commit,
        'commit_date': commit_date,
    }
    yaml_utils.write(yaml_filename, config)


def integrate_benchmark(project, fuzz_target, benchmark_name, commit,
                        commit_date):
    """Copies files needed to integrate an OSS-Fuzz benchmark and creates the
    benchmark's benchmark.yaml file."""
    benchmark_name = get_benchmark_name(project, fuzz_target, benchmark_name)
    benchmark_dir = os.path.join(benchmark_utils.BENCHMARKS_DIR, benchmark_name)
    # TODO(metzman): Replace with dateutil since fromisoformat isn't supposed to
    # work on arbitrary iso format strings.
    commit_date = datetime.datetime.fromisoformat(commit_date).astimezone(
        datetime.timezone.utc)
    if commit_date >= OSS_FUZZ_IMAGE_UPGRADE_DATE:
        raise ValueError(
            f'Cannot integrate benchmark after {OSS_FUZZ_IMAGE_UPGRADE_DATE}. '
            'See https://github.com/google/fuzzbench/issues/1353')
    copy_oss_fuzz_files(project, commit_date, benchmark_dir)
    replace_base_builder(benchmark_dir, commit_date)
    create_oss_fuzz_yaml(project, fuzz_target, commit, commit_date,
                         benchmark_dir)
    return benchmark_name


def main():
    """Copies files needed to integrate an OSS-Fuzz benchmark and creates the
    benchmark's benchmark.yaml file."""
    parser = argparse.ArgumentParser(description='Integrate a new benchmark.')
    parser.add_argument('-p',
                        '--project',
                        help='Project for benchmark. Example: "zlib"',
                        required=True)
    parser.add_argument(
        '-f',
        '--fuzz-target',
        help='Fuzz target for benchmark. Example: "zlib_uncompress_fuzzer"',
        required=True)
    parser.add_argument(
        '-n',
        '--benchmark-name',
        help='Benchmark name. Defaults to <project>_<fuzz_target>',
        required=False)
    parser.add_argument('-c', '--commit', help='Project commit hash.')
    parser.add_argument(
        '-d',
        '--date',
        help='Date of the commit. Example: 2019-10-19T09:07:25+01:00')

    logs.initialize()
    args = parser.parse_args()
    benchmark = integrate_benchmark(
        args.project, args.fuzz_target, args.benchmark_name,
        args.commit, args.date)
    logs.info('Successfully integrated benchmark: %s.', benchmark)
    logs.info('Please run "make test-run-afl-%s" to test integration.',
              benchmark)
    return 0


if __name__ == '__main__':
    main()
