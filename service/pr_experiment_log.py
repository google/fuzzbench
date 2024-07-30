"""Show PR experiment basic info."""
import logging
import os

logging.info('PR: %s', os.getenv('PR_NUMBER'))
