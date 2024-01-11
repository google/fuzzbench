# Copyright 2023 Google LLC
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
"""Module for mutation testing measurer functionality."""

from contextlib import contextmanager
import os
from pathlib import Path
import random
import shlex
import sqlite3
import subprocess
import time
import traceback
from common import logs
from common import benchmark_utils
from common import experiment_utils
from common import new_process
from common import environment
from experiment.build import build_utils
from experiment.exec_id import read_exec_id

logger = logs.Logger()

MUTATION_ANALYSIS_IMAGE_NAME = 'mutation_analysis'

GOOGLE_CLOUD_MUA_MAPPED_DIR = '/etc/mua_out/'
MAX_PARALLEL_MEASURE_RUNS = 2

DISPATCHER_MUA_OUT_DIR = Path('/mua_out/')

EXEC_ID = None


def get_container_name(benchmark):
    """Return the container name for the given benchmark."""
    return f'mutation_analysis_{benchmark}_container'


def get_host_mua_out_dir():
    """Return the host directory where mua_out is mapped."""
    if experiment_utils.is_local_experiment():
        return Path(os.environ.get('HOST_MUA_OUT_DIR',
                                   '/tmp/mua_out')).absolute()
    return Path(GOOGLE_CLOUD_MUA_MAPPED_DIR)


def get_mua_results_path():
    """Return the path to the mua results directory."""
    experiment_name = experiment_utils.get_experiment_name()
    return Path(DISPATCHER_MUA_OUT_DIR / experiment_name / 'mua-results')


def get_measure_db_path():
    """Return the path to the measure_runs database."""
    return get_mua_results_path() / 'measure_runs.sqlite'


def get_dispatcher_mua_out_dir():
    """Return the dispatcher directory where mua_out is mapped to."""
    return DISPATCHER_MUA_OUT_DIR


def stop_mua_container(benchmark):
    """Stop the mua container for the benchmark."""
    container_name = get_container_name(benchmark)
    try:
        new_process.execute(['docker', 'rm', '-f', container_name])
    except subprocess.CalledProcessError:
        pass


def run_mua_container(benchmark):
    """Run commands on mua container to prepare it"""
    experiment_name = experiment_utils.get_experiment_name()
    host_mua_out_dir = get_host_mua_out_dir()
    shared_mua_binaries_dir = host_mua_out_dir / experiment_name
    docker_mua_binaries_dir = f'/mapped/{experiment_name}'
    mount_arg = f'{shared_mua_binaries_dir}:{docker_mua_binaries_dir}'
    os.makedirs(shared_mua_binaries_dir, exist_ok=True)

    builder_image_url = benchmark_utils.get_builder_image_url(
        benchmark, MUTATION_ANALYSIS_IMAGE_NAME,
        environment.get('DOCKER_REGISTRY'))

    container_name = get_container_name(benchmark)

    host_mua_mapped_dir = os.environ.get('HOST_MUA_MAPPED_DIR')

    mua_run_cmd = [
        'docker', 'run', '--init', '-it', '--detach', '--name', container_name,
        '-v', mount_arg, *([] if host_mua_mapped_dir is None else
                           ['-v', f'{host_mua_mapped_dir}:/mapped_dir']),
        builder_image_url, '/bin/bash', '-c', 'sleep infinity'
    ]

    mua_run_res = new_process.execute(mua_run_cmd, expect_zero=False)
    if mua_run_res.retcode != 0:
        if 'Conflict. The container name' in mua_run_res.output:
            logger.debug('mua container already running')
            return
        logger.error('could not run mua container:\n' +
                     f'command: {mua_run_cmd}\n' +
                     f'returncode: {mua_run_res.retcode}\n' +
                     f'timed_out: {mua_run_res.timed_out}\n' +
                     f'{mua_run_res.output}')
        raise Exception('Could not run mua container.')

    # Run pipx once to set up environment
    command = [
        'pipx', 'run', 'hatch', 'run', 'python', '-c',
        'import pathlib; pathlib.Path("/tmp/mua_started").touch()'
    ]

    docker_exec_command = [
        'docker', 'exec', '-w', '/mutator/', '-t', container_name, '/bin/bash',
        '-c',
        shlex.join(command)
    ]

    logger.info(f'mua run pipx command: {docker_exec_command}')
    try:
        new_process.execute(docker_exec_command, write_to_stdout=True)
    except subprocess.CalledProcessError as err:
        logger.error(f'mua pipx run failed: {err}')
        raise err


def mua_container_is_running(benchmark):
    """Return true if the mua container is started."""
    container_name = get_container_name(benchmark)
    try:
        res = new_process.execute(
            ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
            expect_zero=False)
        if res.retcode != 0:
            return False
        if res.output.strip() == 'true':
            return True
        return False
    except subprocess.CalledProcessError:
        return False


def ensure_mua_container_running(benchmark):
    """Start the mutation analysis container for the benchmark."""
    if mua_container_is_running(benchmark):
        return

    # find correct container and start it
    container_name = get_container_name(benchmark)

    docker_start_command = ['docker', 'start', container_name]
    res = new_process.execute(docker_start_command, expect_zero=False)
    if res.retcode != 0:
        run_mua_container(benchmark)

    while True:
        check_mua_prepared_command = [
            'docker', 'exec', '-t', container_name, '/bin/bash', '-c',
            'test -f /tmp/mua_started'
        ]
        res = new_process.execute(check_mua_prepared_command, expect_zero=False)
        if res.retcode == 0:
            logger.info('mua container is prepared')
            break
        time.sleep(1)


def copy_mua_stats_db(benchmark, mua_results_dir):
    """Copy the stats db from the container to the mua results dir."""
    # Wait a bit if the container was just started
    for _ in range(10):
        if mua_container_is_running(benchmark):
            break
        logger.debug('Waiting for mua container to start.')
        time.sleep(1)

    container_name = get_container_name(benchmark)
    corpus_run_stats_db = mua_results_dir / 'stats.sqlite'

    if not corpus_run_stats_db.is_file():
        logger.info(
            f'Copying stats db from container to: {corpus_run_stats_db}')

        copy_stats_db_command = [
            'docker', 'cp', f'{container_name}:/mua_build/build/stats.db',
            str(corpus_run_stats_db)
        ]
        logger.debug(f'mua copy stats db command: {copy_stats_db_command}')
        new_process.execute(copy_stats_db_command, write_to_stdout=True)
        build_utils.store_mua_stats_db(corpus_run_stats_db, benchmark)


def run_mua_build_ids(benchmark, trial_num, fuzzer, cycle):
    """Run mua_build_ids.py on the container."""
    global EXEC_ID
    if EXEC_ID is None:
        EXEC_ID = read_exec_id()
        logger.debug('Setting EXEC_ID to %s', EXEC_ID)

    container_name = get_container_name(benchmark)
    # get additional info from commons
    experiment_name = experiment_utils.get_experiment_name()
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    # execute command on container
    command = [
        'python3',
        '/mutator/mua_build_ids.py',
        str(EXEC_ID),
        fuzz_target,
        benchmark,
        experiment_name,
        fuzzer,
        str(trial_num),
        # "--debug_num_mutants=200"
    ]

    docker_exec_command = [
        'docker', 'exec', '-t', container_name, '/bin/bash', '-c',
        shlex.join(command)
    ]

    logger.debug(f'mua_build_ids command: {docker_exec_command}')
    try:
        mua_build_res = new_process.execute(docker_exec_command)
    except subprocess.CalledProcessError as err:
        logger.error(f'mua_build_ids failed: {err}')
        trace_msg = traceback.format_exc()
        error_msg = f'mua_build_ids failed: {err}\n{trace_msg}'
        build_utils.store_mua_build_log(error_msg, benchmark, fuzzer, trial_num,
                                        cycle)
        raise err
    logger.info(f'mua_build_ids result: {mua_build_res.retcode} ' +
                f'timed_out: {mua_build_res.timed_out}\n' +
                f'{mua_build_res.output}')
    build_utils.store_mua_build_log(mua_build_res.output or '', benchmark,
                                    fuzzer, trial_num, cycle)


class MeasureRunsDB:
    """Class for managing the measure_runs database, which is used to limit
    concurrently ran mutation measurments."""

    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file,
                                    check_same_thread=False,
                                    timeout=300)

    @contextmanager
    def cur(self):
        """Return a cursor to the database."""
        with self.conn as conn:
            cur = conn.cursor()
            yield cur
            cur.close()

    @contextmanager
    def transaction(self, transaction_type):
        """Return a cursor to the database, with a started transaction of the
        given type."""
        while True:
            try:
                with self.cur() as cur:
                    cur.execute(f'BEGIN {transaction_type} TRANSACTION')
                    yield cur
                    return
            except sqlite3.OperationalError as err:
                if 'database is locked' in str(err):
                    time.sleep(random.random() * 10)
                else:
                    raise
        raise Exception('Could not begin transaction.')

    def initialize(self, num_trials):
        """Initialize the database."""
        logger.info(f'Initializing measure_runs database: {self.db_file}')
        with self.cur() as cur:
            cur.execute('PRAGMA journal_mode=WAL')
            cur.execute('PRAGMA synchronous=NORMAL')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS instances (
                    spot INTEGER PRIMARY KEY,
                    in_use INTEGER
                )
            ''')

            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_cpus_used ON instances
                        (in_use, spot)
            ''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS meta (
                    num_trials INTEGER
                )
            ''')

            cur.execute(
                '''
                INSERT OR IGNORE INTO meta (num_trials)
                VALUES (?)
                ''', (num_trials,))

            cur.execute('''
                CREATE TABLE IF NOT EXISTS measure_runs (
                    fuzzer TEXT,
                    benchmark TEXT,
                    run_idx INTEGER,
                    done INTEGER,
                    trial_num INTEGER,
                    covered_mutants INTEGER,
                    PRIMARY KEY (fuzzer, benchmark, run_idx)
                )''')

            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_measure_runs ON measure_runs (
                    fuzzer, benchmark, run_idx, done
                )''')

            cur.execute('''
                CREATE TABLE IF NOT EXISTS covered_muts (
                    trial_id INTEGER,
                    covered_mut INTEGER,
                    PRIMARY KEY (trial_id, covered_mut)
                )''')

            cur.execute('''
                CREATE INDEX IF NOT EXISTS idx_covered_muts ON covered_muts (
                    trial_id, covered_mut
                )''')

        with self.transaction('EXCLUSIVE') as cur:
            for idx in range(MAX_PARALLEL_MEASURE_RUNS):
                cur.execute(
                    '''
                    INSERT OR IGNORE INTO instances (spot, in_use)
                    VALUES (?, 0)
                    ''', (idx,))

    def get_free_spot(self):
        """Return a free spot, or None if none are available."""
        with self.transaction('EXCLUSIVE') as cur:
            cur.execute('''
                SELECT spot FROM instances WHERE in_use = 0
                ORDER BY spot ASC LIMIT 1
            ''')
            row = cur.fetchone()
            if row:
                cur.execute('UPDATE instances SET in_use = 1 WHERE spot = ?',
                            (row[0],))
                return row[0]
            return None

    def release_spot(self, spot):
        """Release a spot."""
        with self.transaction('IMMEDIATE') as cur:
            cur.execute('UPDATE instances SET in_use = 0 WHERE spot = ?',
                        (spot,))

    def get_num_trials(self):
        """Return the number of trials."""
        with self.cur() as cur:
            cur.execute('SELECT num_trials FROM meta')
            row = cur.fetchone()
            if row:
                return row[0]
            return None

    def ensure_measure_runs(self, benchmark, fuzzer, num_trials):
        """Ensure that there are measure runs for the given benchmark and
        fuzzer."""
        with self.transaction('EXCLUSIVE') as cur:
            for run_idx in range(num_trials):
                cur.execute(
                    '''
                    INSERT OR IGNORE INTO measure_runs (
                        fuzzer, benchmark, run_idx, done
                    ) VALUES (?, ?, ?, 0)
                    ''', (fuzzer, benchmark, run_idx))

    def add_measure_run(self, benchmark, fuzzer, trial_num, covered_mutants):
        """Add a measure run."""
        with self.transaction('EXCLUSIVE') as cur:
            cur.execute(
                '''
                UPDATE measure_runs SET
                    done = 1,
                    trial_num = ?,
                    covered_mutants = ?
                WHERE rowid = (
                    SELECT MIN(rowid)
                    FROM measure_runs
                    WHERE fuzzer = ? AND benchmark = ? AND done = 0
                )
                ''', (trial_num, covered_mutants, fuzzer, benchmark))

    def add_measure_run_failed(self, benchmark, fuzzer, trial_num):
        """Add a measure run."""
        with self.transaction('EXCLUSIVE') as cur:
            cur.execute(
                '''
                UPDATE measure_runs SET
                    done = 2,
                    trial_num = ?
                WHERE rowid = (
                    SELECT MIN(rowid)
                    FROM measure_runs
                    WHERE fuzzer = ? AND benchmark = ? AND done = 0
                )
                ''', (trial_num, fuzzer, benchmark))

    def wait_for_other_trials_to_complete(self, benchmark, fuzzer):
        """Wait for other trials to complete."""
        num_trials = self.get_num_trials()
        if num_trials is None:
            raise Exception('Could not get number of trials from database.')
        while True:
            with self.cur() as cur:
                cur.execute(
                    '''
                    SELECT COUNT(*) FROM measure_runs
                    WHERE fuzzer = ? AND benchmark = ? AND done = 0
                    ''', (fuzzer, benchmark))
                row = cur.fetchone()
                if row:
                    if row[0] == 0:
                        return
                    logger.info(
                        f'Waiting on other trials for {benchmark} {fuzzer} ' +
                        f'to complete, {row[0]} remaining.')
                else:
                    logger.error('Could not get number of remaining trials.')
                time.sleep(10)

    def get_median_run(self, benchmark, fuzzer):
        """Return the median run for the given benchmark and fuzzer."""
        num_trials = self.get_num_trials()
        if num_trials is None:
            raise Exception('Could not get number of trials from database.')
        with self.cur() as cur:
            cur.execute(
                '''
                SELECT trial_num FROM measure_runs
                WHERE fuzzer = ? AND benchmark = ? AND done = 1
                ORDER BY covered_mutants, rowid DESC LIMIT 1 OFFSET ?
                ''', (fuzzer, benchmark, num_trials // 2))
            row = cur.fetchone()
            if row:
                return row[0]
            return None

    def get_num_covered_mutants(self, trial_num):
        """Return the number of covered mutants for the given trial."""
        with self.cur() as cur:
            cur.execute(
                '''
                SELECT COUNT(*) FROM covered_muts
                WHERE trial_id = ?
                ''', (trial_num,))
            row = cur.fetchone()
            if row:
                return row[0]
            return None


def init_measure_db(num_trials):
    """Initialize the measure_runs database."""
    measure_db_path = get_measure_db_path()
    logger.warning(f'Initializing measure_runs database: {measure_db_path}')
    measure_db = MeasureRunsDB(measure_db_path)
    measure_db.initialize(num_trials)


def get_covered_mutants(trial_num):
    """Return the number of covered mutants for the given trial."""
    measure_db_path = get_measure_db_path()
    measure_db = MeasureRunsDB(measure_db_path)
    return measure_db.get_num_covered_mutants(trial_num)


def add_measure_run_failed(benchmark, fuzzer, trial_num):
    """Add that the measure run failed and should not be waited for nor used as
    a candidate for the median run."""
    measure_db_path = get_measure_db_path()
    measure_db = MeasureRunsDB(measure_db_path)
    num_trials = measure_db.get_num_trials()
    measure_db.ensure_measure_runs(benchmark, fuzzer, num_trials)
    measure_db.add_measure_run_failed(benchmark, fuzzer, trial_num)


def add_measure_run(benchmark, fuzzer, trial_num, covered_mutants):
    """Add the covered mutants for a measure run, this indicates that the
    trial is done."""
    measure_db_path = get_measure_db_path()
    measure_db = MeasureRunsDB(measure_db_path)
    num_trials = measure_db.get_num_trials()
    measure_db.ensure_measure_runs(benchmark, fuzzer, num_trials)
    measure_db.add_measure_run(benchmark, fuzzer, trial_num, covered_mutants)


def wait_if_median_run(benchmark, fuzzer, trial_id):
    """Wait until all trials for benchmark fuzzer are done and return
     True if the trial_id is the median run."""
    measure_db_path = get_measure_db_path()
    measure_db = MeasureRunsDB(measure_db_path)
    measure_db.wait_for_other_trials_to_complete(benchmark, fuzzer)
    median_run_trial_id = measure_db.get_median_run(benchmark, fuzzer)
    return trial_id == median_run_trial_id


@contextmanager
def get_measure_spot():
    """Context manager for getting a free measure spot."""
    measure_db_path = get_measure_db_path()
    measure_db = MeasureRunsDB(measure_db_path)
    start_wait = time.time()
    while True:
        new_cpu = measure_db.get_free_spot()
        if new_cpu is not None:
            logger.info(
                f'Got spot {new_cpu} after {time.time() - start_wait:.2f}s')
            try:
                yield new_cpu
            finally:
                measure_db.release_spot(new_cpu)
            break
        time.sleep(random.random() * 2)
    else:  # no break
        yield None
