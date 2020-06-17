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
"""Code for setting up a work queue with rq."""
import redis
import rq
import rq.job

from common import experiment_utils


def initialize_queue(redis_host):
    """Returns a redis-backed rq queue."""
    queue_name = experiment_utils.get_experiment_name()
    redis_connection = redis.Redis(host=redis_host)
    queue = rq.Queue(queue_name, connection=redis_connection)
    return queue


def get_all_jobs(queue):
    """Returns all the jobs in queue."""
    job_ids = queue.get_job_ids()
    return rq.job.Job.fetch_many(job_ids, queue.connection)
