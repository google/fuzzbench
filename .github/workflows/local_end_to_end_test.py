# Lint as: python3
"""Tests for local_end_to_end."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import subprocess
import time

EXPERIMENT_FILESTORE = '/tmp/experiment-data'
REPORT_FILESTORE = '/tmp/report_data'
WAITING_TIME = 10
EXPERIMENT_NAME = 'local_test'


def start_local_experiment():
    """Starts a local experiment."""
    return subprocess.Popen(
        ['PYTHONPATH=.', 'python3 experiment/run_experiment.py',
         '--experiment-config', '.github/workflow/experiment-config.yaml',
         '--benchmarks', 'freetype2-2017', 'bloaty_fuzz_target',
         '--experiment-name', EXPERIMENT_NAME, '--fuzzers afl libfuzzer']).pid


def main():
    """Tests end-to-end run for local support."""
    # Start a local experiment in background.
    experiment_process_pid = start_local_experiment()

    time_limit = 20 * 60
    cur_time = time.time()
    end_time = cur_time
    success = False
    while(end_time < cur_time + time_limit):

        # Check `index.html` whether exists in report folder.
        if os.path.isfile(os.path.join(REPORT_FILESTORE, EXPERIMENT_NAME,
                                       'index.html')):
            # Check Whether `corpus` folder contains snapshot data.
            if os.path.isfile(
                os.path.join(
                    EXPERIMENT_FILESTORE, EXPERIMENT_NAME, 'experiment-folders',
                    'freetype2-2017-afl', 'trial-2', 'corpus',
                    'corpus-archive-0001.tar.gz')):
                success = True

        if success:
            return True
        time.sleep(WAITING_TIME)

    assert(False, 'Local end-to-end test failed.')


if __name__ == '__main__':
    main()
