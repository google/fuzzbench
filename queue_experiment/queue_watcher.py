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

class QueueWatcher:
    """The main module."""
    def __init__(self, config):
        """Initializes the module."""
        # Connect to the Redis server and get related queue information.

        # Connect to the database.

        # Initialize the pool for watching/monitoring tasks.

    def add_task(self, job_id):
        """Adds one job into pool for monitoring."""

    def delete_task(self, job_id):
        """Removes one job from monitoring pool."""

    def query_task(self, job_id):
        """Queries the status of one job in watcher's view."""

    def start(self):
        """Starts monitoring."""

    def stop(self):
        """Stops monitoring."""
