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
import json
import os
import posixpath
import tempfile

import pandas as pd

from analysis import data_utils
from common import filestore_utils
from common import logs


def get_fuzzer_benchmark_key(fuzzer: str, benchmark: str):
    """Returns the key in coverage dict for a pair of fuzzer-benchmark."""
    return fuzzer + ' ' + benchmark


def get_exp_filestore_path_for_fuzzer_benchmark(df, fuzzer, benchmark):
    df = df[df['fuzzer'] == fuzzer]
    df = df[df['benchmark'] == benchmark]
    experiment_filestore_paths = get_exp_filestore_paths(df)
    if len(experiment_filestore_paths) != 1:
        logs.warning(
            'Multiple cov filestores (%s) for this fuzzer (%s) benchmark (%s) pair.',
            experiment_filestore_paths, fuzzer, benchmark)
    return experiment_filestore_paths[0]


def get_exp_filestore_paths(df):
    """Returns the experiment filestore path from |df|."""
    # vc = experiment_df.filestore_path.value_counts()
    # filestore_path = max(list(zip(list(vc.index), list(vc))), key=lambda x: int(x[1]))

    # vc = experiment_df.experiment.value_counts()
    # exp = max(list(zip(list(vc.index), list(vc))), key=lambda x: int(x[1]))

    return list((df['experiment_filestore'] + '/' + df['experiment']).unique())



def get_coverage_report_filestore_path(fuzzer, benchmark, df: pd.DataFrame):
    """Returns the filestore path of the coverage report for |fuzzer| on
    |benchmark| for |df|."""
    exp_filestore_path = get_exp_filestore_path_for_fuzzer_benchmark(
        df, fuzzer, benchmark)
    return posixpath.join(exp_filestore_path, 'coverage', 'reports',
                          benchmark, fuzzer, 'index.html')


def get_fuzzer_benchmark_covered_regions(fuzzer, benchmark, filestore):
    """Accepts a tuple containing the fuzzer, benchmark, filestore and
    temp_dir.
    Returns a tuple containing the fuzzer benchmark key and the regions covered
    by the fuzzer on the benchmark."""
    fuzzer_benchmark_covered_regions = get_fuzzer_covered_regions(
        fuzzer, benchmark, filestore)
    key = get_fuzzer_benchmark_key(fuzzer, benchmark)
    return key, fuzzer_benchmark_covered_regions


def get_covered_regions_dict(experiment_df, pool):
    """Combines json files for different fuzzer-benchmark pair
    in |experiment_df| and returns a dictionary of the covered regions."""
    covered_regions_dict = {}
    benchmarks = experiment_df.benchmark.unique()

    for benchmark in benchmarks:
        benchmark_df = experiment_df[experiment_df.benchmark == benchmark]
        fuzzers = benchmark_df.fuzzer.unique()
        arguments = [
            (fuzzer, benchmark, get_exp_filestore_path_for_fuzzer_benchmark(
                benchmark_df, fuzzer, benchmark))
            for fuzzer in fuzzers]
        print('yo')
        fuzzer_benchmark_covered_regions = list(pool.starmap(
            get_fuzzer_benchmark_covered_regions, arguments))
        for fuzzer_benchmark_key, covered_regions in (
            fuzzer_benchmark_covered_regions):
            covered_regions_dict[fuzzer_benchmark_key] = covered_regions

    print('cov done')
    return covered_regions_dict


def get_fuzzer_covered_regions(fuzzer, benchmark, filestore):
    """Gets the covered regions for |fuzzer| in from the json
    file in the bucket."""
    src_file = posixpath.join(filestore, 'coverage', 'data', benchmark,
                              fuzzer, 'covered_regions.json')
    with tempfile.NamedTemporaryFile() as dst_file:
        if filestore_utils.cp(
            src_file, dst_file.name, expect_zero=False).retcode:
            return {}
        with open(dst_file.name) as json_file:
            return json.load(json_file)


def get_unique_region_dict(benchmark_coverage_dict):
    """Returns a dictionary containing the covering fuzzers for each
    unique region, where the |threshold| defines which regions are unique."""
    region_dict = collections.defaultdict(list)
    unique_region_dict = {}
    threshold_count = 1
    for fuzzer in benchmark_coverage_dict:
        for region in benchmark_coverage_dict[fuzzer]:
            region_dict[region].append(fuzzer)
    for region, fuzzers in region_dict.items():
        if len(fuzzers) <= threshold_count:
            unique_region_dict[region] = fuzzers
    return unique_region_dict


def get_unique_region_cov_df(unique_region_dict, fuzzer_names):
    """Returns a DataFrame where the two columns are fuzzers and the number
    of unique regions covered."""
    fuzzers = collections.defaultdict(int)
    for region in unique_region_dict:
        for fuzzer in unique_region_dict[region]:
            fuzzers[fuzzer] += 1
    dict_to_transform = {'fuzzer': [], 'unique_regions_covered': []}
    for fuzzer in fuzzer_names:
        covered_num = fuzzers[fuzzer]
        dict_to_transform['fuzzer'].append(fuzzer)
        dict_to_transform['unique_regions_covered'].append(covered_num)
    return pd.DataFrame(dict_to_transform)


def get_benchmark_cov_dict(coverage_dict, benchmark):
    """Returns a dictionary to store the covered regions of each fuzzer.
    Uses a set of tuples to store the covered regions."""
    benchmark_cov_dict = {}
    for key_pair, covered_regions in coverage_dict.items():
        current_fuzzer, current_benchmark = key_pair.split()
        if current_benchmark == benchmark:
            covered_regions_in_set = set()
            for region in covered_regions:
                covered_regions_in_set.add(tuple(region))
            benchmark_cov_dict[current_fuzzer] = covered_regions_in_set
    return benchmark_cov_dict


def get_benchmark_aggregated_cov_df(coverage_dict, benchmark):
    """Returns a dataframe where each row represents a fuzzer and its
    aggregated coverage number."""
    dict_to_transform = {'fuzzer': [], 'aggregated_edges_covered': []}
    for key_pair, covered_regions in coverage_dict.items():
        current_fuzzer, current_benchmark = key_pair.split()
        if current_benchmark == benchmark:
            dict_to_transform['fuzzer'].append(current_fuzzer)
            dict_to_transform['aggregated_edges_covered'].append(
                len(covered_regions))
    return pd.DataFrame(dict_to_transform)


def get_pairwise_unique_coverage_table(benchmark_coverage_dict, fuzzers):
    """Returns a table that shows the unique coverage between
    each pair of fuzzers.

    The pairwise unique coverage table is a square matrix where each
    row and column represents a fuzzer, and each cell contains a number
    showing the regions covered by the fuzzer of the column but not by
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


def get_unique_covered_percentage(fuzzer_row_covered_regions,
                                  fuzzer_col_covered_regions):
    """Returns the number of regions covered by the fuzzer of the column
    but not by the fuzzer of the row."""

    unique_region_count = 0
    for region in fuzzer_col_covered_regions:
        if region not in fuzzer_row_covered_regions:
            unique_region_count += 1
    return unique_region_count


def rank_by_average_normalized_score(benchmarks_unique_coverage_list):
    """Returns the rank based on average normalized score on unique coverage."""
    df_list = [df.set_index('fuzzer') for df in benchmarks_unique_coverage_list]
    combined_df = pd.concat(df_list, axis=1).astype(float).T
    scores = data_utils.experiment_rank_by_average_normalized_score(combined_df)
    return scores
