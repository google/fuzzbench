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
"""Report generator tool."""

import argparse
import lzma
import os
import sys
import sqlite3
import tempfile

from collections import defaultdict

import pandas as pd

from analysis import data_utils
from analysis import coverage_data_utils
from analysis import experiment_results
from analysis import plotting
from analysis import queries
from analysis import rendering
from common import filesystem
from common import logs
from common import experiment_utils

logger = logs.Logger()

DATA_FILENAME = 'data.csv.gz'


def get_arg_parser():
    """Returns argument parser."""
    parser = argparse.ArgumentParser(description='Report generator.')
    parser.add_argument('experiments', nargs='+', help='Experiment names')
    parser.add_argument(
        '-n',
        '--report-name',
        help='Name of the report. Default: name of the first experiment.')
    parser.add_argument(
        '-t',
        '--report-type',
        choices=['default', 'experimental', 'with_mua'],
        default='default',
        help='Type of the report (which template to use). Default: default.')
    parser.add_argument(
        '-d',
        '--report-dir',
        default='./report',
        help='Directory for writing a report. Default: ./report')
    parser.add_argument(
        '-q',
        '--quick',
        action='store_true',
        default=False,
        help='If set, plots are created faster, but contain less details.')
    parser.add_argument('-mua',
                        '--mutation-analysis',
                        action='store_true',
                        default=False,
                        help='If set, mutation analysis report is created.')
    parser.add_argument(
        '--log-scale',
        action='store_true',
        default=False,
        help='If set, the time axis of the coverage growth plot is log scale.')
    parser.add_argument(
        '-b',
        '--benchmarks',
        nargs='*',
        help='Names of the benchmarks to include in the report.')
    parser.add_argument(
        '-e',
        '--end-time',
        default=None,
        type=int,
        help=('The last time (in seconds) during an experiment to include in '
              'the report.'))
    parser.add_argument('-f',
                        '--fuzzers',
                        nargs='*',
                        help='Names of the fuzzers to include in the report.')
    parser.add_argument(
        '-xb',
        '--experiment-benchmarks',
        nargs='*',
        help='Names of the benchmarks to include in the report.')
    parser.add_argument(
        '-cov',
        '--coverage-report',
        action='store_true',
        default=False,
        help='If set, clang coverage reports and differential plots are shown.')

    # It doesn't make sense to clobber and label by experiment, since nothing
    # can get clobbered like this.
    mutually_exclusive_group = parser.add_mutually_exclusive_group()
    mutually_exclusive_group.add_argument(
        '-l',
        '--label-by-experiment',
        action='store_true',
        default=False,
        help='If set, then the report will track progress made in experiments')
    mutually_exclusive_group.add_argument(
        '-m',
        '--merge-with-clobber',
        action='store_true',
        default=False,
        help=('When generating a report from multiple experiments, and trials '
              'exist for fuzzer-benchmark pairs in multiple experiments, only '
              'include trials for that pair from the last experiment. For '
              'example, if experiment "A" has all fuzzers but experiment "B" '
              'has used an updated version of afl++, this option allows you to '
              'get a report of all trials in "A" except for afl++ and all the '
              'trials from "B". "Later experiments" are those whose names come '
              'later when passed to this script.'))
    mutually_exclusive_group.add_argument(
        '-p',
        '--merge-with-clobber-nonprivate',
        action='store_true',
        default=False,
        help=('Does --merge-with-clobber but includes all experiments that are '
              'not private. See help for --merge-with-clobber for more '
              'details.'))
    parser.add_argument(
        '-c',
        '--from-cached-data',
        action='store_true',
        default=False,
        help=('If set, and the experiment data is already cached, '
              'don\'t query the database again to get the data.'))

    return parser


def get_experiment_data(experiment_names,
                        main_experiment_name,
                        from_cached_data,
                        data_path,
                        main_experiment_benchmarks=None):
    """Helper function that reads data from disk or from the database. Returns a
    dataframe and the experiment description."""
    if from_cached_data and os.path.exists(data_path):
        logger.info('Reading experiment data from %s.', data_path)
        experiment_df = pd.read_csv(data_path)
        logger.info('Done reading data from %s.', data_path)
        return experiment_df, 'from cached data'
    logger.info('Reading experiment data from db.')
    experiment_df = queries.get_experiment_data(experiment_names,
                                                main_experiment_benchmarks)
    # experiment_df.to_csv('/tmp/experiment-data/experiment_data.csv')
    logger.info('Done reading experiment data from db.')
    description = queries.get_experiment_description(main_experiment_name)
    return experiment_df, description


def modify_experiment_data_if_requested(  # pylint: disable=too-many-arguments
        experiment_df, experiment_names, benchmarks, fuzzers,
        label_by_experiment, end_time, merge_with_clobber):
    """Helper function that returns a copy of |experiment_df| that is modified
    based on the other parameters. These parameters come from values specified
    by the user on the command line (or callers to generate_report)."""
    if benchmarks:
        # Filter benchmarks if requested.
        logger.debug('Filter included benchmarks: %s.', benchmarks)
        experiment_df = data_utils.filter_benchmarks(experiment_df, benchmarks)

    if not experiment_df['benchmark'].empty:
        # Filter benchmarks in experiment DataFrame.
        unique_benchmarks = experiment_df['benchmark'].unique().tolist()
        logger.debug('Filter experiment_df benchmarks: %s.', unique_benchmarks)
        experiment_df = data_utils.filter_benchmarks(experiment_df,
                                                     unique_benchmarks)

    if fuzzers is not None:
        # Filter fuzzers if requested.
        experiment_df = data_utils.filter_fuzzers(experiment_df, fuzzers)

    if label_by_experiment:
        # Label each fuzzer by the experiment it came from to easily compare the
        # same fuzzer accross multiple experiments.
        experiment_df = data_utils.label_fuzzers_by_experiment(experiment_df)

    if end_time is not None:
        # Cut off the experiment at a specific time if requested.
        experiment_df = data_utils.filter_max_time(experiment_df, end_time)

    if merge_with_clobber:
        # Merge with clobber if requested.
        experiment_df = data_utils.clobber_experiments_data(
            experiment_df, experiment_names)

    return experiment_df


def normalized_timestamps(timestamps):
    """Normalize timestamps."""
    print(timestamps[0])
    seed_timestamp_file = next(
        (tt for tt in timestamps if tt[2] == '<seed_entry>'), None)
    try:
        min_timestamp_file = min(
            (tt for tt in timestamps if tt[2] != '<seed_entry>'),
            key=lambda x: x[3])
    except ValueError:
        min_timestamp_file = seed_timestamp_file
    try:
        max_timestamp_file = max(
            (tt for tt in timestamps if tt[2] != '<seed_entry>'),
            key=lambda x: x[3])
    except ValueError:
        max_timestamp_file = seed_timestamp_file
    # print(len(timestamps))
    # print('min_timestamp', min_timestamp_file)
    # print('max_timestamp', max_timestamp_file)
    min_timestamp = min_timestamp_file[3]
    max_timestamp = max_timestamp_file[3]
    print('max_timestamp - min_timestamp', max_timestamp - min_timestamp)
    timestamps_normalized = {}
    for _hashname, input_file_id, input_file, timestamp in timestamps:
        if input_file == '<seed_entry>':
            timestamps_normalized[input_file_id] = 0
        else:
            timestamps_normalized[input_file_id] = timestamp - min_timestamp

    timespan = max_timestamp - min_timestamp
    return timestamps_normalized, timespan


def get_first_covered_killed(results, timestamps_map):
    """Get first covered and killed mutant."""
    ordered_inputs = sorted(results, key=lambda x: timestamps_map[x[0]])
    mut_result_times = defaultdict(lambda: {'seen': None, 'killed': None})
    for ordered_input in ordered_inputs:
        input_file_id, mut_id, skipped, killed = ordered_input[:4]
        if skipped:
            continue
        if mut_id not in mut_result_times:
            mut_result_times[mut_id]['seen'] = timestamps_map[input_file_id]
        if killed:
            assert mut_id in mut_result_times
            if mut_result_times[mut_id]['killed'] is None:
                mut_result_times[mut_id]['killed'] = timestamps_map[
                    input_file_id]
    return mut_result_times


def get_timeline(time_covered_killed, timespan, fuzz_target, benchmark,
                 fuzzer_name, trial_num, cycle):
    """Create timeline regarding covering and killing of mutants."""
    if timespan == 0:
        max_time_base = 1
    else:
        max_time_base = 16
    normalized_time_elem = timespan / (max_time_base**2)
    time = 'time'
    count_seen = 'seen'
    count_killed = 'killed'
    print(f'{time:<10} {count_seen:<7} {count_killed:<7}')
    res = []
    for time_base in range(1, max_time_base + 1):
        time = normalized_time_elem * (time_base**2)
        count_seen = 0
        count_killed = 0
        for _mut_id, times in time_covered_killed.items():
            if times['seen'] is not None and times['seen'] <= time:
                count_seen += 1
            if times['killed'] is not None and times['killed'] <= time:
                count_killed += 1
        print(f'{time:8.2f}s: {count_seen:>7} {count_killed:>7}')
        res.append((fuzz_target, benchmark, fuzzer_name, trial_num, cycle, time,
                    count_seen, count_killed))
    return res


def load_result_db(res_db_path):
    """Load result.sqlite database."""
    with tempfile.NamedTemporaryFile() as tmp_file:
        with lzma.open(res_db_path) as res_db:
            tmp_file.write(res_db.read())
        tmp_file.flush()
        tmp_file.seek(0)
        with sqlite3.connect(tmp_file.name) as conn:
            run_info = conn.execute(
                'SELECT benchmark, fuzz_target, fuzzer, trial_num FROM run_info'
            ).fetchall()
            results = conn.execute('''SELECT
                    input_file_id,
                    mut_id,
                    skipped,
                    killed,
                    orig_retcode,
                    mutant_retcode,
                    orig_runtime,
                    mutant_runtime,
                    orig_timed_out,
                    mutant_timed_out
                FROM results''').fetchall()
            timestamps = conn.execute(
                '''SELECT hashname, input_file_id, input_file, timestamp
                 FROM timestamps''').fetchall()
    return run_info, results, timestamps


def get_mua_results(experiment_df):
    """Get mutation analysis results for each fuzzer in each trial to use in
    the report."""

    #get relationship between trial_id and benchmark from df
    trial_dict = experiment_df.set_index('trial_id')['benchmark'].to_dict()

    #logger.info(f'trial_dict: {trial_dict}')

    experiment_data_dir = experiment_utils.get_experiment_filestore_path()
    results_data_dir = f'{experiment_data_dir}/mua-results/results'

    if not os.path.isdir(results_data_dir):
        logger.warning('''mua-results/results dir does not exist,
              stopping mua report creation''')
        return None

    fuzzer_pds = defaultdict(list)

    for trial in trial_dict.keys():

        print(experiment_data_dir)
        mua_result_db_file =  f'{results_data_dir}/{trial}/' \
            'results.sqlite.lzma'
        logger.info('mua_result_db_file:')
        logger.info(mua_result_db_file)
        run_info, results, timestamps = load_result_db(mua_result_db_file)
        assert len(run_info) == 1
        benchmark, fuzz_target, fuzzer, trial_num = run_info[0]
        print(benchmark, fuzz_target, fuzzer, trial_num, trial)
        timestamps_map, timespan = normalized_timestamps(timestamps)

        results = [
            rr for rr in results if timestamps_map.get(rr[0]) is not None
        ]
        time_covered_killed = get_first_covered_killed(results, timestamps_map)
        timeline = get_timeline(time_covered_killed, timespan, fuzz_target,
                                benchmark, fuzzer, trial_num, trial)
        pd_timeline = pd.DataFrame(timeline,
                                   columns=[
                                       'fuzz_target', 'benchmark', 'fuzzer',
                                       'trial_num', 'cycle', 'time', 'seen',
                                       'killed'
                                   ])
        fuzzer_pds[fuzzer].append(pd_timeline)

    num_trials = None
    for fuzzer in fuzzer_pds.keys():
        if num_trials is None:
            num_trials = len(fuzzer_pds[fuzzer])
        else:
            assert num_trials == len(fuzzer_pds[fuzzer])

    num_fuzzers = len(fuzzer_pds)

    print(num_trials, num_fuzzers)

    return (num_trials, fuzzer_pds)


# pylint: disable=too-many-arguments,too-many-locals
def generate_report(experiment_names,
                    report_directory,
                    report_name=None,
                    label_by_experiment=False,
                    benchmarks=None,
                    fuzzers=None,
                    report_type='default',
                    quick=False,
                    log_scale=False,
                    from_cached_data=False,
                    in_progress=False,
                    end_time=None,
                    merge_with_clobber=False,
                    merge_with_clobber_nonprivate=False,
                    coverage_report=False,
                    experiment_benchmarks=None,
                    mutation_analysis=False):
    """Generate report helper."""
    if merge_with_clobber_nonprivate:
        experiment_names = (
            queries.add_nonprivate_experiments_for_merge_with_clobber(
                experiment_names))
        merge_with_clobber = True

    main_experiment_name = experiment_names[0]
    report_name = report_name or main_experiment_name

    filesystem.create_directory(report_directory)

    data_path = os.path.join(report_directory, DATA_FILENAME)
    experiment_df, experiment_description = get_experiment_data(
        experiment_names,
        main_experiment_name,
        from_cached_data,
        data_path,
        main_experiment_benchmarks=experiment_benchmarks)

    # TODO(metzman): Ensure that each experiment is in the df. Otherwise there
    # is a good chance user misspelled something.
    data_utils.validate_data(experiment_df)

    experiment_df = modify_experiment_data_if_requested(
        experiment_df, experiment_names, benchmarks, fuzzers,
        label_by_experiment, end_time, merge_with_clobber)

    # experiment_df.to_csv('/tmp/experiment-data/out.csv')

    #TODO: make this work with a single fuzzer selected
    # Add |bugs_covered| column prior to export.
    experiment_df = data_utils.add_bugs_covered_column(experiment_df)

    # Save the filtered raw data along with the report if not using cached data
    # or if the data does not exist.
    if not from_cached_data or not os.path.exists(data_path):
        experiment_df.to_csv(data_path)

    # Load the coverage json summary file.
    coverage_dict = {}
    if coverage_report:
        logger.info('Generating coverage report info.')
        coverage_dict = coverage_data_utils.get_covered_branches_dict(
            experiment_df)
        logger.info('Finished generating coverage report info.')

    if mutation_analysis:
        # TODO get_mua_results(main_experiment_name, fuzzers,
        # experiment_benchmarks, experiment_df)
        #fuzzers = ['afl', 'libfuzzer']
        mua_results = get_mua_results(experiment_df)
    else:
        mua_results = None

    fuzzer_names = experiment_df.fuzzer.unique()
    plotter = plotting.Plotter(fuzzer_names, quick, log_scale)
    experiment_ctx = experiment_results.ExperimentResults(
        experiment_df,
        coverage_dict,
        report_directory,
        plotter,
        mua_results=mua_results,
        experiment_name=report_name)

    template = report_type + '.html'
    logger.info('Rendering HTML report.')
    detailed_report = rendering.render_report(experiment_ctx, template,
                                              in_progress, coverage_report,
                                              experiment_description)
    logger.info('Done rendering HTML report.')

    filesystem.write(os.path.join(report_directory, 'index.html'),
                     detailed_report)


def main():
    """Generates report."""
    logs.initialize()

    parser = get_arg_parser()
    args = parser.parse_args()

    generate_report(experiment_names=args.experiments,
                    report_directory=args.report_dir,
                    report_name=args.report_name,
                    label_by_experiment=args.label_by_experiment,
                    benchmarks=args.benchmarks,
                    fuzzers=args.fuzzers,
                    report_type=args.report_type,
                    quick=args.quick,
                    log_scale=args.log_scale,
                    from_cached_data=args.from_cached_data,
                    end_time=args.end_time,
                    merge_with_clobber=args.merge_with_clobber,
                    coverage_report=args.coverage_report,
                    experiment_benchmarks=args.experiment_benchmarks,
                    mutation_analysis=args.mutation_analysis)


if __name__ == '__main__':
    sys.exit(main())
