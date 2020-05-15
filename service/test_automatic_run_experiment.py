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
"""Tests for automatic_run_experiment.py"""
import os
from unittest import mock

from common import utils
from service import automatic_run_experiment

# pylint: disable=invalid-name,unused-argument


@mock.patch('experiment.run_experiment.start_experiment')
@mock.patch('experiment.stop_experiment.stop_experiment')
@mock.patch(
    'src_analysis.change_utils.get_changed_fuzzers_since_last_experiment')
@mock.patch('service.automatic_run_experiment.get_experiment_name')
def test_run_diff_experiment(mocked_get_experiment_name,
                             mocked_get_changed_fuzzers_since_last_experiment,
                             mocked_stop_experiment, mocked_start_experiment,
                             db):
    """Tests that run_diff_experiment starts and stops the experiment
    properly."""
    expected_experiment_name = 'myexperiment'
    mocked_get_experiment_name.return_value = expected_experiment_name
    fuzzers = ['afl', 'aflplusplus']
    mocked_get_changed_fuzzers_since_last_experiment.return_value = fuzzers
    automatic_run_experiment.run_diff_experiment(False)
    expected_config_file = os.path.join(utils.ROOT_DIR, 'service',
                                        'experiment-config.yaml')

    def sort_key(dictionary):
        return dictionary['fuzzer']

    expected_fuzzer_configs = list(
        sorted([{
            'fuzzer': fuzzer
        } for fuzzer in fuzzers], key=sort_key))
    expected_benchmarks = [
        'bloaty_fuzz_target',
        'curl_curl_fuzzer_http',
        'jsoncpp_jsoncpp_fuzzer',
        'libpcap_fuzz_both',
        'mbedtls_fuzz_dtlsclient',
        'openssl_x509',
        'sqlite3_ossfuzz',
        'systemd_fuzz-link-parser',
        'zlib_zlib_uncompress_fuzzer',
        'freetype2-2017',
        'harfbuzz-1.3.2',
        'lcms-2017-03-21',
        'libjpeg-turbo-07-2017',
        'libpng-1.2.56',
        'libxml2-v2.9.2',
        'openthread-2019-12-23',
        'proj4-2017-08-14',
        're2-2014-12-09',
        'vorbis-2017-12-11',
        'woff2-2016-05-06',
    ]
    start_experiment_call_args = mocked_start_experiment.call_args_list
    expected_calls = [
        mock.call(expected_experiment_name, expected_config_file,
                  expected_benchmarks, expected_fuzzer_configs)
    ]
    assert len(start_experiment_call_args) == 1
    start_experiment_call_args[0][0][3].sort(key=sort_key)
    assert start_experiment_call_args == expected_calls
    mocked_stop_experiment.assert_called_with(expected_experiment_name,
                                              expected_config_file)
