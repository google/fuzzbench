"""Tests Config class."""


from dacite import from_dict

from queue_experiment.config import Config


CONFIG_DATA = {
        'local_experiment': True,
        'docker_registry': 'gcr.io/fuzzbench',
        'experiment_filestore': '/tmp/experiment_data',
        'report_filestore': '/tmp/report_data',

        'benchmarks': ['zlib_zlib_uncompress_fuzzer', 'jsoncpp_jsoncpp_fuzzer'],
        'fuzzers': ['afl', 'libfuzzer'],
        'trials': 2,
        'max_total_time': 3600,
        'experiment': 'testname'
    }

CONFIG_OBJ = Config(
        local_experiment=True,
        docker_registry='gcr.io/fuzzbench',
        experiment_filestore='/tmp/experiment_data',
        report_filestore='/tmp/report_data',

        benchmarks=['zlib_zlib_uncompress_fuzzer', 'jsoncpp_jsoncpp_fuzzer'],
        fuzzers=['afl', 'libfuzzer'],
        trials=2,
        max_total_time=3600,
        experiment='testname'
    )


def test_from_dict():
    """Tests that dacite.from_dict works as expected."""
    config_from_dict_obj = from_dict(data_class=Config, data=CONFIG_DATA)
    assert CONFIG_OBJ == config_from_dict_obj


def test_validate_all():
    """Tests that it can validate all config together."""
    assert CONFIG_OBJ.validate_all()
