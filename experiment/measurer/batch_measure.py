import json
import os
import posixpath

from common import new_process
from common import filesystem
from common import logs
from common import filestore_utils
from common import experiment_utils
from experiment.build import build_utils
from experiment.measurer import measure_manager

REGION_COVERAGE = False

def main():
    logs.initialize(default_extras={
        'component': 'dispatcher',
        'subcomponent': 'batch',
    })
    benchmark = os.getenv('BENCHMARK')
    fuzzer = os.getenv('FUZZER')
    experiment = os.getenv('EXPERIMENT')
    trial_num = int(os.getenv('TRIAL'))
    coverage_binaries_dir = build_utils.get_coverage_binaries_dir()
    filesystem.create_directory(coverage_binaries_dir)
    measure_manager.set_up_coverage_binary(benchmark)
    max_total_time = int(os.getenv('MAX_TOTAL_TIME'))
    max_cycle = measure_manager._time_to_cycle(max_total_time)
    print('RUNNING2')
    for cycle in range(max_cycle + 1):
        snapshot = measure_manager.measure_snapshot_coverage(fuzzer, benchmark, trial_num, cycle, REGION_COVERAGE)
        print(snapshot.edges_covered)
        time = experiment_utils.get_cycle_time(cycle)
        filename = f'{benchmark}-{fuzzer}-{trial_num}-trial-{cycle}.json'
        with open(filename, 'w+') as fp:
            data = json.dumps({'edges_covered': snapshot.edges_covered, 'trial_id': trial_num, 'experiment': experiment, 'time': time})
            fp.write(data)
        gcs_path = posixpath.join('gs://fuzzbench-data', 'batch', filename)
        print('gcs_path', gcs_path)
        filestore_utils.cp(filename, gcs_path)




if __name__ == '__main__':
    main()
