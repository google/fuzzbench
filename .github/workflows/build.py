import sys
import subprocess

# Don't build php benchmark since it fills up disk in GH actions.
OSS_FUZZ_BENCHMARKS = [
    'bloaty_fuzz_target',
    'curl_curl_fuzzer_http',
    'irssi_server-fuzz',
    'jsoncpp_jsoncpp_fuzzer',
    'libpcap_fuzz_both',
    'mbedtls_fuzz_dtlsclient',
    'openssl_x509',
    'sqlite3_ossfuzz',
    'systemd_fuzz-link-parser',
    'zlib_zlib_uncompress_fuzz',
]

STANDARD_BENCHMARKS = [
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
    'wpantund-2018-02-27',
]


def get_build_targets(benchmarks, fuzzer):
    """Get build targets for |fuzzer| and each benchmark in |benchmarks| to
    pass to make."""
    return [
        'build-%s-%s' % (fuzzer, benchmark)
        for benchmark in benchmarks
    ]


def delete_docker_images():
    result = subprocess.run(['docker', 'images', '-q'], stdout=subprocess.PIPE)
    image_names = result.stdout.splitlines()
    subprocess.run(['docker', 'rmi', '-f'] + image_names, check=False)



def make_builds(build_targets, is_oss_fuzz):
    """Use make to build each target in |build_targets|."""
    success = True
    for target in build_targets:
        if not is_oss_fuzz:
            subprocess.run(['docker', 'pull', 'gcr.io/fuzzbench/base-builder'])
        try:
            subprocess.run(['make', target])
        except subprocess.CalledProcessError:
            success = False
        delete_docker_images()
    return success


def do_build(build_type, fuzzer):
    """Build fuzzer,benchmark pairs for CI."""
    if build_type == 'oss-fuzz':
        benchmarks = OSS_FUZZ_BENCHMARKS
    elif build_type == 'standard':
        benchmarks = STANDARD_BENCHMARKS
    else:
        raise Exception('Invalid build_type: %s' % build_type)

    build_targets = get_build_targets(benchmarks, fuzzer)
    return make_builds(build_targets, build_type == 'oss-fuzz')



def main():
    if len(sys.argv) != 3:
        print('Usage: %s <build_type> <fuzzer>' % sys.argv[0])
        return 1
    build_type = sys.argv[1]
    fuzzer = sys.argv[2]
    result = do_build(build_type, fuzzer)
    return 0 if result else 1

if __name__ == '__main__':
    sys.exit(main())
