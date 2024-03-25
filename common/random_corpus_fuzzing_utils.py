# Copyright 2023 Google LLC
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
"""Utility functions for micro-experiment run."""

import random
import os
import tempfile
import multiprocessing
import zipfile
from typing import List

from common import experiment_utils
from common import filesystem
from common import logs

MAX_SOURCE_CORPUS_FILES = 1
CORPUS_ELEMENT_BYTES_LIMIT = 1 * 1024 * 1024


def initialize_random_corpus_fuzzing(benchmarks: List[str], num_trials: int):
    """Prepare corpus for micro experiment."""
    pool_args = ()
    with multiprocessing.Pool(*pool_args) as pool:
        pool.starmap(prepare_benchmark_random_corpus,
                     [(benchmark, num_trials) for benchmark in benchmarks])
        logs.info('Done preparing corpus for micro experiment')


# pylint: disable=too-many-locals
def prepare_benchmark_random_corpus(benchmark: str, num_trials: int):
    """Prepare corpus for given benchmark."""
    # Temporary location to park corpus files before get picked randomly.
    benchmark_unarchived_corpora = os.path.join(
        experiment_utils.get_oss_fuzz_corpora_unarchived_path(), benchmark)
    filesystem.create_directory(benchmark_unarchived_corpora)

    # Unzip oss fuzz corpus.
    corpus_archive_filename = f'{benchmark}.zip'
    oss_fuzz_corpus_archive_path = os.path.join(
        experiment_utils.get_oss_fuzz_corpora_filestore_path(),
        corpus_archive_filename)
    with zipfile.ZipFile(oss_fuzz_corpus_archive_path) as zip_file:
        idx = 0
        for seed_corpus_file in zip_file.infolist():
            if seed_corpus_file.filename.endswith('/'):
                # Ignore directories.
                continue
            # Allow callers to opt-out of unpacking large files.
            if seed_corpus_file.file_size > CORPUS_ELEMENT_BYTES_LIMIT:
                continue
            output_filename = f'{idx:016d}'
            output_file_path = os.path.join(benchmark_unarchived_corpora,
                                            output_filename)
            zip_file.extract(seed_corpus_file, output_file_path)
            idx += 1

    # Path used to store and feed seed corpus for benchmark runner
    # each trial group will have the same seed input(s).
    benchmark_random_corpora = os.path.join(
        experiment_utils.get_random_corpora_filestore_path(), benchmark)
    filesystem.create_directory(benchmark_random_corpora)

    with tempfile.TemporaryDirectory() as tmp_dir:
        all_corpus_files = []
        for root, _, files in os.walk(benchmark_unarchived_corpora):
            for filename in files:
                file_path = os.path.join(root, filename)
                all_corpus_files.append(file_path)

        all_corpus_files.sort()
        trial_group_num = 0
        # All trials in the same group will start with the same
        # set of randomly selected seed files.
        while trial_group_num < num_trials:
            trial_group_subdir = f'trial-group-{trial_group_num}'
            custom_corpus_trial_dir = os.path.join(benchmark_random_corpora,
                                                   trial_group_subdir)
            src_dir = os.path.join(tmp_dir, 'source')
            filesystem.recreate_directory(src_dir)

            source_files = random.sample(all_corpus_files,
                                         MAX_SOURCE_CORPUS_FILES)
            for file in source_files:
                filesystem.copy(file, src_dir)

            # Copy only the src directory.
            filesystem.copytree(src_dir, custom_corpus_trial_dir)
            trial_group_num += 1

    return []
