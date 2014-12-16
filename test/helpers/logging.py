"""
This test logging module configures test case logging to print
debug messages to stdout.
"""

from qiutil.logging import (configure, logger)

configure(app='qixnat', level='DEBUG')
