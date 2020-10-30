#!/usr/bin/env python3
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
"""Script for building and briefly running fuzzer,benchmark pairs in CI."""
import sys
import subprocess

from common import retry
from experiment.build import builder
from src_analysis import change_utils
from src_analysis import diff_utils

ALWAYS_BUILD_FUZZER = 'afl'
NUM_RETRIES = 2
RETRY_DELAY = 60

# Don't build php benchmark since it fills up disk in GH actions.
OSS_FUZZ_BENCHMARKS = {
    'bloaty_fuzz_target',
    'curl_curl_fuzzer_http',
    'jsoncpp_jsoncpp_fuzzer',
    'libpcap_fuzz_both',
    'libxslt_xpath',
    'mbedtls_fuzz_dtlsclient',
    'openssl_x509',
    'sqlite3_ossfuzz',
    'systemd_fuzz-link-parser',
    'zlib_zlib_uncompress_fuzzer',
}

STANDARD_BENCHMARKS = {
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
}

BUG_BENCHMARKS = {
    'harfbuzz_hb-subset-fuzzer',
    'libhevc_hevc_dec_fuzzer',
    'matio_matio_fuzzer',
    'ndpi_fuzz_ndpi_reader',
    'openh264_decoder_fuzzer',
    'stb_stbi_read_fuzzer',
    'wabt_wasm2wat_fuzzer',
}


def get_make_target(fuzzer, benchmark):
    """Return test target for a fuzzer and benchmark."""
    return 'test-run-%s-%s' % (fuzzer, benchmark)


def delete_docker_images():
    """Delete docker images."""
    # TODO(metzman): Don't delete base-runner/base-builder so it
    # doesn't need to be pulled for every target.

    result = subprocess.run(['docker', 'ps', '-a', '-q'],
                            stdout=subprocess.PIPE,
                            check=True)
    container_ids = result.stdout.splitlines()
    subprocess.run(['docker', 'rm', '-f'] + container_ids, check=False)

    result = subprocess.run(['docker', 'images', '-a', '-q'],
                            stdout=subprocess.PIPE,
                            check=True)
    image_ids = result.stdout.splitlines()
    subprocess.run(['docker', 'rmi', '-f'] + image_ids, check=False)

    # Needed for BUILDKIT to clear build cache & avoid insufficient disk space.
    subprocess.run(['docker', 'builder', 'prune', '-f'], check=False)


@retry.wrap(NUM_RETRIES, RETRY_DELAY, 'run_command')
def run_command(command):
    """Runs a command with retries until success."""
    print('Running command:', ' '.join(command))
    subprocess.check_call(command)


def make_builds(benchmarks, fuzzer):
    """Use make to test the fuzzer on each benchmark in |benchmarks|."""
    fuzzer_benchmark_pairs = builder.get_fuzzer_benchmark_pairs([fuzzer],
                                                                benchmarks)
    # Sort benchmarks so that they get built in a deterministic order.
    fuzzer_benchmark_pairs = sorted(fuzzer_benchmark_pairs,
                                    key=lambda pair: pair[1])
    print('Building fuzzer-benchmark pairs: {}'.format(fuzzer_benchmark_pairs))
    for _, benchmark in fuzzer_benchmark_pairs:
        make_target = get_make_target(fuzzer, benchmark)
        make_command = ['make', 'RUNNING_ON_CI=yes', '-j', make_target]
        run_command(make_command)

        # Delete docker images so disk doesn't fill up.
        delete_docker_images()

    return True


def do_build(build_type, fuzzer, always_build):
    """Build fuzzer,benchmark pairs for CI."""
    if build_type == 'oss-fuzz':
        benchmarks = OSS_FUZZ_BENCHMARKS
    elif build_type == 'standard':
        benchmarks = STANDARD_BENCHMARKS
    elif build_type == 'bug':
        benchmarks = BUG_BENCHMARKS
    else:
        raise Exception('Invalid build_type: %s' % build_type)

    if always_build:
        # Always do a build if always_build is True.
        return make_builds(benchmarks, fuzzer)

    changed_files = diff_utils.get_changed_files()
    changed_fuzzers = change_utils.get_changed_fuzzers(changed_files)
    if fuzzer in changed_fuzzers:
        # Otherwise if fuzzer is in changed_fuzzers then build it with all
        # benchmarks, the change could have affected any benchmark.
        return make_builds(benchmarks, fuzzer)

    # Otherwise, only build benchmarks that have changed.
    changed_benchmarks = set(change_utils.get_changed_benchmarks(changed_files))
    benchmarks = benchmarks.intersection(changed_benchmarks)
    return make_builds(benchmarks, fuzzer)


def main():
    """Build OSS-Fuzz or standard benchmarks with a fuzzer."""
    if len(sys.argv) != 3:
        print('Usage: %s <build_type> <fuzzer>' % sys.argv[0])
        return 1
    build_type = sys.argv[1]
    fuzzer = sys.argv[2]
    always_build = ALWAYS_BUILD_FUZZER == fuzzer
    result = do_build(build_type, fuzzer, always_build)
    return 0 if result else 1


if __name__ == '__main__':
    sys.exit(main())
