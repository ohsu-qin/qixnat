"""
This test logging module configures test case logging to print
debug messages to stdout.
"""

import os
from qiutil.logging import (configure, logger)

LOG_FILE = os.path.dirname(__file__) + '/../results/log/qixnat.log'


configure(app='qixnat', filename=LOG_FILE, level='DEBUG')
