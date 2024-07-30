"""Show PR experiment basic info."""
import logging
import os

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

logging.info('PR: %s', os.getenv('PR_NUMBER'))
