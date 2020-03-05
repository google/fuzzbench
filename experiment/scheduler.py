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
"""Code for starting and ending trials."""
import datetime
import multiprocessing
import shlex
import sys
import time

from common import benchmark_utils
from common import experiment_utils
from common import fuzzer_config_utils
from common import gcloud
from common import logs
from common import yaml_utils
from database import models
from database import utils as db_utils

# Give the trial runner a little extra time to shut down and account for how
# long it can take to actually start running once an instance is started. 5
# minutes is an arbitrary amount of time.
GRACE_TIME_SECONDS = 5 * 60

FAIL_WAIT_SECONDS = 10 * 60

logger = logs.Logger('scheduler')  # pylint: disable=invalid-name


def datetime_now() -> datetime.datetime:
    """Return datetime.datetime.utcnow(). This function is needed for
    mocking."""
    return datetime.datetime.now(datetime.timezone.utc)


# TODO(metzman): Figure out what are the best practices for the functions which
# must return sqlalchemy.orm.Query. Importing it just for annotation might be
# confusing to readers. There may also be weird situations where it is
# acceptable to use a list or query (because of duck typing) but type hints
# prevents us unless handled intelligently).
def get_experiment_trials(experiment: str):
    """Returns a query of trials in |experiment|."""
    return db_utils.query(models.Trial).filter(
        models.Trial.experiment == experiment).order_by(models.Trial.id)


def get_pending_trials(experiment: str):
    """Returns trial entities from |experiment| that have PENDING status."""
    return get_experiment_trials(experiment).filter(
        models.Trial.time_started.is_(None))


def get_expired_trials(experiment: str, max_total_time: int):
    """Returns trial entities from |experiment| that have not ended and were
    started more than |max_total_time| + |GRACE_TIME_SECONDS| ago."""
    earliest_nonexpired_dt = datetime_now() - datetime.timedelta(
        seconds=max_total_time + GRACE_TIME_SECONDS)

    return get_experiment_trials(experiment).filter(
        models.Trial.time_started <= earliest_nonexpired_dt).filter(
            models.Trial.time_ended.is_(None))


def all_trials_ended(experiment: str) -> bool:
    """Return a bool if there are any trials in |experiment| that have not
    started."""
    return not get_experiment_trials(experiment).filter(
        models.Trial.time_ended.is_(None)).all()


def end_expired_trials(experiment_config: dict):
    """Get all expired trials, end them and return them."""
    trials_past_expiry = get_expired_trials(experiment_config['experiment'],
                                            experiment_config['max_total_time'])
    expired_instances = []
    current_dt = datetime_now()
    for trial in trials_past_expiry:
        expired_instances.append(
            experiment_utils.get_trial_instance_name(
                experiment_config['experiment'], trial.id))
        trial.time_ended = current_dt

    # Bail out here because trials_past_expiry will be truthy until evaluated.
    if not expired_instances:
        return

    # Delete instances for expired trials.
    running_instances = gcloud.list_instances()
    instances_to_delete = [
        i for i in expired_instances if i in running_instances
    ]
    if instances_to_delete and not gcloud.delete_instances(
            instances_to_delete, experiment_config['cloud_compute_zone']):
        # If we failed to delete some instances, then don't update the status
        # of expired trials in database as we don't know which instances were
        # successfully deleted. Wait for next iteration of end_expired_trials.
        return

    db_utils.bulk_save(trials_past_expiry)


def schedule(experiment_config: dict, pool):
    """Gets all pending trials for the current experiment and then schedules
    those that are possible."""
    logger.info('Finding trials to schedule.')

    # End expired trials
    end_expired_trials(experiment_config)

    # Start pending trials.
    experiment = experiment_config['experiment']
    start_trials(get_experiment_trials(experiment), experiment_config, pool)


def schedule_loop(experiment_config: dict):
    """Continuously run the scheduler until there is nothing left to schedule.
    Note that this should not be called unless
    multiprocessing.set_start_method('spawn') was called first. Otherwise it
    will use fork to create the Pool which breaks logging."""
    experiment = experiment_config['experiment']

    # Create the thread pool once and reuse it to avoid leaking threads and
    # other issues.
    with multiprocessing.Pool() as pool:
        while True:
            try:
                schedule(experiment_config, pool)

                if all_trials_ended(experiment):
                    # Nothing left to schedule, bail out.
                    break
            except Exception:  # pylint: disable=broad-except
                logger.error('Error occurred during scheduling.')

            # Either
            # - We had an unexpected exception OR
            # - We have not been able to start trials and still have some
            #   remaining. This can happen when we run out of instance quota.
            # In these cases, sleep before retrying again.
            time.sleep(FAIL_WAIT_SECONDS)

    logger.info('Finished scheduling.')


def start_trials(trials, experiment_config: dict, pool):
    """Start all |trials| that are possible to start. Marks the ones that were
    started as started."""
    logger.info('Starting trials.')
    trial_id_mapping = {
        trial.id: trial
        for trial in trials.filter(models.Trial.time_started.is_(None))
    }
    started_trial_proxies = pool.starmap(
        _start_trial, [(TrialProxy(trial), experiment_config)
                       for trial in trial_id_mapping.values()])

    # Map proxies back to trials and mark trials as started when proxies were
    # marked as such.
    started_trials = []
    for proxy in started_trial_proxies:
        if not proxy:
            continue
        trial = trial_id_mapping[proxy.id]
        trial.time_started = proxy.time_started
        started_trials.append(trial)

    if started_trials:
        db_utils.add_all(started_trials)
    return started_trials


class TrialProxy:
    """A proxy object for a model.Trial. TrialProxy's allow these fields to be
    set and gotten without making any database calls."""

    def __init__(self, trial):
        self.id = trial.id  # pylint: disable=invalid-name
        self.fuzzer = trial.fuzzer
        self.benchmark = trial.benchmark
        self.time_started = trial.time_started
        self.time_ended = trial.time_ended


def _initialize_logs(experiment):
    """Initialize logs. This must be called on process start."""
    logs.initialize(default_extras={
        'experiment': experiment,
        'component': 'dispatcher'
    })


def _start_trial(trial: TrialProxy, experiment_config: dict):
    """Start a trial if possible. Mark the trial as started if it was and then
    return the Trial. Otherwise return None."""
    # TODO(metzman): Add support for early exit (trial_creation_failed) that was
    # removed when this started using multiprocessing.
    # Also, support batched saves of trials (with a queue, like measurer uses)
    # so that measuring a schedule doesn't require waiting until the map call
    # that calls this function completely terminates.
    _initialize_logs(experiment_config['experiment'])
    logger.info('Start trial %d.', trial.id)
    started = create_trial_instance(trial.benchmark, trial.fuzzer, trial.id,
                                    experiment_config)
    if started:
        trial.time_started = datetime_now()
        return trial
    logger.info('Trial: %d not started.', trial.id)
    return None


def create_trial_instance(benchmark: str, fuzzer: str, trial_id: int,
                          experiment_config: dict) -> bool:
    """Create or start a trial instance for a specific
    trial_id,fuzzer,benchmark."""
    instance_name = experiment_utils.get_trial_instance_name(
        experiment_config['experiment'], trial_id)
    fuzzer_config = fuzzer_config_utils.get_by_variant_name(fuzzer)
    underlying_fuzzer_name = fuzzer_config['fuzzer']
    docker_image_url = benchmark_utils.get_runner_image_url(
        benchmark, underlying_fuzzer_name, experiment_config['cloud_project'])
    fuzz_target = benchmark_utils.get_fuzz_target(benchmark)

    # Convert additional environment variables from configuration to arguments
    # that will be passed to docker.
    additional_env = ''
    if 'env' in fuzzer_config:
        additional_env = ' '.join([
            '-e {k}={v}'.format(k=k, v=shlex.quote(v))
            for k, v in fuzzer_config['env'].items()
        ])

    startup_script = '''#!/bin/bash
echo 0 > /proc/sys/kernel/yama/ptrace_scope
echo core >/proc/sys/kernel/core_pattern

while ! docker pull {docker_image_url}
do
  echo 'Error pulling image, retrying...'
done

docker run --privileged --cpuset-cpus=0 --rm \
-e INSTANCE_NAME={instance_name} -e FUZZER={fuzzer} -e BENCHMARK={benchmark} \
-e FUZZER_VARIANT_NAME={fuzzer_variant_name} -e EXPERIMENT={experiment} \
-e TRIAL_ID={trial_id} -e MAX_TOTAL_TIME={max_total_time} \
-e CLOUD_PROJECT={cloud_project} -e CLOUD_COMPUTE_ZONE={cloud_compute_zone} \
-e CLOUD_EXPERIMENT_BUCKET={cloud_experiment_bucket} \
-e FUZZ_TARGET={fuzz_target} {additional_env} \
--cap-add SYS_NICE --cap-add SYS_PTRACE --name=runner-container \
{docker_image_url} 2>&1 | tee /tmp/runner-log.txt'''.format(
        instance_name=instance_name,
        benchmark=benchmark,
        experiment=experiment_config['experiment'],
        fuzzer=underlying_fuzzer_name,
        fuzzer_variant_name=fuzzer,
        trial_id=trial_id,
        max_total_time=experiment_config['max_total_time'],
        cloud_project=experiment_config['cloud_project'],
        cloud_compute_zone=experiment_config['cloud_compute_zone'],
        cloud_experiment_bucket=experiment_config['cloud_experiment_bucket'],
        fuzz_target=fuzz_target,
        docker_image_url=docker_image_url,
        additional_env=additional_env)

    startup_script_path = '/tmp/%s-start-docker.sh' % instance_name
    with open(startup_script_path, 'w') as file_handle:
        file_handle.write(startup_script)

    return gcloud.create_instance(instance_name,
                                  gcloud.InstanceType.RUNNER,
                                  experiment_config,
                                  startup_script=startup_script_path)


def main():
    """Main function for running scheduler independently."""
    logs.initialize(default_extras={'component': 'dispatcher'})

    if len(sys.argv) != 2:
        print('Usage: {} <experiment_config.yaml>'.format(sys.argv[0]))
        return 1

    experiment_config = yaml_utils.read(sys.argv[1])
    schedule_loop(experiment_config)

    return 0


if __name__ == '__main__':
    sys.exit(main())
