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
import datetime
from unittest import mock

import pytest

from common import utils
from service import automatic_run_experiment

# pylint: disable=invalid-name,unused-argument

# A valid experiment name.
EXPERIMENT = '2020-01-01'

EXPERIMENT_REQUESTS = [{
    'experiment': datetime.date(2020, 6, 8),
    'fuzzers': ['aflplusplus', 'libfuzzer'],
}, {
    'experiment': datetime.date(2020, 6, 5),
    'fuzzers': ['honggfuzz', 'afl'],
    'description': 'Test experiment',
    'oss_fuzz_corpus': True,
}]


@mock.patch('experiment.run_experiment.start_experiment')
@mock.patch('common.logs.warning')
@mock.patch('service.automatic_run_experiment._get_requested_experiments')
def test_run_requested_experiment_pause_service(
        mocked_get_requested_experiments, mocked_warning,
        mocked_start_experiment, db):
    """Tests that run_requested_experiment doesn't run an experiment when a
    pause is requested."""
    experiment_requests_with_pause = EXPERIMENT_REQUESTS.copy()
    experiment_requests_with_pause.append(
        automatic_run_experiment.PAUSE_SERVICE_KEYWORD)
    mocked_get_requested_experiments.return_value = (
        experiment_requests_with_pause)

    assert (automatic_run_experiment.run_requested_experiment(dry_run=False) is
            None)
    mocked_warning.assert_called_with(
        'Pause service requested, not running experiment.')
    assert mocked_start_experiment.call_count == 0


@mock.patch('experiment.run_experiment.start_experiment')
@mock.patch('service.automatic_run_experiment._get_requested_experiments')
def test_run_requested_experiment(mocked_get_requested_experiments,
                                  mocked_start_experiment, db):
    """Tests that run_requested_experiment starts and stops the experiment
    properly."""
    mocked_get_requested_experiments.return_value = EXPERIMENT_REQUESTS
    expected_experiment_name = '2020-06-05'
    expected_fuzzers = ['honggfuzz', 'afl']
    automatic_run_experiment.run_requested_experiment(dry_run=False)
    expected_config_file = os.path.join(utils.ROOT_DIR, 'service',
                                        'experiment-config.yaml')

    expected_benchmarks = sorted([
        'arduinojson_json_fuzzer',
        'assimp_assimp_fuzzer',
        'astc-encoder_fuzz_astc_physical_to_symbolic',
        'bloaty_fuzz_target',
        'botan_tls_server',
        'brotli_decode_fuzzer',
        'curl_curl_fuzzer_http',
        'double-conversion_string_to_double_fuzzer',
        'draco_draco_pc_decoder_fuzzer',
        'dropbear_fuzzer-postauth_nomaths',
        'firestore_firestore_serializer_fuzzer',
        'fmt_chrono-duration-fuzzer',
        'guetzli_guetzli_fuzzer',
        'icu_unicode_string_codepage_create_fuzzer',
        'jansson_json_load_dump_fuzzer',
        'jsoncpp_jsoncpp_fuzzer',
        'libpcap_fuzz_both',
        'libpcap_fuzz_filter_98b0a2',
        'libxslt_xpath',
        'mbedtls_fuzz_dtlsclient',
        'openssl_x509',
        'sqlite3_ossfuzz',
        'systemd_fuzz-link-parser',
        'systemd_fuzz-network-parser_288baf',
        'zlib_zlib_uncompress_fuzzer',
        'freetype2_ftfuzzer',
        'harfbuzz_hb-shape-fuzzer',
        'lcms_cms_transform_fuzzer',
        'lcms_cms_transform_all_fuzzer_97d37d',
        'libaom_av1_dec_fuzzer',
        'libcoap_pdu_parse_fuzzer',
        'libhevc_hevc_dec_fuzzer',
        'libjpeg-turbo_libjpeg_turbo_fuzzer',
        'libpng_libpng_read_fuzzer',
        'librdkafka_fuzz_regex',
        'libxml2_xml',
        'openh264_decoder_fuzzer',
        'openthread_ot-ip6-send-fuzzer',
        'proj4_proj_crs_to_crs_fuzzer',
        're2_fuzzer',
        'stb_stbi_read_fuzzer',
        'vorbis_decode_fuzzer',
        'woff2_convert_woff2ttf_fuzzer',
    ])
    expected_call = mock.call(
        expected_experiment_name,
        expected_config_file,
        expected_benchmarks,
        expected_fuzzers,
        description='Test experiment',
        concurrent_builds=(automatic_run_experiment.CONCURRENT_BUILDS),
        oss_fuzz_corpus=True)
    start_experiment_call_args = mocked_start_experiment.call_args_list
    assert len(start_experiment_call_args) == 1
    start_experiment_call_args = start_experiment_call_args[0]
    assert start_experiment_call_args == expected_call


@pytest.mark.parametrize(
    ('name', 'expected_result'), [('02000-1-1', False), ('2020-1-1', False),
                                  ('2020-01-01', True),
                                  ('2020-01-01-aflplusplus', True),
                                  ('2020-01-01-1', True)])
def test_validate_experiment_name(name, expected_result):
    """Tests that validate experiment name returns True for valid names and
    False for names that are not valid."""
    assert (automatic_run_experiment.validate_experiment_name(name) ==
            expected_result)


# Call the parameter exp_request instead of request because pytest reserves it.
@pytest.mark.parametrize(
    ('exp_request', 'expected_result'),
    [
        ({
            'experiment': EXPERIMENT,
            'fuzzers': ['afl']
        }, True),
        # Not a dict.
        (1, False),
        # No fuzzers.
        ({
            'experiment': EXPERIMENT,
            'fuzzers': []
        }, False),
        # No fuzzers.
        ({
            'experiment': EXPERIMENT
        }, False),
        # No experiment.
        ({
            'fuzzers': ['afl']
        }, False),
        # Invalid experiment name for request.
        ({
            'experiment': 'invalid',
            'fuzzers': ['afl']
        }, False),
        # Invalid experiment name.
        ({
            'experiment': 'i' * 100,
            'fuzzers': ['afl']
        }, False),
        # Nonexistent fuzzers.
        ({
            'experiment': EXPERIMENT,
            'fuzzers': ['nonexistent-fuzzer']
        }, False),
        # Invalid fuzzers.
        (
            {
                'experiment': EXPERIMENT,
                'fuzzers': ['1']  # Need to make this exist.
            },
            False),
        # Invalid description.
        ({
            'experiment': EXPERIMENT,
            'fuzzers': ['afl'],
            'description': 1,
        }, False),
        # Invalid oss_fuzz_corpus flag.
        ({
            'experiment': EXPERIMENT,
            'fuzzers': ['afl'],
            'oss_fuzz_corpus': 'invalid',
        }, False),
    ])
def test_validate_experiment_requests(exp_request, expected_result):
    """Tests that validate_experiment_requests returns True for valid fuzzres
    and False for invalid ones."""
    assert (automatic_run_experiment.validate_experiment_requests([exp_request])
            is expected_result)


def test_validate_experiment_requests_duplicate_experiments():
    """Tests that validate_experiment_requests returns False if the experiment
    names are duplicated."""
    requests = [
        {
            'experiment': EXPERIMENT,
            'fuzzers': ['afl']
        },
        {
            'experiment': EXPERIMENT,
            'fuzzers': ['libfuzzer']
        },
    ]
    assert not automatic_run_experiment.validate_experiment_requests(requests)


def test_validate_experiment_requests_one_valid_one_invalid():
    """Tests that validate_experiment_requests returns False even if some
    requests are valid."""
    requests = [
        {
            'experiment': EXPERIMENT,
            'fuzzers': ['afl']
        },
        {
            'experiment': '2020-02-02',
            'fuzzers': []
        },
    ]
    assert not automatic_run_experiment.validate_experiment_requests(requests)
