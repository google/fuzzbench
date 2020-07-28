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
"""Self-defined worker module."""
import time

import redis
import rq

MAX_TIME_LIMIT = 3600
REASSIGN_GAP_TIME = 5


def no_pending_jobs(queue):
    """Checks whether the queue has unfinished jobs."""
    return (queue.deferred_job_registry.count + queue.count +
            queue.started_job_registry.count) == 0


def main():
    """Sets up Redis connection and starts the worker."""
    redis_connection = redis.Redis(host="queue-server")
    with rq.Connection(redis_connection):
        queue = rq.Queue('build_n_run_queue')
        worker = rq.Worker([queue], connection=redis_connection)

        start_time = time.time()
        while time.time() - start_time < MAX_TIME_LIMIT:
            if not no_pending_jobs(queue):
                worker.work(burst=True)
            else:
                time.sleep(REASSIGN_GAP_TIME)
                if no_pending_jobs(queue):
                    return
            time.sleep(REASSIGN_GAP_TIME)


if __name__ == '__main__':
    main()
