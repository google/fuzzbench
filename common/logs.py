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
"""Set up for logging."""
from enum import Enum
import logging
import os
import sys
import traceback

import google.cloud.logging
from google.cloud.logging.handlers.handlers import CloudLoggingHandler
from google.cloud import error_reporting

# Disable this check since we have a bunch of non-constant globals in this file.
# pylint: disable=invalid-name

from common import retry
from common import utils

_default_logger = None
_log_client = None
_error_reporting_client = None
_default_extras = {}

LOG_LENGTH_LIMIT = 250 * 1000

NUM_RETRIES = 5
RETRY_DELAY = 1


def _initialize_cloud_clients():
    """Initialize clients for Google Cloud Logging and Error reporting."""
    assert not utils.is_local()
    global _log_client
    if _log_client:
        return
    _log_client = google.cloud.logging.Client()
    logging_handler = CloudLoggingHandler(_log_client)
    logging.getLogger().addHandler(logging_handler)
    global _error_reporting_client
    _error_reporting_client = error_reporting.Client()


def initialize(name='fuzzbench', default_extras=None, log_level=logging.INFO):
    """Initializes stackdriver logging if running on Google Cloud."""
    logging.getLogger().setLevel(log_level)
    logging.getLogger().addFilter(LengthFilter())

    # Don't log so much with SQLalchemy to avoid stressing the logging library.
    # See crbug.com/1044343.
    logging.getLogger('sqlalchemy').setLevel(logging.ERROR)

    if utils.is_local():
        return
    _initialize_cloud_clients()
    global _default_logger
    _default_logger = _log_client.logger(name)

    default_extras = {} if default_extras is None else default_extras

    _set_instance_name(default_extras)
    _set_experiment(default_extras)

    global _default_extras
    _default_extras.update(default_extras)


def _set_instance_name(extras: dict):
    """Set instance_name in |extras| if it is provided by the environment and
    not already set."""
    if 'instance_name' in extras:
        return

    instance_name = os.getenv('INSTANCE_NAME')
    if instance_name is None:
        return

    extras['instance_name'] = instance_name


def _set_experiment(extras: dict):
    """Set experiment in |extras| if it is provided by the environment and
    not already set."""
    if 'experiment' in extras:
        return

    experiment = os.getenv('EXPERIMENT')
    if experiment is None:
        return

    extras['experiment'] = experiment


class Logger:
    """Wrapper around logging.Logger that allows it to be used like we use the
    root logger for stackdriver."""

    def __init__(self, name, default_extras=None, log_level=logging.INFO):
        if not utils.is_local():
            _initialize_cloud_clients()
            self.logger = _log_client.logger(name)
        else:
            self.logger = logging.getLogger(name)

        logging.getLogger(name).setLevel(log_level)
        logging.getLogger(name).addFilter(LengthFilter())
        self.default_extras = default_extras if default_extras else {}

    def error(self, *args, **kwargs):
        """Wrapper that uses _log_function_wrapper to call error."""
        self._log_function_wrapper(error, *args, **kwargs)

    def warning(self, *args, **kwargs):
        """Wrapper that uses _log_function_wrapper to call warning."""
        self._log_function_wrapper(warning, *args, **kwargs)

    def info(self, *args, **kwargs):
        """Wrapper that uses _log_function_wrapper to call info."""
        self._log_function_wrapper(info, *args, **kwargs)

    def debug(self, *args, **kwargs):
        """Wrapper that uses _log_function_wrapper to call debug."""
        self._log_function_wrapper(debug, *args, **kwargs)

    def _log_function_wrapper(self, log_function, message, *args, extras=None):
        """Wrapper around log functions that passes extras and the logger this
        object wraps (self.logger)."""
        extras = {} if extras is None else extras
        extras = extras.copy()
        extras.update(self.default_extras)
        log_function(message, *args, extras=extras, logger=self.logger)


class LogSeverity(Enum):
    """Enum for different levels of log severity."""
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG


@retry.wrap(NUM_RETRIES, RETRY_DELAY, 'common.logs.log', log_retries=False)
def log(logger, severity, message, *args, extras=None):
    """Log a message with severity |severity|. If using stack driver logging
    then |extras| is also logged (in addition to default extras)."""
    message = str(message)
    if args:
        message = message % args

    if utils.is_local():
        if extras:
            message += ' Extras: ' + str(extras)
        logging.log(severity, message)
        return

    if logger is None:
        logger = _default_logger
    assert logger

    struct_message = {
        'message': message,
    }
    all_extras = _default_extras.copy()
    extras = extras or {}
    all_extras.update(extras)
    struct_message.update(all_extras)
    severity = LogSeverity(severity).name
    logger.log_struct(struct_message, severity=severity)


def error(message, *args, extras=None, logger=None):
    """Logs |message| to stackdriver logging and error reporting (including
    exception if there was one."""

    @retry.wrap(NUM_RETRIES,
                RETRY_DELAY,
                'common.logs.error._report_error_with_retries',
                log_retries=False)
    def _report_error_with_retries(message):
        if utils.is_local():
            return
        _error_reporting_client.report(message)

    if not any(sys.exc_info()):
        _report_error_with_retries(message % args)
        log(logger, logging.ERROR, message, *args, extras=extras)
        return
    # I can't figure out how to include both the message and the exception
    # other than this having the exception message preceed the log message
    # (without using private APIs).
    _report_error_with_retries(traceback.format_exc() + '\nMessage: ' +
                               message % args)
    extras = {} if extras is None else extras
    extras['traceback'] = traceback.format_exc()
    log(logger, logging.ERROR, message, *args, extras=extras)


def warning(message, *args, extras=None, logger=None):
    """Log a message with severity 'WARNING'."""
    log(logger, logging.WARNING, message, *args, extras=extras)


def info(message, *args, extras=None, logger=None):
    """Log a message with severity 'INFO'."""
    log(logger, logging.INFO, message, *args, extras=extras)


def debug(message, *args, extras=None, logger=None):
    """Log a message with severity 'DEBUG'."""
    log(logger, logging.DEBUG, message, *args, extras=extras)


class LengthFilter(logging.Filter):
    """Filter for truncating log messages that are too long for stackdriver."""

    def filter(self, record):
        if len(record.msg) > LOG_LENGTH_LIMIT:
            record.msg = ('TRUNCATED: ' + record.msg)[:LOG_LENGTH_LIMIT]
        return True
