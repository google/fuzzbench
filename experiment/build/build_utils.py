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
"""Module for utility code shared by build submodules."""

import datetime
import os
import sqlite3
import tempfile

from common import experiment_path as exp_path
from common import filestore_utils


def store_build_logs(build_config, build_result):
    """Save build results in the build logs bucket."""
    build_output = (f'Command returned {build_result.retcode}.\n'
                    f'Output: {build_result.output}')
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        tmp.write(build_output)
        tmp.flush()

        build_log_filename = build_config + '.txt'
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(get_build_logs_dir() / build_log_filename))


def store_mua_stats_db(stats_db, benchmark):
    """Save mua stats_db in the mua bucket."""
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        with sqlite3.connect(stats_db) as conn:
            conn.execute('VACUUM INTO ?', (tmp.name, ))
        tmp.flush()
        os.chmod(tmp.name, 0o666)
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(
                get_mua_results_dir() / 'base_build' / benchmark /
                'stats.sqlite'))


def store_mua_results_db(results_db, benchmark, fuzzer, cycle):
    """Save mua stats_db in the mua bucket."""
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        with sqlite3.connect(results_db) as conn:
            conn.execute('VACUUM INTO ?', (tmp.name, ))
        tmp.flush()
        os.chmod(tmp.name, 0o666)
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(get_mua_results_dir() / 'results' / benchmark /
                            fuzzer / f'{cycle}.sqlite'))


def store_mua_build_log(build_output, benchmark, fuzzer, cycle):
    """Save mua stats_db in the mua bucket."""
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        tmp.write(build_output)
        tmp.flush()
        os.chmod(tmp.name, 0o666)
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(get_mua_results_dir() / 'mua_build' / benchmark /
                               fuzzer / f'{cycle}.log'))


def store_mua_run_log(run_output, benchmark, fuzzer, cycle):
    """Save mua stats_db in the mua bucket."""
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        tmp.write(run_output)
        tmp.flush()
        os.chmod(tmp.name, 0o666)
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(get_mua_results_dir() / 'mua_run' / benchmark /
                               fuzzer / f'{cycle}.log'))


def store_report_error_log(report_error):
    """Save mua stats_db in the mua bucket."""
    timestamp_filename = datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S')
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        tmp.write(report_error)
        tmp.flush()
        os.chmod(tmp.name, 0o666)
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(get_report_errors_logs_dir() /
                               f'{timestamp_filename}.log'))


def get_coverage_binaries_dir():
    """Return coverage binaries directory."""
    return exp_path.path('coverage-binaries')


def get_mua_results_dir():
    """Return mua finder binaries directory."""
    return exp_path.path('mua-results')


def get_build_logs_dir():
    """Return build logs directory."""
    return exp_path.path('build-logs')


def get_report_errors_logs_dir():
    """Return report errors logs directory."""
    return exp_path.path('report-errors-logs')
