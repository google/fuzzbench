"""
This module watches the status of all tasks in redis server. When a task
updates, this module will update the database to reflect the change.

This module functions as a callback object and will talk to databse in a non
parallel way.

This module will write and read the database.
This module is the only module who can write the database.
The other one is the report_generator.py, where it will read the database for
updates.
"""

from database import utils as db_utils
from database import models
from experiment import scheduler

class QueueWatcher:
    """The main module."""
    def __init__(self, config, build_n_run_queue, measure_queue):
        """Initializes the module."""
        self.config = config
        self.build_n_run_queue = build_n_run_queue
        self.measure_queue = measure_queue
        self.experiment = config['experiment']

        # Connect to the database.

        # Initialize the pool for watching/monitoring tasks.
        self.task_pool = dict()

    def add_task(self, job_id):
        """Adds one job into pool for monitoring."""
        self.task_pool.append(job_id)

    def delete_task(self, job_id):
        """Removes one job from monitoring pool."""

    def query_task(self, job_id):
        """Queries the status of one job in watcher's view."""
        print(job_id.status)
        # TODO: If it starts, set the start time.
        #       If it is done, set the end time and delete the task.

    def check(self):
        """Updates database based on the job pool finished status."""
        for job_id in self.task_pool:
            query_task(job_id)

    def finished(self):
        """Checks database to see whether all trials finish."""
        return scheduler.all_trials_ended(self.experiment)
