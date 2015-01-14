"""Command XNAT options."""

import qiutil
from qiutil import command

def add_options(parser):
    """
    Adds the logging, project and config options to the given command
    line arugment parser.
    
    :param parser: the Python ``argparse`` parser
    """
    # The logging options.
    qiutil.command.add_options(parser)
    
    # The XNAT project.
    parser.add_argument('-p', '--project',
                        help="the XNAT project (default is 'QIN')")
    
    # The XNAT configuration.
    parser.add_argument('-c', '--config', help='the XNAT configuration file',
                        metavar='FILE')
