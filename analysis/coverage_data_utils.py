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


def get_fuzzer_benchmark_key(fuzzer: str, benchmark: str):
    """Returns the key in coverage dict for a pair of fuzzer-benchmark."""
    return fuzzer + ' ' + benchmark


def get_fuzzer_filestore_path(benchmark_df, fuzzer):
    """Gets the filestore_path for |fuzzer| in |benchmark_df|."""
    fuzzer_df = benchmark_df[benchmark_df.fuzzer == fuzzer]
    filestore_path = fuzzer_df.experiment_filestore.unique()[0]
    exp_name = fuzzer_df.experiment.unique()[0]
    return posixpath.join(filestore_path, exp_name)


def get_covered_regions_dict(experiment_df):
    """Combines json files for different fuzzer-benchmark pair
    in |experiment_df| and returns a dictionary of the covered regions."""
    covered_regions_dict = {}
    benchmarks = experiment_df.benchmark.unique()
    for benchmark in benchmarks:
        benchmark_df = experiment_df[experiment_df.benchmark == benchmark]
        fuzzers = benchmark_df.fuzzer.unique()
        for fuzzer in fuzzers:
            fuzzer_covered_regions = get_fuzzer_covered_regions(
                benchmark_df, benchmark, fuzzer)
            key = get_fuzzer_benchmark_key(fuzzer, benchmark)
            covered_regions_dict[key] = fuzzer_covered_regions

    return covered_regions_dict


def get_fuzzer_covered_regions(benchmark_df, benchmark, fuzzer):
    """Gets the covered regions for |fuzzer| in |benchmark_df| from the json
    file in the bucket."""
    with tempfile.TemporaryDirectory() as temp_dir:
        dst_file = os.path.join(temp_dir, 'tmp.json')
        src_filestore_path = get_fuzzer_filestore_path(benchmark_df, fuzzer)
        src_file = posixpath.join(src_filestore_path, 'coverage', 'data',
                                  benchmark, fuzzer, 'covered_regions.json')
        if filestore_utils.ls(src_file, must_exist=False).retcode:
            # Error occurred, coverage file does not exit. Bail out.
            return {}

        filestore_utils.cp(src_file, dst_file)
        with open(dst_file) as json_file:
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
