"""
This module defines the object for watching filestores and assign new measure
tasks to the queues.
"""

from queue_experiment.task_module import measure_task

class FilestoreWatcher():
    """The implementation."""
    def ___init___(self, config, measure_queue):
        self.config = config
        self.measure_queue = measure_queue

    def no_measure_tasks(self):
        """Check whether there needs to assign new measure tasks."""
        return True

    def check(self):
        """Checks the filestore and assign measure tasks if there are new corpus
        data."""
        measure_queue.enqueue(measure_task, config.fuzzers[0], config.benchmarks[0])

