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
"""Utility functions for coverage data calculation."""

import collections
import itertools
import json
import posixpath
from typing import Dict, List, Tuple
import tempfile

import pandas as pd

from analysis import data_utils
from common import filestore_utils
from common import logs

logger = logs.Logger('coverage_data_utils')


def fuzzer_and_benchmark_to_key(fuzzer: str, benchmark: str) -> str:
    """Returns the key representing |fuzzer| and |benchmark|."""
    return fuzzer + ' ' + benchmark


def key_to_fuzzer_and_benchmark(key: str) -> Tuple[str, str]:
    """Returns a tuple containing the fuzzer and the benchmark represented by
    |key|."""
    return tuple(key.split(' '))


def get_experiment_filestore_path_for_fuzzer_benchmark(
    fuzzer: str,
    benchmark: str,
    df: pd.DataFrame,
) -> str:
    """Returns the experiment filestore path for |fuzzer| and |benchmark| in
    |df|. Returns an arbitrary filestore path if there are multiple."""
    df = df[df['fuzzer'] == fuzzer]
    df = df[df['benchmark'] == benchmark]
    experiment_filestore_paths = get_experiment_filestore_paths(df)
    fuzzer_benchmark_filestore_path = experiment_filestore_paths[0]
    if len(experiment_filestore_paths) != 1:
        logger.warning(
            'Multiple cov filestores (%s) for this fuzzer (%s) benchmark (%s) '
            'pair. Using first: %s.', experiment_filestore_paths, fuzzer,
            benchmark, fuzzer_benchmark_filestore_path)
    return fuzzer_benchmark_filestore_path


def get_experiment_filestore_paths(df: pd.DataFrame) -> List[str]:
    """Returns a list of experiment filestore paths from |df|."""
    return list((df['experiment_filestore'] + '/' + df['experiment']).unique())


def get_coverage_report_filestore_path(fuzzer: str, benchmark: str,
                                       df: pd.DataFrame) -> str:
    """Returns the filestore path of the coverage report for |fuzzer| on
    |benchmark| for |df|."""
    exp_filestore_path = get_experiment_filestore_path_for_fuzzer_benchmark(
        fuzzer, benchmark, df)
    return posixpath.join(exp_filestore_path, 'coverage', 'reports', benchmark,
                          fuzzer, 'index.html')


def get_covered_branches_dict(experiment_df: pd.DataFrame) -> Dict:
    """Combines json files for different fuzzer-benchmark pair in
    |experiment_df| and returns a dictionary of the covered branches."""
    fuzzers_and_benchmarks = set(
        zip(experiment_df.fuzzer, experiment_df.benchmark))
    arguments = [(fuzzer, benchmark,
                  get_experiment_filestore_path_for_fuzzer_benchmark(
                      fuzzer, benchmark, experiment_df))
                 for fuzzer, benchmark in fuzzers_and_benchmarks]
    result = itertools.starmap(get_fuzzer_benchmark_covered_branches_and_key,
                               arguments)
    return dict(result)


def get_fuzzer_benchmark_covered_branches_filestore_path(
        fuzzer: str, benchmark: str, exp_filestore_path: str) -> str:
    """Returns the path to the covered branches json file in the |filestore| for
    |fuzzer| and |benchmark|."""
    return posixpath.join(exp_filestore_path, 'coverage', 'data', benchmark,
                          fuzzer, 'covered_branches.json')


def get_fuzzer_covered_branches(fuzzer: str, benchmark: str, filestore: str):
    """Returns the covered branches dict for |fuzzer| from the json file in the
    filestore."""
    src_file = get_fuzzer_benchmark_covered_branches_filestore_path(
        fuzzer, benchmark, filestore)
    with tempfile.NamedTemporaryFile() as dst_file:
        if filestore_utils.cp(src_file, dst_file.name,
                              expect_zero=False).retcode:
            logger.warning(
                'covered_branches.json file: %s could not be copied.', src_file)
            return {}
        with open(dst_file.name) as json_file:
            return json.load(json_file)


def get_fuzzer_benchmark_covered_branches_and_key(
        fuzzer: str, benchmark: str, filestore: str) -> Tuple[str, Dict]:
    """Accepts |fuzzer|, |benchmark|, |filestore|.
    Returns a tuple containing the fuzzer benchmark key and the branches covered
    by the fuzzer on the benchmark."""
    fuzzer_benchmark_covered_branches = get_fuzzer_covered_branches(
        fuzzer, benchmark, filestore)
    key = fuzzer_and_benchmark_to_key(fuzzer, benchmark)
    return key, fuzzer_benchmark_covered_branches


def get_unique_branch_dict(benchmark_coverage_dict: Dict) -> Dict:
    """Returns a dictionary containing the covering fuzzers for each unique
    branch, where the |threshold| defines which branches are unique."""
    branch_dict = collections.defaultdict(list)
    unique_branch_dict = {}
    threshold_count = 1
    for fuzzer in benchmark_coverage_dict:
        for branch in benchmark_coverage_dict[fuzzer]:
            branch_dict[branch].append(fuzzer)
    for branch, fuzzers in branch_dict.items():
        if len(fuzzers) <= threshold_count:
            unique_branch_dict[branch] = fuzzers
    return unique_branch_dict


def get_unique_branch_cov_df(unique_branch_dict: Dict,
                             fuzzer_names: List[str]) -> pd.DataFrame:
    """Returns a DataFrame where the two columns are fuzzers and the number of
    unique branches covered."""
    fuzzers = collections.defaultdict(int)
    for branch in unique_branch_dict:
        for fuzzer in unique_branch_dict[branch]:
            fuzzers[fuzzer] += 1
    dict_to_transform = {'fuzzer': [], 'unique_branches_covered': []}
    for fuzzer in fuzzer_names:
        covered_num = fuzzers[fuzzer]
        dict_to_transform['fuzzer'].append(fuzzer)
        dict_to_transform['unique_branches_covered'].append(covered_num)
    return pd.DataFrame(dict_to_transform)


def get_benchmark_cov_dict(coverage_dict, benchmark):
    """Returns a dictionary to store the covered branches of each fuzzer. Uses a
    set of tuples to store the covered branches."""
    benchmark_cov_dict = {}
    for key, covered_braches in coverage_dict.items():
        current_fuzzer, current_benchmark = key_to_fuzzer_and_benchmark(key)
        if current_benchmark == benchmark:
            covered_braches_in_set = set()
            for branch in covered_braches:
                covered_braches_in_set.add(tuple(branch))
            benchmark_cov_dict[current_fuzzer] = covered_braches_in_set
    return benchmark_cov_dict


def get_benchmark_aggregated_cov_df(coverage_dict, benchmark):
    """Returns a dataframe where each row represents a fuzzer and its aggregated
    coverage number."""
    dict_to_transform = {'fuzzer': [], 'aggregated_edges_covered': []}
    for key, covered_branches in coverage_dict.items():
        current_fuzzer, current_benchmark = key_to_fuzzer_and_benchmark(key)
        if current_benchmark == benchmark:
            dict_to_transform['fuzzer'].append(current_fuzzer)
            dict_to_transform['aggregated_edges_covered'].append(
                len(covered_branches))
    return pd.DataFrame(dict_to_transform)


def get_pairwise_unique_coverage_table(benchmark_coverage_dict, fuzzers):
    """Returns a table that shows the unique coverage between each pair of
    fuzzers.

    The pairwise unique coverage table is a square matrix where each
    row and column represents a fuzzer, and each cell contains a number
    showing the branches covered by the fuzzer of the column but not by
    the fuzzer of the row."""

    pairwise_unique_coverage_values = []
    for fuzzer_in_row in fuzzers:
        row = []
        for fuzzer_in_col in fuzzers:
            pairwise_unique_coverage_value = get_unique_covered_percentage(
                benchmark_coverage_dict[fuzzer_in_row],
                benchmark_coverage_dict[fuzzer_in_col])
            row.append(pairwise_unique_coverage_value)
        pairwise_unique_coverage_values.append(row)

    return pd.DataFrame(pairwise_unique_coverage_values,
                        index=fuzzers,
                        columns=fuzzers)


def get_unique_covered_percentage(fuzzer_row_covered_branches,
                                  fuzzer_col_covered_branches):
    """Returns the number of branches covered by the fuzzer of the
    column but not by the fuzzer of the row."""

    unique_branch_count = 0
    for branch in fuzzer_col_covered_branches:
        if branch not in fuzzer_row_covered_branches:
            unique_branch_count += 1
    return unique_branch_count


def rank_by_average_normalized_score(benchmarks_unique_coverage_list):
    """Returns the rank based on average normalized score on unique coverage."""
    df_list = [df.set_index('fuzzer') for df in benchmarks_unique_coverage_list]
    combined_df = pd.concat(df_list, axis=1).astype(float).T
    scores = data_utils.experiment_rank_by_average_normalized_score(combined_df)
    return scores
