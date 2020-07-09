"""
Defines the config object, including all required config information during the
experiment.

This is a data object.

It is a combination between platform config and experiment config.
"""


from dataclasses import dataclass
from typing import List


@dataclass
class Config():
    """Defines all configurations."""

    # Platform.
    local_experiment: bool
    docker_registry: str
    experiment_filestore: str
    report_filestore: str

    # Experiment.
    benchmarks: List[str]
    fuzzers: List[str]
    trials: int
    max_total_time: int


    def validate_all(self):
        """Validates all configs."""
        # TODO: add validation logic later.
        return True
