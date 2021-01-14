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
"""Utility DetailedCoverageData class and functions for report generation on
segment and function coverage for the entire experiment
(all Fuzzer-benchmark-trial combinations)."""

import os
import hashlib

import pandas as pd

from common import experiment_path as exp_path
from common import filestore_utils
from experiment.measurer import coverage_utils


class DetailedCoverageData:  # pylint: disable=too-many-instance-attributes
    """Maintains segment and function coverage information, and writes this
    information to CSV files."""

    def __init__(self):
        """Constructor"""
        self.segment_entries = []
        self.function_entries = []
        self.fuzzer_names = {}
        self.benchmark_names = {}
        self.function_names = {}
        self.file_names = {}

        # Will be initialized upon done_adding_entries().
        self.segment_df = None
        self.function_df = None
        self.name_df = None

    def add_function_entry(  # pylint: disable=too-many-arguments
            self, benchmark, fuzzer, trial_id, function, function_hits, time):
        """Adds an entry to the function_df."""
        fuzzer_id = self.name_to_id(fuzzer)
        benchmark_id = self.name_to_id(benchmark)
        function_id = self.name_to_id(function)
        self.fuzzer_names[fuzzer] = fuzzer_id
        self.benchmark_names[benchmark] = benchmark_id
        self.function_names[function] = function_id

        function_entry = [
            benchmark_id, fuzzer_id, trial_id, time, function_id, function_hits
        ]
        self.function_entries.append(function_entry)

    def add_segment_entry(  # pylint: disable=too-many-arguments
            self, benchmark, fuzzer, trial_id, file_name, line, column, time):
        """Adds an entry to the segment_df."""
        fuzzer_id = self.name_to_id(fuzzer)
        benchmark_id = self.name_to_id(benchmark)
        file_id = self.name_to_id(file_name)
        self.fuzzer_names[fuzzer] = fuzzer_id
        self.benchmark_names[benchmark] = benchmark_id
        self.file_names[file_name] = file_id

        segment_entry = [
            benchmark_id, fuzzer_id, trial_id, time, file_id, line, column
        ]
        self.segment_entries.append(segment_entry)

    def done_adding_entries(self):
        """Generates the data frames from the individual entries."""

        if len(self.segment_entries) == 0:
            coverage_utils.logger.error(
                'Finalizing, but no entries were added.')
            return

        self.segment_df = pd.DataFrame(self.segment_entries,
                                       columns=[
                                           'benchmark', 'fuzzer', 'trial',
                                           'time', 'file', 'line', 'column'
                                       ])
        self.function_df = pd.DataFrame(self.function_entries,
                                        columns=[
                                            'benchmark', 'fuzzer', 'trial',
                                            'time', 'function', 'hits'
                                        ])

        name_entries = []
        for name in self.benchmark_names:
            name_entries.append([self.benchmark_names[name], name, 'benchmark'])
        for name in self.fuzzer_names:
            name_entries.append([self.fuzzer_names[name], name, 'fuzzer'])
        for name in self.function_names:
            name_entries.append([self.function_names[name], name, 'function'])
        for name in self.file_names:
            name_entries.append([self.file_names[name], name, 'file'])
        self.name_df = pd.DataFrame(name_entries,
                                    columns=['id', 'name', 'type'])

    def name_to_id(self, name):  # pylint: disable=no-self-use
        """Generates a hash for the name. This is to save disk storage"""
        return hashlib.md5(name.encode()).hexdigest()[:7]

    def remove_redundant_entries(self):
        """Removes redundant entries in segment_df. Before calling this
        method, for each time stamp, segment_df contains all segments that are
        covered in this time stamp. After calling this method, for each time
        stamp, segment_df only contains segments that have been covered since
        the previous time stamp. This significantly reduces the size of the
        resulting CSV file."""
        try:
            # Drop duplicates but with different timestamps in segment data.
            self.segment_df = self.segment_df.sort_values(by=['time'])
            self.segment_df = self.segment_df.drop_duplicates(
                subset=self.segment_df.columns.difference(['time']),
                keep='first')
            self.name_df = self.name_df.drop_duplicates(keep='first')

        except (ValueError, KeyError, IndexError):
            coverage_utils.logger.error(
                'Error occurred when removing duplicates.')

    def generate_csv_files(self):
        """Generates three compressed CSV files containing coverage information
        for all fuzzers, benchmarks, and trials. To maintain a small file size,
        all strings, such as file and function names, are referenced by id and
        resolved in 'names.csv'."""

        # Clean and prune experiment-specific data frames.
        self.remove_redundant_entries()

        # Write CSV files to filestore.
        def csv_filestore_helper(file_name, df):
            """Helper method for storing csv files in filestore."""
            src = os.path.join(coverage_utils.get_coverage_info_dir(), 'data',
                               file_name)
            dst = exp_path.filestore(src)
            df.to_csv(src, index=False, compression='infer')
            filestore_utils.cp(src, dst)

        csv_filestore_helper('functions.csv.gz', self.function_df)
        csv_filestore_helper('segments.csv.gz', self.segment_df)
        csv_filestore_helper('names.csv.gz', self.name_df)


def extract_segments_and_functions_from_summary_json(  # pylint: disable=too-many-locals
        summary_json_file, benchmark, fuzzer, trial_id, time):
    """Return a trial-specific data frame container with segment and function
     coverage information given a trial-specific coverage summary json file."""

    trial_coverage_df_container = DetailedCoverageData()

    try:
        coverage_info = coverage_utils.get_coverage_infomation(
            summary_json_file)
        # Extract coverage information for functions.
        for function_data in coverage_info['data'][0]['functions']:
            trial_coverage_df_container.add_function_entry(
                benchmark, fuzzer, trial_id, function_data['name'],
                function_data['count'], time)

        # Extract coverage information for segments.
        for file in coverage_info['data'][0]['files']:
            for segment in file['segments']:
                if segment[2] != 0:  # Segment hits.
                    trial_coverage_df_container.add_segment_entry(
                        benchmark,
                        fuzzer,
                        trial_id,
                        file['filename'],
                        segment[0],  # Segment line.
                        segment[1],  # Segment column.
                        time)

    except (ValueError, KeyError, IndexError):
        coverage_utils.logger.error(
            'Failed when extracting trial-specific segment and function '
            'information from coverage summary.')

    trial_coverage_df_container.done_adding_entries()
    return trial_coverage_df_container
