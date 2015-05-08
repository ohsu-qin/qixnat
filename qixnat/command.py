"""Command XNAT options."""

import qiutil
from .helpers import path_hierarchy

def add_options(parser):
    """
    Adds the logging, project and config options to the given command
    line arugment parser.

    :param parser: the Python ``argparse`` parser
    """
    # The logging options.
    qiutil.command.add_options(parser)

    # The XNAT configuration.
    parser.add_argument('-c', '--config', help='the XNAT configuration file',
                        metavar='FILE')


def configure_log(**opts):
    # Configure the logger for this qixnat module and the qiutil module.
    qiutil.command.configure_log('qixnat', 'qiutil', **opts)
